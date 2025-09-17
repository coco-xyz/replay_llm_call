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
│   ├── base.py               # 基础模型（BaseDBModel）
│   ├── test_case.py          # 测试用例模型
│   └── test_log.py           # 测试日志模型
├── stores/
│   ├── test_case_store.py    # 测试用例数据访问
│   └── test_log_store.py     # 测试日志数据访问
├── services/
│   ├── test_case_service.py  # 测试用例业务逻辑
│   ├── test_execution_service.py # 测试执行业务逻辑
│   ├── test_log_service.py   # 测试日志业务逻辑
│   ├── llm_parser_service.py # LLM数据解析服务
│   └── llm_execution_service.py # LLM执行服务（使用pydantic-ai Direct Model Requests）
├── agents/
│   └── demo_agent.py         # 演示代理（示例pydantic-ai代理）
├── api/
│   └── v1/
│       └── endpoints/
│           ├── test_cases.py # 测试用例API
│           ├── test_execution.py # 测试执行API
│           └── test_logs.py  # 测试日志API
├── templates/                # 前端模板
│   ├── test_cases.html       # 测试用例管理页面
│   ├── test_execution.html   # 测试执行页面
│   └── test_logs.html        # 测试日志页面
└── static/                   # 静态文件
    └── js/                   # JavaScript文件
        ├── test-cases.js     # 测试用例管理页面脚本
        ├── test-execution.js # 测试执行页面脚本
        └── test-logs.js      # 测试日志页面脚本
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
from sqlalchemy import String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional

# mapped_column 是 SQLAlchemy 2.0+ 的新语法，用于定义表列的映射
# 它提供了更好的类型提示和IDE支持，替代了旧的 Column() 语法

class TestCase(BaseDBModel):  # 继承自BaseDBModel，包含id、created_at、updated_at
    __tablename__ = "test_cases"

    # 基本信息
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 存储原始的logfire raw data（用于审计和参考）
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)

    # 分离存储以实现高效replay
    # middle_messages包含除第一条system prompt和最后一条user message之外的所有消息
    middle_messages: Mapped[List[dict]] = mapped_column(JSON, nullable=False)
    tools: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # 解析出的关键组件，用于显示和replay
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    last_user_message: Mapped[str] = mapped_column(Text, nullable=False)

    # 关联测试日志
    test_logs: Mapped[List["TestLog"]] = relationship(
        "TestLog", 
        back_populates="test_case",
        cascade="all, delete-orphan"
    )
```

### 3.2 测试日志模型 (TestLog)
```python
from sqlalchemy import String, Text, JSON, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

class TestLog(BaseDBModel):  # 继承自BaseDBModel，包含id、created_at、updated_at
    __tablename__ = "test_logs"

    # 关联测试用例
    test_case_id: Mapped[str] = mapped_column(
        String, 
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False
    )

    # 模型信息
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # 输入数据（执行时的实际参数，可能被用户修改过）
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    tools: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 输出数据
    llm_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 执行状态（同步执行：success 或 failed）
    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 关联测试用例
    test_case: Mapped["TestCase"] = relationship(
        "TestCase", 
        back_populates="test_logs"
    )
```

### 3.3 LLM数据解析模型
```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class ParsedLLMData(BaseModel):
    """从logfire raw data解析后的LLM数据，用于服务层使用"""
    
    # 原始数据（用于replay拼接）
    middle_messages: List[Dict] = Field(..., description="除system prompt和最后一条user message外的消息")
    tools: Optional[List[Dict]] = Field(None, description="工具配置")
    model_name: str = Field(..., description="模型名称")

    # 解析出的关键数据（用于页面显示和replay拼接）
    system_prompt: str = Field(..., description="系统提示词")
    last_user_message: str = Field(..., description="最后一条用户消息")

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
    """
    解析logfire raw data，分离system prompt、最后一条user message和其他messages。
    
    实现优化的存储策略：
    - System prompt（第一条system message）单独提取
    - 最后一条user message单独提取  
    - 所有其他messages存储在middle_messages中用于replay拼接
    
    Args:
        raw_data: 包含LLM请求的原始logfire数据
        
    Returns:
        ParsedLLMData: 分离组件的解析数据
        
    Raises:
        ValueError: 如果raw data格式无效
        KeyError: 如果缺少必需字段
    """
    try:
        # 从logfire数据中提取请求体
        attributes = raw_data.get("attributes", {})
        request_body = attributes.get("http.request.body.text", {})
        
        # 提取原始数据
        all_messages = request_body.get("messages", [])
        tools = request_body.get("tools", [])
        model_name = request_body.get("model", "")
        
        # 分离system prompt和最后一条user message
        system_prompt = ""
        last_user_message = ""
        middle_messages = []
        
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
                last_user_message = all_messages[i].get("content", "")
                last_user_message_index = i
                break
        
        # 构建middle_messages（除了第一条system和最后一条user之外的所有消息）
        for i, message in enumerate(all_messages):
            if i != system_message_index and i != last_user_message_index:
                middle_messages.append(message)
        
        return ParsedLLMData(
            middle_messages=middle_messages,
            tools=tools if tools else None,
            model_name=model_name,
            system_prompt=system_prompt,
            last_user_message=last_user_message
        )
        
    except Exception as e:
        logger.error(f"Failed to parse LLM raw data: {e}")
        raise ValueError(f"Invalid raw data format: {e}")
```

### 5.2 LLM调用集成 - 使用pydantic-ai Direct Model Requests
```python
# 使用pydantic-ai的Direct Model Requests进行LLM调用
from pydantic_ai.direct import model_request
from pydantic_ai.messages import (
    ModelRequest,
    SystemPromptPart,
    UserPromptPart,
    ToolReturnPart,
    TextPart,
    ToolCallPart,
)
from pydantic_ai.models import ModelRequestParameters
from src.core.llm_factory import create_llm_model

async def execute_llm_test(
    model_name: str,
    middle_messages: List[Dict],  # 除system prompt和最后一条user message外的其他messages
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

    # 2. 添加middle_messages中的其他消息
    replay_messages.extend(middle_messages)

    # 3. 添加user message（如果有）
    if user_message:
        replay_messages.append({
            "role": "user",
            "content": user_message
        })

    # 转换为pydantic-ai消息格式
    pydantic_messages = convert_messages_to_pydantic_ai(replay_messages)

    # 使用修改后的tools或原始tools
    tools_to_use = modified_tools if modified_tools is not None else original_tools
    
    # 转换tools为pydantic-ai格式
    model_request_parameters = None
    if tools_to_use:
        model_request_parameters = convert_logfire_tools_to_pydantic_ai(tools_to_use)

    # 创建模型实例（从model_name解析provider和model）
    provider, model = parse_model_name(model_name)
    llm_model = create_llm_model(model, provider)

    # 直接调用模型
    model_response = await model_request(
        model=llm_model,
        messages=pydantic_messages,
        model_request_parameters=model_request_parameters
    )

    # 提取响应内容
    return extract_response_text(model_response)

def convert_messages_to_pydantic_ai(messages: List[Dict]) -> List[ModelRequest]:
    """将消息转换为pydantic-ai格式"""
    # 实现消息格式转换逻辑
    pass

def convert_logfire_tools_to_pydantic_ai(tools: List[Dict]) -> ModelRequestParameters:
    """将logfire工具格式转换为pydantic-ai ModelRequestParameters格式"""
    # 实现工具格式转换逻辑
    pass

def parse_model_name(model_name: str) -> tuple[str, str]:
    """解析模型名称，返回(provider, model)"""
    # 实现模型名称解析逻辑
    pass

def extract_response_text(response) -> str:
    """从模型响应中提取文本内容"""
    # 实现响应文本提取逻辑
    pass
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
CREATE TABLE IF NOT EXISTS test_cases (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    raw_data JSONB NOT NULL,
    middle_messages JSONB NOT NULL,
    tools JSONB,
    model_name VARCHAR(255) NOT NULL,
    system_prompt TEXT NOT NULL,
    last_user_message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 测试日志表
CREATE TABLE IF NOT EXISTS test_logs (
    id VARCHAR(255) PRIMARY KEY,
    test_case_id VARCHAR(255) NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,
    model_name VARCHAR(100) NOT NULL,
    system_prompt TEXT NOT NULL,
    user_message TEXT NOT NULL,
    tools JSONB,
    llm_response TEXT,
    response_time_ms INTEGER,
    status VARCHAR(20) DEFAULT 'success' NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 创建索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_test_cases_name ON test_cases(name);
CREATE INDEX IF NOT EXISTS idx_test_cases_created_at ON test_cases(created_at);
CREATE INDEX IF NOT EXISTS idx_test_logs_test_case_id ON test_logs(test_case_id);
CREATE INDEX IF NOT EXISTS idx_test_logs_status ON test_logs(status);
CREATE INDEX IF NOT EXISTS idx_test_logs_created_at ON test_logs(created_at);

-- 注释说明
COMMENT ON TABLE test_cases IS 'Stores LLM test cases with original and parsed data for replay';
COMMENT ON TABLE test_logs IS 'Stores execution logs and results for LLM test runs';

COMMENT ON COLUMN test_cases.raw_data IS 'Original logfire raw data for audit purposes';
COMMENT ON COLUMN test_cases.middle_messages IS 'Messages except system prompt and last user message';
COMMENT ON COLUMN test_cases.tools IS 'Tools definition from the request';
COMMENT ON COLUMN test_cases.model_name IS 'Model name used in original request';
COMMENT ON COLUMN test_cases.system_prompt IS 'Extracted system prompt for display and replay';
COMMENT ON COLUMN test_cases.last_user_message IS 'Extracted last user message for display and replay';

COMMENT ON COLUMN test_logs.system_prompt IS 'Actual system prompt used in execution (may be modified)';
COMMENT ON COLUMN test_logs.user_message IS 'Actual user message used in execution (may be modified)';
COMMENT ON COLUMN test_logs.tools IS 'Actual tools used in execution (may be modified)';
COMMENT ON COLUMN test_logs.status IS 'Execution status: success or failed';
COMMENT ON COLUMN test_logs.response_time_ms IS 'Response time in milliseconds';
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
# src/core/config.py 现有配置已包含LLM相关设置
class Settings(BaseSettings):
    # ... 现有配置 ...

    # AI API Keys (已有配置)
    ai__openrouter_api_key: Optional[SecretStr] = Field(
        default=None, description="OpenRouter API key"
    )
    ai__anthropic_api_key: Optional[SecretStr] = Field(
        default=None, description="Anthropic API key"
    )
    # ... 其他AI配置 ...

    # 模型配置 (已有配置)
    ai__default_model__provider: str = Field(
        default="openrouter", description="Default model provider"
    )
    ai__default_model__name: str = Field(
        default="openai/gpt-4o-mini", description="Default model name"
    )

    # 可以添加LLM Replay System特定配置
    # frontend__page_size: int = Field(default=50, description="页面默认分页大小")
    # frontend__max_response_length: int = Field(default=10000, description="最大响应长度显示")
    # test__execution_timeout: int = Field(default=300, description="测试执行超时时间(秒)")
```

### 15.2 路由注册
```python
# 在main.py或api/router.py中注册路由
from src.api.v1.endpoints import test_cases, test_execution, test_logs
from src.api.pages import router as pages_router

# 注册API路由
app.include_router(test_cases.router, prefix="/api/v1/test-cases", tags=["test-cases"])
app.include_router(test_execution.router, prefix="/api/v1/test-execution", tags=["test-execution"])
app.include_router(test_logs.router, prefix="/api/v1/test-logs", tags=["test-logs"])

# 注册页面路由
app.include_router(pages_router, tags=["pages"])

# 静态文件服务
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")
```

### 15.3 页面路由
```python
# src/api/pages.py - 前端页面路由
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """主页 - 重定向到测试用例页面"""
    return templates.TemplateResponse("test_cases.html", {"request": request})

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

## 18. 实施现状与设计对比

### 18.1 关键实现差异

**数据模型字段命名变化：**
- `original_messages` → `middle_messages` （更准确描述中间消息）
- `original_tools` → `tools` （简化命名）
- `original_model` → `model_name` （简化命名）
- `parsed_system_prompt` → `system_prompt` （简化命名）
- `parsed_user_message` → `last_user_message` （更准确描述最后一条用户消息）

**服务层架构：**
- 实际实现分离了 `llm_parser_service.py` 和 `llm_execution_service.py`
- 移除了设计中的 `llm_replay_service.py`，功能分散到专门的服务中
- 添加了 `test_log_service.py` 独立处理日志业务逻辑

**模型继承结构：**
- 所有模型都继承自 `BaseDBModel`，自动包含 `id`、`created_at`、`updated_at` 字段
- 无需在每个模型中重复定义这些基础字段

**LLM集成方式：**
- 使用现有的 `llm_factory.py` 创建模型实例
- 通过 `parse_model_name()` 函数解析模型名称和提供商
- 完整的工具格式转换逻辑已实现

### 18.2 已实现的核心功能

**✅ 已完成功能：**
- 完整的数据模型定义（TestCase、TestLog）
- 数据库表结构和索引
- 完整的API端点实现
- 前端页面和JavaScript逻辑
- LLM数据解析服务
- LLM执行服务（使用pydantic-ai Direct Model Requests）
- 测试用例、执行、日志的完整业务逻辑
- 页面路由和静态文件服务

**✅ 技术特性：**
- SQLAlchemy 2.0+ 语法和类型提示
- pydantic-ai Direct Model Requests集成
- 分层架构设计
- 完整的错误处理
- 响应时间监控
- 级联删除关系

### 18.3 系统架构优势

1. **优化的存储策略** - 通过分离存储system prompt、middle messages和last user message，实现高效的replay机制
2. **类型安全** - 使用SQLAlchemy 2.0+的Mapped类型注解，提供完整的类型检查
3. **模块化设计** - 清晰的服务层分离，每个服务专注特定功能
4. **扩展性** - 基于现有的LLM工厂模式，易于添加新的模型提供商
5. **可维护性** - 标准化的API设计和错误处理

## 19. 实施总结

这个技术实施文档现在准确反映了当前的系统实现，包括：

1. **完整的架构设计** - 基于现有项目的分层架构
2. **详细的数据模型** - 使用SQLAlchemy 2.0+语法，准确的字段命名
3. **API接口设计** - 与实际实现一致的RESTful API设计
4. **前端实现** - 包含HTML模板和JavaScript逻辑
5. **核心业务逻辑** - 使用pydantic-ai Direct Model Requests的LLM调用
6. **配置和部署** - 基于现有配置系统的环境配置
7. **开发指南** - 本地开发和测试的完整流程

**核心特性：**
- ✅ 无需登录的简单页面
- ✅ 测试用例管理（CRUD + Play）
- ✅ 四格测试执行界面
- ✅ 模型选择功能
- ✅ 测试日志记录和筛选
- ✅ 同步执行，简化状态管理
- ✅ 使用pydantic-ai Direct Model Requests
- ✅ 完整的错误处理和监控

文档现已与实际代码实现保持一致，可以作为系统维护和扩展的准确参考。
