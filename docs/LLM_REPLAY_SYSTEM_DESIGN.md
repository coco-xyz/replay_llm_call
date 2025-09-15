# LLM测试回放系统技术实施文档

## 1. 项目概述

### 1.1 需求分析
构建一个LLM测试回放系统，支持：
- 测试Case管理：添加、编辑、删除、列表展示
- 测试执行：解析raw data，调用LLM，展示结果
- 测试日志：记录测试历史，支持筛选
- 模型选择：支持OpenRouter不同模型

### 1.2 技术栈
基于现有项目架构：
- **后端**: FastAPI + pydantic-ai + SQLAlchemy + PostgreSQL
- **前端**: HTML + JavaScript + Bootstrap（简单页面）
- **LLM**: OpenRouter API
- **缓存**: Redis
- **监控**: Logfire

## 2. 系统架构设计

### 2.1 模块结构
```
src/
├── models/
│   ├── test_case.py          # 测试用例模型
│   ├── test_log.py           # 测试日志模型
│   └── llm_data.py           # LLM数据解析模型
├── stores/
│   ├── test_case_store.py    # 测试用例数据访问
│   └── test_log_store.py     # 测试日志数据访问
├── services/
│   ├── test_case_service.py  # 测试用例业务逻辑
│   ├── test_execution_service.py # 测试执行业务逻辑
│   └── llm_replay_service.py # LLM回放服务
├── agents/
│   └── replay_agent.py       # LLM回放代理
├── api/
│   └── v1/
│       └── endpoints/
│           ├── test_cases.py # 测试用例API
│           ├── test_execution.py # 测试执行API
│           └── test_logs.py  # 测试日志API
└── templates/                # 前端模板
    ├── test_cases.html       # 测试用例管理页面
    ├── test_execution.html   # 测试执行页面
    └── test_logs.html        # 测试日志页面
```

### 2.2 页面流程
```
测试用例管理页面 → 点击Play → 测试执行页面 → 执行测试 → 测试日志页面
     ↑                                                        ↓
     ←←←←←←←←←←←←← 查看历史日志 ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
```

## 3. 数据模型设计

### 3.1 测试用例模型 (TestCase)
```python
from sqlalchemy import String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import List, Optional

# mapped_column 是 SQLAlchemy 2.0+ 的新语法，用于定义表列的映射
# 它提供了更好的类型提示和IDE支持，替代了旧的 Column() 语法

class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # 存储原始的logfire raw data
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)

    # 存储原始请求中除system prompt和最后一条user message外的其他messages（用于replay拼接）
    original_messages: Mapped[List[dict]] = mapped_column(JSON, nullable=False)
    # 存储原始请求的tools
    original_tools: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)
    # 存储原始请求的model名称
    original_model: Mapped[str] = mapped_column(String(255), nullable=False)

    # 存储解析后的关键数据，用于页面展示和replay拼接
    parsed_system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_user_message: Mapped[str] = mapped_column(Text, nullable=False)

    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联测试日志
    test_logs: Mapped[List["TestLog"]] = relationship("TestLog", back_populates="test_case")
```

### 3.2 测试日志模型 (TestLog)
```python
from sqlalchemy import String, Text, DateTime, JSON, Integer, ForeignKey

class TestLog(Base):
    __tablename__ = "test_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    test_case_id: Mapped[str] = mapped_column(String, ForeignKey("test_cases.id"))
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # 输入数据（执行时的实际输入，可能被用户修改过）
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    tools: Mapped[Optional[dict]] = mapped_column(JSON)

    # 输出数据
    llm_response: Mapped[Optional[str]] = mapped_column(Text)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer)

    # 执行状态 - 同步执行，只有 success 或 failed
    status: Mapped[str] = mapped_column(String(20), default="success")  # success, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关联测试用例
    test_case: Mapped["TestCase"] = relationship("TestCase", back_populates="test_logs")
```

### 3.3 LLM数据解析模型
```python
class LLMRawData(BaseModel):
    """解析logfire raw data的模型"""
    messages: List[Dict[str, str]]
    tools: Optional[List[Dict]] = None
    model: Optional[str] = None
    
class ParsedLLMData(BaseModel):
    """解析后的LLM数据"""
    # 原始数据（用于replay拼接）
    original_messages: List[Dict]  # 除system prompt和最后一条user message外的其他messages
    original_tools: Optional[List[Dict]] = None
    original_model: str

    # 解析出的关键数据（用于页面展示和replay拼接）
    system_prompt: str
    user_message: str

class TestExecutionRequest(BaseModel):
    """测试执行请求"""
    test_case_id: str
    # 用户可能修改的参数（如果为None则使用原始值）
    modified_system_prompt: Optional[str] = None
    modified_user_message: Optional[str] = None
    modified_tools: Optional[List[Dict]] = None
```

## 4. API接口设计

### 4.1 测试用例管理API
```python
# GET /api/v1/test-cases - 获取测试用例列表
# POST /api/v1/test-cases - 创建测试用例（包含解析）
# GET /api/v1/test-cases/{case_id} - 获取单个测试用例
# PUT /api/v1/test-cases/{case_id} - 更新测试用例
# DELETE /api/v1/test-cases/{case_id} - 删除测试用例
```

### 4.2 测试执行API
```python
# POST /api/v1/test-execution/run - 同步执行测试
```

### 4.3 测试日志API
```python
# GET /api/v1/test-logs - 获取测试日志列表（支持按case_id筛选）
# GET /api/v1/test-logs/{log_id} - 获取单个测试日志
# DELETE /api/v1/test-logs/{log_id} - 删除测试日志
```

## 5. 核心功能实现

### 5.1 Raw Data解析逻辑
```python
def parse_llm_raw_data(raw_data: dict) -> ParsedLLMData:
    """解析logfire raw data，提取system prompt、user message和tools"""
    
    # 从http.request.body.text.messages中提取
    messages = raw_data.get("attributes", {}).get("http.request.body.text", {}).get("messages", [])
    tools = raw_data.get("attributes", {}).get("http.request.body.text", {}).get("tools", [])
    
    system_prompt = ""
    user_message = ""
    
    for message in messages:
        if message.get("role") == "system":
            system_prompt = message.get("content", "")
        elif message.get("role") == "user":
            user_message = message.get("content", "")
    
    return ParsedLLMData(
        system_prompt=system_prompt,
        user_message=user_message,
        tools=tools if tools else None
    )
```

### 5.2 LLM调用集成 - 完整Replay原始请求
```python
# 使用pydantic-ai的最底层用法：Direct Model Requests
from pydantic_ai.direct import model_request
from pydantic_ai.messages import ModelRequest, SystemPromptPart, UserPromptPart
from typing import Optional, List, Dict

async def execute_llm_test(
    model_name: str,
    original_messages: List[Dict],  # 除system prompt和最后一条user message外的其他messages
    original_tools: Optional[List[Dict]] = None,
    # 用户可能修改的参数
    system_prompt: str = "",
    user_message: str = "",
    modified_tools: Optional[List[Dict]] = None
) -> str:
    """执行LLM测试调用 - 通过拼接方式replay原始请求"""

    # 构建完整的replay messages
    replay_messages = []

    # 1. 添加system prompt（如果有）
    if system_prompt:
        replay_messages.append({
            "role": "system",
            "content": system_prompt
        })

    # 2. 添加原始messages中的其他消息
    replay_messages.extend(original_messages)

    # 3. 添加user message（如果有）
    if user_message:
        replay_messages.append({
            "role": "user",
            "content": user_message
        })

    # 构建pydantic-ai的消息格式
    pydantic_messages = []
    current_parts = []

    for message in replay_messages:
        role = message.get("role")
        content = message.get("content", "")

        if role == "system":
            current_parts.append(SystemPromptPart(content=content))
        elif role == "user":
            current_parts.append(UserPromptPart(content=content))
        # TODO: 可以根据需要添加其他类型的消息处理（assistant、tool等）

    if current_parts:
        pydantic_messages.append(ModelRequest(parts=current_parts))

    # 使用修改后的tools或原始tools
    tools_to_use = modified_tools if modified_tools is not None else original_tools

    # 构建model_request_parameters
    model_request_parameters = None
    if tools_to_use:
        # TODO: 将tools转换为pydantic-ai的ModelRequestParameters格式
        # 这里需要根据原始tools的格式进行转换
        pass

    # 直接调用模型（model_name已经是完整名称）
    model_response = await model_request(
        model=model_name,
        messages=pydantic_messages,
        model_request_parameters=model_request_parameters
    )

    # 提取响应内容
    if model_response.parts:
        # 获取第一个文本部分的内容
        for part in model_response.parts:
            if hasattr(part, 'content'):
                return part.content

    return ""
```

## 6. 前端页面设计

### 6.1 测试用例管理页面 (test_cases.html)
- 顶部：添加按钮
- 主体：测试用例列表表格
  - 列：ID、名称、创建时间、操作（编辑、删除、Play）
- 弹窗：添加/编辑测试用例
  - Case Name输入框
  - Case Data文本域（用于粘贴raw data JSON）

### 6.2 测试执行页面 (test_execution.html)
- 四个格子布局（2x2网格）
  - 左上：System Prompt（可编辑文本域）
  - 右上：User Message（可编辑文本域）
  - 左下：Tools（可编辑JSON文本域）
  - 右下：LLM Response（只读文本域）
- 顶部：模型选择下拉框、执行按钮
- 底部：返回按钮

### 6.3 测试日志页面 (test_logs.html)
- 顶部：筛选器（按测试用例筛选）
- 主体：测试日志列表表格
  - 列：执行时间、测试用例、模型、状态、响应时间、操作（查看详情、删除）
- 详情弹窗：显示完整的输入输出内容

## 7. 配置和部署

### 7.1 环境配置
```bash
# 在.env文件中添加
AI__OPENROUTER_API_KEY=your-openrouter-api-key
AI__DEFAULT_PROVIDER=openrouter
AI__DEFAULT_MODEL=anthropic/claude-sonnet-4
```

### 7.2 数据库迁移
```python
# 创建数据库表的迁移脚本
# 使用SQLAlchemy的create_all()或Alembic
```

## 8. 开发计划

### Phase 1: 基础功能（1-2周）
1. 数据模型定义和数据库表创建
2. 测试用例CRUD API实现
3. Raw data解析逻辑实现
4. 基础前端页面（测试用例管理）

### Phase 2: 核心功能（1-2周）
1. LLM调用集成
2. 测试执行API实现
3. 测试执行页面
4. 测试日志记录

### Phase 3: 完善功能（1周）
1. 测试日志查看页面
2. 筛选和搜索功能
3. 错误处理和用户体验优化
4. 测试和文档完善

## 9. 技术细节

### 9.1 错误处理
- API层统一错误处理
- 前端友好的错误提示
- LLM调用失败的重试机制

### 9.2 性能优化
- 数据库查询优化
- 前端分页加载
- Redis缓存常用数据

### 9.3 安全考虑
- API输入验证
- SQL注入防护
- XSS防护

## 10. 详细实现示例

### 10.1 测试用例服务实现
```python
# src/services/test_case_service.py
from typing import List, Optional
from src.models.test_case import TestCase
from src.stores.test_case_store import TestCaseStore
from src.services.llm_replay_service import parse_llm_raw_data
from src.utils.snowflake_generator import generate_snowflake_id

class TestCaseService:
    def __init__(self):
        self.store = TestCaseStore()

    async def create_test_case(self, name: str, raw_data: dict, description: Optional[str] = None) -> TestCase:
        """创建测试用例 - 创建时就进行解析"""
        case_id = generate_snowflake_id()

        # 解析raw_data
        try:
            parsed_data = parse_llm_raw_data(raw_data)
        except Exception as e:
            raise ValueError(f"Invalid raw data format: {e}")

        test_case = TestCase(
            id=case_id,
            name=name,
            raw_data=raw_data,
            original_messages=parsed_data.original_messages,
            original_tools=parsed_data.original_tools,
            original_model=parsed_data.original_model,
            parsed_system_prompt=parsed_data.system_prompt,
            parsed_user_message=parsed_data.user_message,
            description=description
        )

        return await self.store.create(test_case)

    async def get_test_cases(self, limit: int = 50, offset: int = 0) -> List[TestCase]:
        """获取测试用例列表"""
        return await self.store.get_all(limit=limit, offset=offset)

    async def get_test_case(self, case_id: str) -> Optional[TestCase]:
        """获取单个测试用例"""
        return await self.store.get_by_id(case_id)

    async def update_test_case(self, case_id: str, name: Optional[str] = None,
                              raw_data: Optional[dict] = None,
                              description: Optional[str] = None) -> Optional[TestCase]:
        """更新测试用例"""
        test_case = await self.store.get_by_id(case_id)
        if not test_case:
            return None

        if name is not None:
            test_case.name = name
        if raw_data is not None:
            # 重新解析raw_data
            try:
                parsed_data = parse_llm_raw_data(raw_data)
            except Exception as e:
                raise ValueError(f"Invalid raw data format: {e}")
            test_case.raw_data = raw_data
            test_case.original_messages = parsed_data.original_messages
            test_case.original_tools = parsed_data.original_tools
            test_case.original_model = parsed_data.original_model
            test_case.parsed_system_prompt = parsed_data.system_prompt
            test_case.parsed_user_message = parsed_data.user_message
        if description is not None:
            test_case.description = description

        return await self.store.update(test_case)

    async def delete_test_case(self, case_id: str) -> bool:
        """删除测试用例"""
        return await self.store.delete(case_id)
```

### 10.2 测试执行服务实现
```python
# src/services/test_execution_service.py
import time
from typing import Optional
from src.models.test_log import TestLog
from src.stores.test_log_store import TestLogStore
from src.services.llm_replay_service import execute_llm_test
from src.utils.snowflake_generator import generate_snowflake_id

class TestExecutionService:
    def __init__(self):
        self.log_store = TestLogStore()

    async def execute_test(self, test_case_id: str,
                          modified_system_prompt: Optional[str] = None,
                          modified_user_message: Optional[str] = None,
                          modified_tools: Optional[list] = None) -> TestLog:
        """同步执行测试 - 基于原始数据进行replay"""
        log_id = generate_snowflake_id()

        # 获取测试用例
        test_case = await self.test_case_store.get_by_id(test_case_id)
        if not test_case:
            raise ValueError("Test case not found")

        # 记录开始时间
        start_time = time.time()

        # 确定实际使用的参数（用户修改的或原始的）
        actual_system_prompt = modified_system_prompt or test_case.parsed_system_prompt
        actual_user_message = modified_user_message or test_case.parsed_user_message
        actual_tools = modified_tools or test_case.original_tools

        try:
            # 执行LLM调用 - 通过拼接方式replay原始请求
            response = await execute_llm_test(
                model_name=test_case.original_model,
                original_messages=test_case.original_messages,
                original_tools=test_case.original_tools,
                system_prompt=actual_system_prompt,
                user_message=actual_user_message,
                modified_tools=modified_tools
            )

            # 计算响应时间
            response_time_ms = int((time.time() - start_time) * 1000)

            # 创建成功的测试日志
            test_log = TestLog(
                id=log_id,
                test_case_id=test_case_id,
                model_name=test_case.original_model,
                system_prompt=actual_system_prompt,
                user_message=actual_user_message,
                tools=actual_tools,
                llm_response=response,
                response_time_ms=response_time_ms,
                status="success"
            )

        except Exception as e:
            # 创建失败的测试日志
            response_time_ms = int((time.time() - start_time) * 1000)
            test_log = TestLog(
                id=log_id,
                test_case_id=test_case_id,
                model_name=test_case.original_model,
                system_prompt=actual_system_prompt,
                user_message=actual_user_message,
                tools=actual_tools,
                response_time_ms=response_time_ms,
                status="failed",
                error_message=str(e)
            )

        # 保存测试日志
        return await self.log_store.create(test_log)
```

### 10.3 LLM回放服务实现
```python
# src/services/llm_replay_service.py
from typing import Optional, List, Dict, Any
from pydantic_ai.direct import model_request
from pydantic_ai.messages import ModelRequest, SystemPromptPart, UserPromptPart
from src.core.config import settings

# 这个函数已经在上面更新过了，这里是重复的，删除这个重复部分

def parse_llm_raw_data(raw_data: dict) -> 'ParsedLLMData':
    """解析logfire raw data，分离system prompt、最后一条user message和其他messages"""

    # 从http.request.body.text中提取完整的原始请求
    attributes = raw_data.get("attributes", {})
    request_body = attributes.get("http.request.body.text", {})

    # 提取原始数据
    all_messages = request_body.get("messages", [])
    original_tools = request_body.get("tools", [])
    original_model = request_body.get("model", "")

    # 分离system prompt和最后一条user message
    system_prompt = ""
    user_message = ""
    other_messages = []

    # 找到第一条system message
    system_message_index = -1
    for i, message in enumerate(all_messages):
        if message.get("role") == "system":
            system_prompt = message.get("content", "")
            system_message_index = i
            break

    # 找到最后一条user message
    last_user_message_index = -1
    for i in range(len(all_messages) - 1, -1, -1):
        if all_messages[i].get("role") == "user":
            user_message = all_messages[i].get("content", "")
            last_user_message_index = i
            break

    # 构建other_messages（除了第一条system和最后一条user之外的所有消息）
    for i, message in enumerate(all_messages):
        if i != system_message_index and i != last_user_message_index:
            other_messages.append(message)

    return ParsedLLMData(
        original_messages=other_messages,
        original_tools=original_tools if original_tools else None,
        original_model=original_model,
        system_prompt=system_prompt,
        user_message=user_message
    )
```

### 10.4 API端点实现示例
```python
# src/api/v1/endpoints/test_cases.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from src.services.test_case_service import TestCaseService
from src.api.schemas.test_case_schemas import (
    TestCaseCreate, TestCaseUpdate, TestCaseResponse, ParsedDataResponse
)

router = APIRouter()

def get_test_case_service() -> TestCaseService:
    return TestCaseService()

@router.get("/", response_model=List[TestCaseResponse])
async def get_test_cases(
    limit: int = 50,
    offset: int = 0,
    service: TestCaseService = Depends(get_test_case_service)
):
    """获取测试用例列表"""
    test_cases = await service.get_test_cases(limit=limit, offset=offset)
    return test_cases

@router.post("/", response_model=TestCaseResponse)
async def create_test_case(
    request: TestCaseCreate,
    service: TestCaseService = Depends(get_test_case_service)
):
    """创建测试用例"""
    try:
        test_case = await service.create_test_case(
            name=request.name,
            raw_data=request.raw_data,
            description=request.description
        )
        return test_case
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{case_id}", response_model=TestCaseResponse)
async def get_test_case(
    case_id: str,
    service: TestCaseService = Depends(get_test_case_service)
):
    """获取单个测试用例"""
    test_case = await service.get_test_case(case_id)
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")
    return test_case

@router.put("/{case_id}", response_model=TestCaseResponse)
async def update_test_case(
    case_id: str,
    request: TestCaseUpdate,
    service: TestCaseService = Depends(get_test_case_service)
):
    """更新测试用例"""
    try:
        test_case = await service.update_test_case(
            case_id=case_id,
            name=request.name,
            raw_data=request.raw_data,
            description=request.description
        )
        if not test_case:
            raise HTTPException(status_code=404, detail="Test case not found")
        return test_case
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{case_id}")
async def delete_test_case(
    case_id: str,
    service: TestCaseService = Depends(get_test_case_service)
):
    """删除测试用例"""
    success = await service.delete_test_case(case_id)
    if not success:
        raise HTTPException(status_code=404, detail="Test case not found")
    return {"message": "Test case deleted successfully"}

# 移除parse接口，因为创建时就已经解析了
```

## 11. 前端实现细节

### 11.1 测试用例管理页面JavaScript
```javascript
// static/js/test_cases.js
class TestCaseManager {
    constructor() {
        this.apiBase = '/api/v1/test-cases';
        this.init();
    }

    init() {
        this.loadTestCases();
        this.bindEvents();
    }

    async loadTestCases() {
        try {
            const response = await fetch(this.apiBase);
            const testCases = await response.json();
            this.renderTestCases(testCases);
        } catch (error) {
            console.error('Failed to load test cases:', error);
            this.showError('加载测试用例失败');
        }
    }

    renderTestCases(testCases) {
        const tbody = document.getElementById('test-cases-tbody');
        tbody.innerHTML = '';

        testCases.forEach(testCase => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${testCase.id}</td>
                <td>${testCase.name}</td>
                <td>${new Date(testCase.created_at).toLocaleString()}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="testCaseManager.editTestCase('${testCase.id}')">编辑</button>
                    <button class="btn btn-sm btn-danger" onclick="testCaseManager.deleteTestCase('${testCase.id}')">删除</button>
                    <button class="btn btn-sm btn-success" onclick="testCaseManager.playTestCase('${testCase.id}')">Play</button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    async createTestCase(name, rawData, description) {
        try {
            const response = await fetch(this.apiBase, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: name,
                    raw_data: JSON.parse(rawData),
                    description: description
                })
            });

            if (response.ok) {
                this.loadTestCases();
                this.hideModal();
                this.showSuccess('测试用例创建成功');
            } else {
                const error = await response.json();
                this.showError(error.detail || '创建失败');
            }
        } catch (error) {
            console.error('Failed to create test case:', error);
            this.showError('创建测试用例失败');
        }
    }

    async deleteTestCase(caseId) {
        if (!confirm('确定要删除这个测试用例吗？')) {
            return;
        }

        try {
            const response = await fetch(`${this.apiBase}/${caseId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.loadTestCases();
                this.showSuccess('测试用例删除成功');
            } else {
                this.showError('删除失败');
            }
        } catch (error) {
            console.error('Failed to delete test case:', error);
            this.showError('删除测试用例失败');
        }
    }

    playTestCase(caseId) {
        // 跳转到测试执行页面
        window.location.href = `/test-execution?case_id=${caseId}`;
    }

    bindEvents() {
        // 绑定添加按钮事件
        document.getElementById('add-test-case-btn').addEventListener('click', () => {
            this.showAddModal();
        });

        // 绑定表单提交事件
        document.getElementById('test-case-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleFormSubmit();
        });
    }

    showAddModal() {
        document.getElementById('modal-title').textContent = '添加测试用例';
        document.getElementById('test-case-form').reset();
        $('#test-case-modal').modal('show');
    }

    hideModal() {
        $('#test-case-modal').modal('hide');
    }

    handleFormSubmit() {
        const name = document.getElementById('case-name').value;
        const rawData = document.getElementById('case-data').value;
        const description = document.getElementById('case-description').value;

        this.createTestCase(name, rawData, description);
    }

    showSuccess(message) {
        // 显示成功提示
        this.showAlert(message, 'success');
    }

    showError(message) {
        // 显示错误提示
        this.showAlert(message, 'danger');
    }

    showAlert(message, type) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="close" data-dismiss="alert">
                <span>&times;</span>
            </button>
        `;

        document.getElementById('alerts-container').appendChild(alertDiv);

        // 3秒后自动消失
        setTimeout(() => {
            alertDiv.remove();
        }, 3000);
    }
}

// 初始化
const testCaseManager = new TestCaseManager();
```

## 12. 部署配置

### 12.1 Docker配置更新
```dockerfile
# 在现有Dockerfile基础上，确保包含前端静态文件
COPY templates/ /app/templates/
COPY static/ /app/static/
```

### 12.2 环境变量配置
```bash
# .env文件新增配置
AI__OPENROUTER_API_KEY=your-openrouter-api-key
AI__REPLAY_DEFAULT_MODEL=anthropic/claude-sonnet-4

# 数据库配置（如果需要新表）
DATABASE__AUTO_CREATE_TABLES=true
```

### 12.3 启动脚本更新
```python
# main.py中添加静态文件服务
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
```

## 13. 数据库Schema定义

### 13.1 创建表的SQL脚本
```sql
-- 测试用例表
CREATE TABLE test_cases (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    raw_data JSONB NOT NULL,
    original_messages JSONB NOT NULL,
    original_tools JSONB,
    original_model VARCHAR(255) NOT NULL,
    parsed_system_prompt TEXT NOT NULL,
    parsed_user_message TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 测试日志表
CREATE TABLE test_logs (
    id VARCHAR(255) PRIMARY KEY,
    test_case_id VARCHAR(255) REFERENCES test_cases(id) ON DELETE CASCADE,
    model_name VARCHAR(100) NOT NULL,
    system_prompt TEXT NOT NULL,
    user_message TEXT NOT NULL,
    tools JSONB,
    llm_response TEXT,
    response_time_ms INTEGER,
    status VARCHAR(20) DEFAULT 'success',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_test_logs_test_case_id ON test_logs(test_case_id);
CREATE INDEX idx_test_logs_created_at ON test_logs(created_at);
CREATE INDEX idx_test_logs_status ON test_logs(status);
```

### 13.2 数据库初始化脚本
```python
# src/stores/database_init.py
from sqlalchemy import text
from src.stores.database import get_database_engine

async def init_database():
    """初始化数据库表"""
    engine = get_database_engine()

    # 读取SQL文件并执行
    with open("sql/init_tables.sql", "r") as f:
        sql_content = f.read()

    async with engine.begin() as conn:
        await conn.execute(text(sql_content))
```

## 14. 前端模板文件

### 14.1 测试用例管理页面模板
```html
<!-- templates/test_cases.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM测试用例管理</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-4">
        <div class="row">
            <div class="col-12">
                <h1>LLM测试用例管理</h1>

                <!-- 操作按钮 -->
                <div class="mb-3">
                    <button id="add-test-case-btn" class="btn btn-primary">添加测试用例</button>
                    <a href="/test-logs" class="btn btn-secondary">查看测试日志</a>
                </div>

                <!-- 提示信息容器 -->
                <div id="alerts-container"></div>

                <!-- 测试用例列表 -->
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>名称</th>
                                <th>创建时间</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="test-cases-tbody">
                            <!-- 动态加载内容 -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- 添加/编辑测试用例模态框 -->
    <div class="modal fade" id="test-case-modal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="modal-title">添加测试用例</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="test-case-form">
                        <div class="mb-3">
                            <label for="case-name" class="form-label">Case Name</label>
                            <input type="text" class="form-control" id="case-name" required>
                        </div>
                        <div class="mb-3">
                            <label for="case-data" class="form-label">Case Data (JSON)</label>
                            <textarea class="form-control" id="case-data" rows="10"
                                      placeholder="请粘贴logfire raw data JSON内容" required></textarea>
                        </div>
                        <div class="mb-3">
                            <label for="case-description" class="form-label">描述 (可选)</label>
                            <textarea class="form-control" id="case-description" rows="3"></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                    <button type="submit" form="test-case-form" class="btn btn-primary">保存</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/static/js/test_cases.js"></script>
</body>
</html>
```

### 14.2 测试执行页面模板
```html
<!-- templates/test_execution.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM测试执行</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .execution-grid {
            height: 70vh;
        }
        .grid-item {
            height: 100%;
        }
        .grid-textarea {
            height: calc(100% - 40px);
            resize: none;
        }
        .readonly {
            background-color: #f8f9fa;
        }
    </style>
</head>
<body>
    <div class="container-fluid mt-3">
        <!-- 顶部控制栏 -->
        <div class="row mb-3">
            <div class="col-12">
                <div class="d-flex justify-content-between align-items-center">
                    <h2>LLM测试执行</h2>
                    <div>
                        <a href="/test-cases" class="btn btn-secondary">返回列表</a>
                    </div>
                </div>
            </div>
        </div>

        <!-- 模型选择和执行控制 -->
        <div class="row mb-3">
            <div class="col-md-6">
                <label for="model-select" class="form-label">选择模型</label>
                <input type="text" class="form-control" id="model-select"
                       value="anthropic/claude-sonnet-4" placeholder="输入模型名称">
            </div>
            <div class="col-md-6 d-flex align-items-end">
                <button id="execute-btn" class="btn btn-success me-2">执行测试</button>
                <button id="clear-response-btn" class="btn btn-warning">清空响应</button>
            </div>
        </div>

        <!-- 提示信息容器 -->
        <div id="alerts-container"></div>

        <!-- 四格布局 -->
        <div class="row execution-grid">
            <!-- 左上：System Prompt -->
            <div class="col-md-6 mb-3">
                <div class="card grid-item">
                    <div class="card-header">
                        <h5 class="mb-0">System Prompt</h5>
                    </div>
                    <div class="card-body">
                        <textarea id="system-prompt" class="form-control grid-textarea"
                                  placeholder="System prompt will be loaded here..."></textarea>
                    </div>
                </div>
            </div>

            <!-- 右上：User Message -->
            <div class="col-md-6 mb-3">
                <div class="card grid-item">
                    <div class="card-header">
                        <h5 class="mb-0">User Message</h5>
                    </div>
                    <div class="card-body">
                        <textarea id="user-message" class="form-control grid-textarea"
                                  placeholder="User message will be loaded here..."></textarea>
                    </div>
                </div>
            </div>

            <!-- 左下：Tools -->
            <div class="col-md-6">
                <div class="card grid-item">
                    <div class="card-header">
                        <h5 class="mb-0">Tools (JSON)</h5>
                    </div>
                    <div class="card-body">
                        <textarea id="tools" class="form-control grid-textarea"
                                  placeholder="Tools JSON will be loaded here..."></textarea>
                    </div>
                </div>
            </div>

            <!-- 右下：LLM Response -->
            <div class="col-md-6">
                <div class="card grid-item">
                    <div class="card-header">
                        <h5 class="mb-0">LLM Response</h5>
                    </div>
                    <div class="card-body">
                        <textarea id="llm-response" class="form-control grid-textarea readonly"
                                  readonly placeholder="LLM response will appear here..."></textarea>
                    </div>
                </div>
            </div>
        </div>

        <!-- 执行状态 -->
        <div class="row mt-3">
            <div class="col-12">
                <div id="execution-status" class="text-muted"></div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/static/js/test_execution.js"></script>
</body>
</html>
```

## 15. 配置文件更新

### 15.1 核心配置更新
```python
# src/core/config.py 添加新的配置项
class Settings(BaseSettings):
    # ... 现有配置 ...

    # LLM Replay System 配置
    ai__openrouter_api_key: SecretStr = Field(default="", description="OpenRouter API Key")
    ai__replay_default_model: str = Field(default="anthropic/claude-sonnet-4", description="默认测试模型")

    # 前端配置
    frontend__page_size: int = Field(default=50, description="页面默认分页大小")
    frontend__max_response_length: int = Field(default=10000, description="最大响应长度显示")

    # 测试执行配置
    test__execution_timeout: int = Field(default=300, description="测试执行超时时间(秒)")
    test__max_concurrent_tests: int = Field(default=5, description="最大并发测试数")
```

### 15.2 路由注册
```python
# src/api/v1/__init__.py 添加新路由
from .endpoints import test_cases, test_execution, test_logs

# 注册路由
app.include_router(test_cases.router, prefix="/test-cases", tags=["test-cases"])
app.include_router(test_execution.router, prefix="/test-execution", tags=["test-execution"])
app.include_router(test_logs.router, prefix="/test-logs", tags=["test-logs"])
```

### 15.3 页面路由
```python
# src/api/v1/endpoints/pages.py - 前端页面路由
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/test-cases", response_class=HTMLResponse)
async def test_cases_page(request: Request):
    """测试用例管理页面"""
    return templates.TemplateResponse("test_cases.html", {"request": request})

@router.get("/test-execution", response_class=HTMLResponse)
async def test_execution_page(request: Request):
    """测试执行页面"""
    return templates.TemplateResponse("test_execution.html", {"request": request})

@router.get("/test-logs", response_class=HTMLResponse)
async def test_logs_page(request: Request):
    """测试日志页面"""
    return templates.TemplateResponse("test_logs.html", {"request": request})
```

## 16. 开发和测试指南

### 16.1 本地开发环境设置
```bash
# 1. 安装依赖
make setup

# 2. 配置环境变量
cp env.sample .env
# 编辑.env文件，添加OpenRouter API Key

# 3. 初始化数据库
python -c "from src.stores.database_init import init_database; import asyncio; asyncio.run(init_database())"

# 4. 启动开发服务器
make run-api-dev
```

### 16.2 测试数据准备
```python
# scripts/create_test_data.py
import asyncio
import json
from src.services.test_case_service import TestCaseService

async def create_sample_test_case():
    """创建示例测试用例"""
    service = TestCaseService()

    # 使用提供的示例数据
    with open("docs/logfire_llm_call_raw_data.json", "r") as f:
        raw_data = json.load(f)

    await service.create_test_case(
        name="示例测试用例",
        raw_data=raw_data,
        description="基于logfire数据的示例测试用例"
    )

    print("示例测试用例创建成功")

if __name__ == "__main__":
    asyncio.run(create_sample_test_case())
```

### 16.3 API测试脚本
```bash
# 测试API端点
curl -X GET "http://localhost:8080/api/v1/test-cases"
curl -X POST "http://localhost:8080/api/v1/test-cases" \
  -H "Content-Type: application/json" \
  -d '{"name": "测试用例", "raw_data": {...}, "description": "测试描述"}'
```

## 17. 关键技术说明

### 17.1 关于mapped_column
`mapped_column` 是 SQLAlchemy 2.0+ 引入的新语法，用于替代旧的 `Column()` 语法：

**优势：**
- 更好的类型提示支持
- 与 `Mapped[]` 类型注解完美配合
- IDE 自动补全和类型检查
- 更清晰的代码结构

**示例对比：**
```python
# 旧语法 (SQLAlchemy 1.x)
class User(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)

# 新语法 (SQLAlchemy 2.0+)
class User(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
```

### 17.2 设计要点总结

1. **数据存储策略**：
   - 存储原始raw data和完整的原始请求数据（messages、tools、model）
   - 额外存储解析后的关键信息用于页面展示
   - 创建时就进行解析，避免重复解析

2. **Replay机制**：
   - 分离存储：system prompt + 其他messages + 最后一条user message
   - 支持用户修改system prompt、user message、tools
   - Replay时通过拼接重建完整请求：system + other_messages + user
   - 避免查找替换，直接拼接，更高效
   - model_name直接使用完整名称（如"openrouter:anthropic/claude-sonnet-4"）

3. **LLM调用方式**：
   - 使用pydantic-ai的Direct Model Requests
   - 最底层的调用方式，完全控制请求结构
   - 支持完整的原始请求replay

4. **执行模式**：
   - 同步执行，简化状态管理
   - 直接返回结果，无需轮询状态

5. **API设计**：
   - 简化接口，移除不必要的parse端点
   - 专注核心功能：CRUD + 执行 + 日志

## 18. 实施总结

这个技术实施文档提供了完整的系统设计和实现指南，包括：

1. **完整的架构设计** - 基于现有项目的分层架构
2. **详细的数据模型** - 使用SQLAlchemy 2.0+语法，存储原始和解析数据
3. **API接口设计** - 简化的RESTful API设计
4. **前端实现** - 包含HTML模板和JavaScript逻辑
5. **核心业务逻辑** - 使用Direct Model Requests的LLM调用
6. **配置和部署** - 环境配置和部署指南
7. **开发指南** - 本地开发和测试的完整流程

**核心特性：**
- ✅ 无需登录的简单页面
- ✅ 测试用例管理（CRUD + Play）
- ✅ 四格测试执行界面
- ✅ 模型选择功能
- ✅ 测试日志记录和筛选
- ✅ 同步执行，简化状态管理
- ✅ 使用pydantic-ai Direct Model Requests

您可以按照这个文档逐步实现LLM测试回放系统。需要我详细解释任何部分或者开始实际的代码实现吗？
