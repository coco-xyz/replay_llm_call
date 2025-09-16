# API结构重构文档

## 概述

本文档记录了LLM Replay System API结构的重构，将API端点从 `src/api/` 目录移动到 `src/api/v1/endpoints/` 目录，以遵循原有的框架设计。

## 重构前后对比

### 重构前的结构
```
src/api/
├── __init__.py
├── factory.py
├── router.py
├── pages.py
├── test_cases.py          # ❌ 不符合框架设计
├── test_execution.py      # ❌ 不符合框架设计
├── test_logs.py           # ❌ 不符合框架设计
└── v1/
    ├── __init__.py
    └── endpoints/
        ├── __init__.py
        ├── demo.py
        └── health.py
```

### 重构后的结构
```
src/api/
├── __init__.py
├── factory.py
├── router.py
├── pages.py
└── v1/
    ├── __init__.py
    └── endpoints/
        ├── __init__.py
        ├── demo.py
        ├── health.py
        ├── test_cases.py      # ✅ 符合框架设计
        ├── test_execution.py  # ✅ 符合框架设计
        └── test_logs.py       # ✅ 符合框架设计
```

## 文件变更详情

### 移动的文件

#### 1. `src/api/test_cases.py` → `src/api/v1/endpoints/test_cases.py`
- **路由前缀**: `/api/test-cases`
- **标签**: `["test-cases"]`
- **端点**:
  - `POST /` - 创建测试用例
  - `GET /` - 获取测试用例列表
  - `GET /search` - 搜索测试用例
  - `GET /{test_case_id}` - 获取单个测试用例
  - `PUT /{test_case_id}` - 更新测试用例
  - `DELETE /{test_case_id}` - 删除测试用例

#### 2. `src/api/test_execution.py` → `src/api/v1/endpoints/test_execution.py`
- **路由前缀**: `/api/test-execution`
- **标签**: `["test-execution"]`
- **端点**:
  - `POST /execute` - 执行测试
  - `POST /execute/{test_case_id}` - 按ID执行测试

#### 3. `src/api/test_logs.py` → `src/api/v1/endpoints/test_logs.py`
- **路由前缀**: `/api/test-logs`
- **标签**: `["test-logs"]`
- **端点**:
  - `GET /` - 获取测试日志列表
  - `GET /{log_id}` - 获取单个测试日志
  - `GET /test-case/{test_case_id}` - 获取测试用例的日志
  - `GET /filter/status/{status}` - 按状态过滤日志
  - `GET /filter/combined` - 组合过滤日志
  - `DELETE /{log_id}` - 删除测试日志
  - `DELETE /test-case/{test_case_id}` - 删除测试用例的所有日志

### 更新的文件

#### 1. `src/api/v1/__init__.py`
**变更前**:
```python
from src.api.test_cases import router as test_cases_router
from src.api.test_execution import router as test_execution_router
from src.api.test_logs import router as test_logs_router
```

**变更后**:
```python
from .endpoints.test_cases import router as test_cases_router
from .endpoints.test_execution import router as test_execution_router
from .endpoints.test_logs import router as test_logs_router
```

#### 2. `src/api/__init__.py`
移除了对已移动文件的导入，简化了导出列表。

## API路径结构

### 完整的API路径映射

| 功能 | HTTP方法 | 完整路径 | 描述 |
|------|----------|----------|------|
| **健康检查** | GET | `/v1/health` | 系统健康状态 |
| **演示** | POST | `/v1/demo/chat` | 演示聊天功能 |
| **测试用例** | POST | `/v1/api/test-cases/` | 创建测试用例 |
| | GET | `/v1/api/test-cases/` | 获取测试用例列表 |
| | GET | `/v1/api/test-cases/search` | 搜索测试用例 |
| | GET | `/v1/api/test-cases/{id}` | 获取单个测试用例 |
| | PUT | `/v1/api/test-cases/{id}` | 更新测试用例 |
| | DELETE | `/v1/api/test-cases/{id}` | 删除测试用例 |
| **测试执行** | POST | `/v1/api/test-execution/execute` | 执行测试 |
| | POST | `/v1/api/test-execution/execute/{id}` | 按ID执行测试 |
| **测试日志** | GET | `/v1/api/test-logs/` | 获取测试日志列表 |
| | GET | `/v1/api/test-logs/{id}` | 获取单个测试日志 |
| | GET | `/v1/api/test-logs/test-case/{id}` | 获取测试用例日志 |
| | GET | `/v1/api/test-logs/filter/status/{status}` | 按状态过滤 |
| | GET | `/v1/api/test-logs/filter/combined` | 组合过滤 |
| | DELETE | `/v1/api/test-logs/{id}` | 删除测试日志 |
| | DELETE | `/v1/api/test-logs/test-case/{id}` | 删除用例所有日志 |

### 路由层次结构

```
FastAPI App
└── /v1 (来自 src/api/router.py)
    ├── /health (来自 src/api/v1/endpoints/health.py)
    ├── /demo/* (来自 src/api/v1/endpoints/demo.py)
    ├── /api/test-cases/* (来自 src/api/v1/endpoints/test_cases.py)
    ├── /api/test-execution/* (来自 src/api/v1/endpoints/test_execution.py)
    └── /api/test-logs/* (来自 src/api/v1/endpoints/test_logs.py)
```

## 前端兼容性

### JavaScript API调用
前端JavaScript文件中的API调用路径保持不变：
- `fetch('/v1/api/test-cases/')`
- `fetch('/v1/api/test-execution/execute')`
- `fetch('/v1/api/test-logs/')`

这确保了前端代码无需修改即可继续正常工作。

## 优势

### 1. 符合框架设计
- ✅ 遵循原有的 `src/api/v1/endpoints/` 目录结构
- ✅ 保持代码组织的一致性
- ✅ 便于版本管理和API演进

### 2. 更好的可维护性
- ✅ 清晰的文件组织结构
- ✅ 易于添加新的API端点
- ✅ 便于团队协作开发

### 3. 向后兼容
- ✅ API路径保持不变
- ✅ 前端代码无需修改
- ✅ 现有功能正常工作

## 验证

### API端点验证
运行以下命令验证API结构：
```bash
python -c "
from src.api.v1 import router
for route in router.routes:
    if hasattr(route, 'path'):
        print(f'{route.methods} {route.path}')
"
```

### 服务器启动验证
```bash
python -m uvicorn src.main:app --reload
```

访问 `http://localhost:8000/docs` 查看自动生成的API文档。

## 后续改进建议

### 1. API版本管理
- 考虑为未来的API版本创建 `v2/` 目录
- 实现API版本切换机制

### 2. 统一响应格式
- 标准化所有API的响应格式
- 添加统一的错误处理

### 3. API文档优化
- 完善OpenAPI文档注释
- 添加更详细的示例和说明

### 4. 测试覆盖
- 为所有API端点添加单元测试
- 实现集成测试

## 总结

本次重构成功将API端点移动到了正确的目录结构中，遵循了原有的框架设计原则。重构过程中保持了API路径的向后兼容性，确保前端代码无需修改即可继续正常工作。

新的结构更加清晰和可维护，为未来的功能扩展和团队协作提供了良好的基础。
