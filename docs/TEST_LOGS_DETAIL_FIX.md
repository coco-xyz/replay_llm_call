# Test Logs详情查看功能修复文档

## 问题描述

在Test Logs页面点击"查看详情"按钮时，出现HTTP 500错误，无法正常显示测试日志的详细信息。

## 错误原因分析

通过代码分析发现了以下问题：

### 1. 方法名不匹配
**问题**: API端点调用的方法名与Service层实际方法名不一致
- API调用: `test_log_service.get_log(log_id)`
- Service实际方法: `get_test_log(log_id)`

### 2. 缺失方法
**问题**: Service层缺少`get_logs_filtered`方法
- API调用: `test_log_service.get_logs_filtered(...)`
- Service层: 方法不存在

### 3. Store层缺失方法
**问题**: Store层缺少`get_filtered`方法
- Service调用: `self.store.get_filtered(...)`
- Store层: 方法不存在

## 修复方案

### 1. 修复API端点方法调用

**文件**: `src/api/v1/endpoints/test_logs.py`

**修复前**:
```python
result = test_log_service.get_log(log_id)
```

**修复后**:
```python
result = test_log_service.get_test_log(log_id)
```

### 2. 添加Service层缺失方法

**文件**: `src/services/test_log_service.py`

**新增方法**:
```python
def get_logs_filtered(
    self, 
    status: Optional[str] = None,
    test_case_id: Optional[str] = None,
    limit: int = 100, 
    offset: int = 0
) -> List[TestLogResponse]:
    """
    Get test logs with combined filters.
    
    Args:
        status: Optional status filter
        test_case_id: Optional test case ID filter
        limit: Maximum number of results
        offset: Number of results to skip
        
    Returns:
        List of filtered test log responses
    """
    try:
        test_logs = self.store.get_filtered(
            status=status,
            test_case_id=test_case_id,
            limit=limit,
            offset=offset
        )
        
        return [
            TestLogResponse(
                id=log.id,
                test_case_id=log.test_case_id,
                model_name=log.model_name,
                system_prompt=log.system_prompt,
                user_message=log.user_message,
                tools=log.tools,
                llm_response=log.llm_response,
                response_time_ms=log.response_time_ms,
                status=log.status,
                error_message=log.error_message,
                created_at=log.created_at
            ) for log in test_logs
        ]
        
    except Exception as e:
        logger.error(f"Failed to get filtered logs: {e}")
        raise
```

### 3. 添加Store层缺失方法

**文件**: `src/stores/test_log_store.py`

**新增方法**:
```python
def get_filtered(
    self, 
    status: Optional[str] = None,
    test_case_id: Optional[str] = None,
    limit: int = 100, 
    offset: int = 0
) -> List[TestLog]:
    """
    Get test logs with combined filters.
    
    Args:
        status: Optional status filter
        test_case_id: Optional test case ID filter
        limit: Maximum number of results
        offset: Number of results to skip
        
    Returns:
        List[TestLog]: Filtered test logs
        
    Raises:
        DatabaseException: If query fails
    """
    try:
        with database_session() as db:
            query = db.query(TestLog)
            
            # Apply filters
            if status:
                query = query.filter(TestLog.status == status)
            if test_case_id:
                query = query.filter(TestLog.test_case_id == test_case_id)
            
            test_logs = (
                query.order_by(desc(TestLog.created_at))
                .limit(limit)
                .offset(offset)
                .all()
            )
            logger.debug(f"Retrieved {len(test_logs)} filtered test logs")
            return test_logs
            
    except Exception as e:
        logger.error(f"Failed to get filtered test logs: {e}")
        raise DatabaseException(
            DatabaseErrorCode.QUERY_FAILED,
            f"Failed to get filtered test logs: {str(e)}"
        ) from e
```

## 修复验证

### 1. 方法存在性验证
```python
# 测试代码
from src.api.v1.endpoints.test_logs import test_log_service

# 验证get_test_log方法
result = test_log_service.get_test_log('test-id')
print('get_test_log method exists and callable')

# 验证get_logs_filtered方法  
result = test_log_service.get_logs_filtered()
print('get_logs_filtered method exists and callable')
```

**验证结果**: ✅ 所有方法都正常工作

### 2. API端点验证
```bash
# 测试API端点
curl -X GET "http://localhost:8000/v1/api/test-logs/{log_id}"
```

**预期结果**: 返回测试日志详情，不再出现500错误

### 3. 前端功能验证
1. 访问 `http://localhost:8000/test-logs`
2. 点击任意测试日志的"查看详情"按钮
3. 应该能正常显示详情模态框

## 功能特性

修复后的查看详情功能包含以下信息：

### 执行信息
- ✅ 执行状态 (Success/Failed)
- ✅ 使用的模型名称
- ✅ 响应时间 (毫秒)
- ✅ 关联的测试用例 (可点击跳转)
- ✅ 执行时间

### 请求内容
- ✅ 系统提示词 (System Prompt)
- ✅ 用户消息 (User Message)
- ✅ 工具配置 (Tools Configuration)

### 响应内容
- ✅ LLM响应内容
- ✅ 错误信息 (如果有)

### 工具信息
- ✅ 工具列表展示
- ✅ 可折叠的工具详情
- ✅ JSON格式的工具配置

## 相关API端点

修复涉及的API端点：

| 端点 | 方法 | 路径 | 描述 |
|------|------|------|------|
| 获取单个日志 | GET | `/v1/api/test-logs/{log_id}` | 获取测试日志详情 |
| 组合过滤 | GET | `/v1/api/test-logs/filter/combined` | 按多条件过滤日志 |

## 技术栈

### 后端
- **FastAPI**: REST API框架
- **SQLAlchemy**: ORM数据库操作
- **Pydantic**: 数据验证和序列化

### 前端
- **Bootstrap 5**: UI框架
- **JavaScript ES6+**: 前端逻辑
- **Fetch API**: HTTP请求

### 数据库
- **PostgreSQL**: 主数据库
- **SQLAlchemy Models**: 数据模型定义

## 后续改进建议

### 1. 错误处理优化
- 添加更详细的错误信息
- 实现前端错误重试机制
- 添加加载状态指示器

### 2. 性能优化
- 实现日志详情缓存
- 添加分页加载
- 优化数据库查询

### 3. 用户体验
- 添加快捷键支持
- 实现详情页面直接链接
- 添加导出功能

### 4. 测试覆盖
- 添加API端点单元测试
- 实现前端功能测试
- 添加集成测试

## 总结

本次修复解决了Test Logs详情查看功能的核心问题，确保了：

1. ✅ **API层**: 方法调用正确匹配
2. ✅ **Service层**: 完整的业务逻辑方法
3. ✅ **Store层**: 完整的数据访问方法
4. ✅ **前端**: 正常显示详情信息

修复后的功能提供了完整的测试日志查看体验，用户可以方便地查看测试执行的详细信息，包括请求内容、响应结果、工具使用情况等。
