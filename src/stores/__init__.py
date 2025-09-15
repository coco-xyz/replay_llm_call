"""
Stores Package

Data persistence and state management for replay-llm-call.
Provides clean interfaces for database and cache operations.

This package follows fast-failing import strategy - missing dependencies will
cause immediate import errors rather than graceful degradation.
"""

# Database components - always available
from .database import (
    Base,
    SessionLocal,
    database_session,
    dispose_engine,
    engine,
    get_db_dependency,
    get_pool_status,
    test_connection,
    transaction_manager,
)

# Redis components - fast-failing imports
from .redis_client import (
    RedisClient,
    close_redis_client,
    get_redis_client,
    get_redis_client_async,
    test_redis_connection,
)
from .redis_lock import SessionLock, session_lock_context

# Stores package exports - only components from this package
__all__ = [
    # Database
    "Base",
    "engine",
    "SessionLocal",
    "get_db_dependency",
    "database_session",
    "transaction_manager",
    "test_connection",
    "get_pool_status",
    "dispose_engine",
    # Redis
    "RedisClient",
    "get_redis_client",
    "get_redis_client_async",
    "close_redis_client",
    "test_redis_connection",
    # Redis Lock
    "SessionLock",
    "session_lock_context",
]
