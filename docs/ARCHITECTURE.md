# Architecture Guide

This document provides a comprehensive overview of the replay-llm-call architecture, designed for building production-ready AI agent applications with pydantic-ai and FastAPI.

## Overview

The replay-llm-call is a production-ready foundation for building AI agent applications that can run in both CLI and API modes. It implements a layered architecture with comprehensive configuration management, monitoring, and extensibility features.

### Technology Stack

- **AI Framework**: [pydantic-ai](https://github.com/pydantic/pydantic-ai) 0.8.1 for type-safe AI agent development
- **Web Framework**: FastAPI 0.115.12 with uvicorn ASGI server
- **Python**: 3.11 (fixed version for consistency)
- **Database**: PostgreSQL with SQLAlchemy ORM and connection pooling
- **Cache**: Redis with async client and distributed locking
- **Monitoring**: Pydantic Logfire with comprehensive instrumentation
- **Package Management**: uv for fast dependency resolution
- **Configuration**: Pydantic Settings with environment variable support

## Layered Architecture

The codebase follows a strict layered architecture to prevent circular dependencies and maintain clean separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    api (Top Layer)                         │
│              FastAPI endpoints and middleware               │
├─────────────────────────────────────────────────────────────┤
│                      services                              │
│                Business logic orchestration                │
├─────────────────────────────────────────────────────────────┤
│                       agents                               │
│              pydantic-ai agents and tools                  │
├─────────────────────────────────────────────────────────────┤
│                       stores                               │
│           Database, Redis, and data persistence            │
├─────────────────────────────────────────────────────────────┤
│                       utils                                │
│           Application utilities (Snowflake IDs, etc.)      │
├─────────────────────────────────────────────────────────────┤
│                       core                                 │
│     Configuration, LLM management, logging, exceptions     │
├─────────────────────────────────────────────────────────────┤
│                      models                                │
│              Data models and schemas (Bottom Layer)        │
└─────────────────────────────────────────────────────────────┘
```

## Core Components Deep Dive

### 1. **models** (Bottom Layer)
- **Purpose**: Data models, schemas, and type definitions
- **Dependencies**: None (pure data structures)
- **Current State**: Empty directory, ready for Pydantic models and SQLAlchemy entities
- **Usage**: Define request/response schemas, database models, and business entities

### 2. **core** (Foundation Layer)
- **Purpose**: Application-specific foundational components
- **Dependencies**: models only
- **Key Components**:
  - **Configuration** (`config.py`): Comprehensive Pydantic Settings with environment variable support
  - **LLM Management** (`llm_factory.py`, `llm_registry.py`): Business-oriented model creation and registry
  - **Error Handling** (`exceptions.py`, `error_codes.py`): Hierarchical exceptions with standardized error codes
  - **Logging** (`logger.py`): Structured logging with file rotation and level configuration
  - **Monitoring** (`logfire_config.py`): Pydantic Logfire integration with instrumentation
  - **Prompts** (`prompt_loader.py`): Template loading and management system

### 3. **utils** (Application Utilities)
- **Purpose**: Application-specific utility functions
- **Dependencies**: core, models
- **Key Components**:
  - **Snowflake Generator** (`snowflake_generator.py`): Distributed unique ID generation using SonyFlake
  - **Helper Functions**: Reusable utilities that require application configuration

### 4. **stores** (Data Persistence Layer)
- **Purpose**: Data persistence and external service connections
- **Dependencies**: core, utils, models
- **Key Components**:
  - **Database** (`database.py`): SQLAlchemy engine with connection pooling, session management, and health monitoring
  - **Redis Client** (`redis_client.py`): Async Redis client with connection pooling and comprehensive operations
  - **Redis Locking** (`redis_lock.py`): Distributed locking mechanisms for coordination

### 5. **agents** (AI Agent Layer)
- **Purpose**: pydantic-ai agents and AI-specific logic
- **Dependencies**: stores, core, utils, models
- **Key Components**:
  - **Demo Agent** (`demo_agent.py`): Example pydantic-ai agent with tool registration
  - **Agent Tools**: Reusable tools and capabilities for agents
  - **Agent Dependencies**: Structured dependency injection for agents

### 6. **services** (Business Logic Layer)
- **Purpose**: Business logic orchestration and complex operations
- **Dependencies**: agents, stores, core, utils, models
- **Key Components**:
  - **Demo Service** (`demo_service.py`): Business logic for agent interactions
  - **Service Orchestration**: Complex business workflows and data processing

### 7. **api** (Interface Layer)
- **Purpose**: FastAPI application with comprehensive middleware
- **Dependencies**: services, agents, stores, core, utils, models
- **Key Components**:
  - **Factory** (`factory.py`): FastAPI application creation with middleware setup
  - **Middleware** (`middleware.py`): Request logging, ID tracking, and custom middleware
  - **Versioned Endpoints** (`v1/`): API version management with structured endpoints
  - **Error Handling** (`errors/`): Global exception handlers and error responses
  - **Schemas** (`schemas/`): Request/response models for API endpoints

## Data Flow and System Interactions

### Request Processing Flow

The system supports two primary modes of operation:

#### CLI Mode Flow
```
main.py → run_cli_mode() → demo_agent → LLM APIs
```

#### API Mode Flow
```
FastAPI Request → Middleware Stack → API Endpoints → Services → Agents → Stores → External Services
```

### Detailed API Request Flow

1. **Request Entry**: FastAPI receives HTTP request
2. **Middleware Processing** (in execution order):
   - Metrics collection (custom middleware)
   - Compression (`GZipMiddleware`)
   - CORS handling (`CORSMiddleware`)
   - Security (`TrustedHostMiddleware`, production only)
   - Request logging (`RequestLoggingMiddleware`)
   - Request ID generation (`RequestIDMiddleware`)
3. **Endpoint Processing**: Route-specific business logic
4. **Service Layer**: Business logic orchestration
5. **Agent Layer**: AI model interactions with tools
6. **Store Layer**: Data persistence and caching
7. **External Services**: LLM APIs, databases, Redis
8. **Response Flow**: Results flow back through the same layers

### Configuration Flow

Configuration flows from environment variables through the application:

```
Environment Variables → Pydantic Settings → Application Components
```

- **Startup**: Settings validated and loaded once
- **Runtime**: Components access configuration through dependency injection
- **Business Logic**: Model selection based on business-oriented configuration

## Configuration Architecture

### Comprehensive Configuration System

The template uses a sophisticated configuration system built on Pydantic Settings:

#### Key Features
- **Environment Variable Support**: Automatic loading from `.env` files
- **Type Safety**: Full validation with Pydantic models
- **Hierarchical Structure**: Nested configuration with `__` delimiter
- **Secure Handling**: `SecretStr` for API keys and sensitive data
- **Business-Oriented**: Model configurations organized by business purpose

#### Configuration Categories

```python
# Application Settings
debug: bool = False
environment: Literal["development", "staging", "production"]
log_level: str = "info"

# API Configuration
api__title: str = "replay-llm-call"
api__docs_url: str = "/docs"

# Database Settings
database__url: str = "postgresql://..."
database__pool_size: int = 10

# Redis Configuration
redis__host: str = "localhost"
redis__port: int = 6379

# AI Model Configuration (Business-Oriented)
ai__demo_agent__provider: str = "openrouter"
ai__demo_agent__model_name: str = "openai/gpt-4o-mini"
ai__fallback__provider: str = "openai"
ai__fallback__model_name: str = "gpt-4o-mini"

# Monitoring
logfire__enabled: bool = False
logfire__service_name: str = "replay_llm_call"
```

## Error Handling and Monitoring

### Comprehensive Error Management

The template implements a sophisticated error handling system:

#### Exception Hierarchy
```python
ApplicationException (Base)
├── ConfigurationException
├── DatabaseException
├── RedisException
├── AgentException
├── APIException
├── ValidationException
├── InternalServiceException
├── RequestParamException
├── AuthException
├── LLMCallException
├── DataProcessException
└── CallbackServiceException
```

#### Error Code System
- **Standardized Codes**: StrEnum-based error codes with domain prefixes
- **HTTP Mapping**: Automatic HTTP status code mapping
- **Traceability**: Request ID tracking for error correlation
- **Safe Serialization**: JSON-safe error responses

#### Example Error Handling
```python
try:
    result = await agent.run(user_input)
except Exception as e:
    raise AgentException.wrap(
        e,
        message="Agent processing failed",
        error_code=AgentErrorCode.RUN_FAILED,
        user_input=user_input
    )
```

### Monitoring and Observability

#### Logfire Integration
- **Automatic Instrumentation**: pydantic-ai, Redis, HTTPX, FastAPI
- **Configurable Monitoring**: Toggle instrumentation per service
- **Performance Tracking**: Request timing and processing metrics
- **Error Correlation**: Distributed tracing with request IDs

#### Health Monitoring
```python
# Database health check
status = test_connection()  # Returns pool status and connection info

# Redis health check
health = await redis_client.health_check()  # Returns performance metrics

# API health endpoints
GET /api/v1/health  # Comprehensive API health check
```

#### Logging Architecture
- **Structured Logging**: JSON-formatted logs with context
- **File Rotation**: Configurable log file management
- **Level Configuration**: Environment-specific log levels
- **Request Tracking**: Unique request IDs for correlation

## SQLAlchemy ORM 使用约定

### mapped_column 说明
```python
# mapped_column 是 SQLAlchemy 2.0+ 的新语法，用于定义表列的映射
# 它提供了更好的类型提示和IDE支持，替代了旧的 Column() 语法

from sqlalchemy.orm import Mapped, mapped_column

class TestCase(Base):
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
```

## Extension Patterns

### Adding New Agents

1. **Create Agent Module** (`agents/your_agent.py`):
```python
from pydantic_ai import Agent
from src.core.llm_registry import get_default_model

your_agent = Agent(
    model=get_default_model(),
    system_prompt="Your agent's system prompt..."
)

@your_agent.tool
def your_tool() -> str:
    """Tool description for the agent."""
    return "Tool result"

async def handle_your_agent(user_input: str) -> str:
    result = await your_agent.run(user_input)
    return result.data
```

2. **Register in Module** (`agents/__init__.py`):
```python
from .your_agent import handle_your_agent, your_agent
```

3. **Add Business Configuration** (`core/config.py`):
```python
ai__your_agent__provider: str = Field(default="openai")
ai__your_agent__model_name: str = Field(default="gpt-4")
```

4. **Create Registry Function** (`core/llm_registry.py`):
```python
def get_your_agent_model() -> Model:
    return create_fallback_model(
        primary_model_name=settings.ai__your_agent__model_name,
        primary_provider=settings.ai__your_agent__provider
    )
```

### Adding New API Endpoints

1. **Create Endpoint Module** (`api/v1/endpoints/your_endpoint.py`):
```python
from fastapi import APIRouter
from src.services.your_service import YourService

router = APIRouter()

@router.post("/your-endpoint")
async def your_endpoint(request: YourRequest):
    service = YourService()
    return await service.process(request)
```

2. **Register Router** (`api/v1/__init__.py`):
```python
from .endpoints.your_endpoint import router as your_router
app.include_router(your_router, prefix="/your-prefix")
```

### Adding New Services

1. **Create Service Module** (`services/your_service.py`):
```python
from src.agents import handle_your_agent
from src.stores.database import database_session

class YourService:
    async def process(self, data: str) -> str:
        # Business logic orchestration
        agent_result = await handle_your_agent(data)

        # Database operations if needed
        with database_session() as db:
            # Database operations
            pass

        return agent_result
```

## Security and Performance

### Security Measures

#### Configuration Security
- **SecretStr**: Automatic masking of sensitive configuration values
- **Environment Isolation**: No hardcoded secrets in code
- **Validation**: Type-safe configuration with runtime validation

#### API Security
- **CORS Configuration**: Configurable cross-origin resource sharing
- **Trusted Hosts**: Production host validation middleware
- **Request Validation**: Automatic input validation with Pydantic
- **Error Sanitization**: Safe error messages without sensitive data exposure

#### Database Security
- **Connection Pooling**: Secure connection management with timeouts
- **ORM Protection**: SQL injection prevention through SQLAlchemy
- **Transaction Isolation**: Proper transaction boundaries

### Performance Optimizations

#### Connection Management
```python
# Database connection pooling
database__pool_size: int = 10
database__max_overflow: int = 20
database__pool_timeout: int = 30

# Redis connection pooling
redis__connect_timeout: float = 3.0
redis__socket_timeout: float = 3.0
```

#### Async Architecture
- **Full Async Support**: Async/await throughout the stack
- **Non-blocking Operations**: Redis and database operations
- **Concurrent Processing**: Multiple requests handled concurrently

#### Response Optimization
- **GZip Compression**: Automatic response compression for large payloads
- **Connection Reuse**: HTTP client connection pooling
- **Efficient Serialization**: Optimized JSON serialization

#### Caching Strategy
```python
# Redis caching patterns
await redis_client.set_json("cache_key", data, ex=3600)  # 1 hour TTL
cached_data = await redis_client.get_json("cache_key")

# Distributed locking for coordination
async with redis_client.lock("operation_lock", timeout=30):
    # Critical section
    pass
```

## Development Guidelines

### Import Guidelines

#### ✅ Correct Import Patterns
```python
# Lower layers can import from even lower layers
from src.core.config import settings
from src.core.logger import get_logger

# Higher layers can import from all lower layers
from src.services.demo_service import DemoService
from src.agents.demo_agent import handle_demo_agent
from src.stores.redis_client import get_redis_client
```

#### ❌ Incorrect Import Patterns
```python
# NEVER: Higher layers importing from lower layers
from src.utils.snowflake_generator import generate_snowflake_id  # ❌ in core
from src.services.demo_service import DemoService  # ❌ in agents
```

### Dependency Rules

1. **Unidirectional Dependencies**: Dependencies flow downward only
2. **No Circular Dependencies**: Use dependency injection to break cycles
3. **Layer Isolation**: Each layer has distinct responsibilities
4. **Interface Segregation**: Clean, minimal interfaces between layers

### Type Safety and Validation

#### Comprehensive Type Annotations
```python
# All functions and methods include type hints
async def handle_demo_agent(user_input: str, deps: Optional[DemoDeps] = None) -> str:
    # Implementation with full type safety

# Pydantic models for validation
class DemoChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = None
```

#### Configuration Validation
```python
# Runtime validation with clear error messages
@field_validator("log_level")
@classmethod
def validate_log_level(cls, v: str) -> str:
    allowed_levels = {"debug", "info", "warning", "error"}
    normalized = v.lower().strip()
    if normalized not in allowed_levels:
        raise ValueError(f"log_level must be one of {sorted(allowed_levels)}")
    return normalized
```

## Deployment Considerations

### Container Deployment

The template includes Docker support for containerized deployment:

```dockerfile
# Multi-stage build for optimized images
FROM python:3.11-slim as builder
# Build dependencies and application

FROM python:3.11-slim as runtime
# Runtime environment with minimal footprint
```

### Environment Configuration

#### Production Settings
```bash
# Essential production environment variables
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info

# Database configuration
DATABASE__URL=postgresql://user:pass@host:5432/db
DATABASE__POOL_SIZE=20

# Redis configuration
REDIS__HOST=redis.example.com
REDIS__SSL=true

# AI API keys
AI__OPENAI_API_KEY=sk-...
AI__ANTHROPIC_API_KEY=sk-ant-...

# Monitoring
LOGFIRE__ENABLED=true
LOGFIRE__TOKEN=your-logfire-token
```

#### Health Check Endpoints
```python
# Built-in health checks for load balancers
GET /api/v1/health  # Comprehensive API health check
```

### Scalability Patterns

#### Horizontal Scaling
- **Stateless Design**: No server-side session state
- **Distributed IDs**: Snowflake IDs for unique identification across instances
- **Shared State**: Redis for coordination and caching
- **Load Balancing**: Health check endpoints for load balancer integration

#### Performance Monitoring
```python
# Built-in metrics collection
response.headers["X-Process-Time"] = str(process_time)
response.headers["X-Request-ID"] = request_id

# Logfire integration for detailed monitoring
# Automatic instrumentation for database, Redis, HTTP calls
```

## Migration and Upgrade Patterns

### Configuration Evolution
The configuration system uses business-oriented model registry patterns:

```python
# Business-oriented registry (recommended)
get_demo_model()    # ✅ Use this pattern
get_default_model() # ✅ Use this pattern
get_fallback_model() # ✅ Use this pattern

# Custom agent models can be added following the same pattern
get_your_agent_model() # ✅ Follow this naming convention
```

---

## Summary

This architecture provides a solid foundation for building production-ready AI agent applications with:

- **Scalability**: Horizontal scaling support with stateless design
- **Maintainability**: Clear layer separation and dependency management
- **Observability**: Comprehensive monitoring and error tracking
- **Security**: Built-in security measures and safe configuration handling
- **Performance**: Optimized connection pooling and async operations
- **Extensibility**: Clear patterns for adding new components

The template is designed to grow with your project while maintaining architectural integrity and development velocity.
