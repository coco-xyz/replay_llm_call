"""
Database Core

SQLAlchemy engine, session management, and database utilities for replay-llm-call.
Provides connection pooling, transaction management, and health monitoring.

Features:
- Connection pool with monitoring and health checks
- Transaction context managers with automatic rollback
- FastAPI-compatible dependency injection
- Comprehensive error handling with core error codes
- Connection lifecycle management
"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import (
    DatabaseError,
    InterfaceError,
    OperationalError,
    SQLAlchemyError,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

# Fast-failing imports from core
from src.core.config import settings
from src.core.error_codes import DatabaseErrorCode
from src.core.exceptions import DatabaseException
from src.core.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class PoolStatus:
    """Immutable connection pool status information."""

    size: int
    checked_out: int
    overflow: int


# Global SQLAlchemy base
Base = declarative_base()


def _create_database_engine() -> Engine:
    """Create and configure the database engine with optimized settings."""
    try:
        db_engine = create_engine(
            settings.database__url,
            echo=settings.database__echo,
            # Use all configurable database settings
            pool_pre_ping=settings.database__pool_pre_ping,
            pool_size=settings.database__pool_size,
            max_overflow=settings.database__max_overflow,
            pool_timeout=settings.database__pool_timeout,
            pool_recycle=settings.database__pool_recycle,
            poolclass=QueuePool,
        )

        return db_engine

    except Exception as e:
        logger.error("Failed to create database engine: %s", str(e))

        # Extract host from database URL for error details
        database_url = str(settings.database__url)
        if "@" in database_url:
            host = database_url.rsplit("@", maxsplit=1)[-1].split("/")[0]
        else:
            host = "unknown"

        raise DatabaseException(
            DatabaseErrorCode.CONNECTION_FAILED,
            f"Database engine creation failed: {str(e)}",
            details={"database_url_host": host},
        ) from e


# Global engine and session factory
engine = _create_database_engine()

# Use safe defaults for session configuration
# expire_on_commit=True: Objects expire after commit, safer but requires refresh for access
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
    expire_on_commit=True,  # Safe default, prevents stale data issues
)


def get_pool_status() -> PoolStatus:
    """
    Get current connection pool status.

    Returns:
        PoolStatus: Immutable pool status information

    Raises:
        DatabaseException: If pool status cannot be retrieved
    """
    try:
        pool = engine.pool
        # QueuePool specific attributes - use getattr with defaults for safety
        return PoolStatus(
            size=getattr(pool, "size", lambda: 0)(),
            checked_out=getattr(pool, "checkedout", lambda: 0)(),
            overflow=getattr(pool, "overflow", lambda: 0)(),
        )
    except Exception as e:
        logger.error("Failed to get pool status: %s", str(e))
        raise DatabaseException(
            DatabaseErrorCode.CONNECTION_FAILED,
            f"Pool status retrieval failed: {str(e)}",
        ) from e


def _create_db_session() -> Generator[Session, None, None]:
    """
    Internal session creation logic with unified error handling.

    This function contains the core database session management logic
    that is shared between FastAPI dependency injection and context manager usage.

    Yields:
        Session: SQLAlchemy database session

    Raises:
        DatabaseException: If session creation or management fails
    """
    db_session = None
    try:
        db_session = SessionLocal()
        logger.debug("Database session created")
        yield db_session

    except SQLAlchemyError as e:
        logger.error("Database session error: %s", str(e))
        if db_session:
            try:
                db_session.rollback()
                logger.debug("Database session rolled back due to error")
            except Exception as rollback_error:
                logger.error("Failed to rollback session: %s", str(rollback_error))
        raise DatabaseException(
            DatabaseErrorCode.QUERY_FAILED, f"Database session error: {str(e)}"
        ) from e

    except Exception as e:
        logger.error("Unexpected session error: %s", str(e))
        if db_session:
            try:
                db_session.rollback()
            except Exception:
                pass
        raise DatabaseException(
            DatabaseErrorCode.CONNECTION_FAILED, f"Unexpected database error: {str(e)}"
        ) from e

    finally:
        if db_session:
            try:
                db_session.close()
                logger.debug("Database session closed")
            except Exception as close_error:
                logger.error("Failed to close database session: %s", str(close_error))


def get_db_dependency() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database session.

    This function is specifically designed for FastAPI dependency injection.
    FastAPI will automatically manage the session lifecycle for each request.

    Yields:
        Session: SQLAlchemy database session

    Raises:
        DatabaseException: If session creation or management fails

    Example:
        @app.get("/users")
        async def get_users(db: Session = Depends(get_db_dependency)):
            return db.query(User).all()

        @app.post("/users")
        async def create_user(user_data: UserCreate, db: Session = Depends(get_db_dependency)):
            user = User(**user_data.dict())
            db.add(user)
            db.commit()
            return user
    """
    yield from _create_db_session()


@contextmanager
def database_session() -> Generator[Session, None, None]:
    """
    Context manager for database session.

    Use this for non-FastAPI contexts such as CLI scripts, background tasks,
    service layer operations, or any standalone database operations.

    Yields:
        Session: SQLAlchemy database session

    Raises:
        DatabaseException: If session creation or management fails

    Example:
        # In background tasks
        with database_session() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.last_login = datetime.now(timezone.utc)
                db.commit()

        # In service layer
        def process_user_data(user_id: int):
            with database_session() as db:
                user = db.query(User).filter(User.id == user_id).first()
                # Complex business logic
                user.status = "processed"
                db.commit()
    """
    yield from _create_db_session()


@contextmanager
def transaction_manager(db_session: Session) -> Generator[Session, None, None]:
    """
    Transaction context manager with automatic commit/rollback.

    Designed for Service layer to manage business transactions.
    Currently does not support nested transactions - use simple patterns to avoid nesting.

    Args:
        db_session: Existing database session

    Yields:
        Session: The same database session within transaction context

    Raises:
        DatabaseException: If transaction fails

    Usage:
        # Recommended pattern
        with database_session() as db:
            with transaction_manager(db) as tx:
                # Multiple operations in single transaction
                user = User(name="John")
                tx.add(user)
                tx.flush()  # Get ID without committing

                profile = Profile(user_id=user.id, bio="Developer")
                tx.add(profile)

                # Transaction commits automatically on successful exit
                # Transaction rolls back automatically on any exception

    Note:
        - Use this for complex business logic that spans multiple database operations
        - For simple operations in FastAPI routes, just use db.commit() directly
        - Nested transactions are not currently supported
    """
    if db_session is None:
        raise DatabaseException(
            DatabaseErrorCode.CONNECTION_FAILED, "Database session is None"
        )

    logger.debug("Starting database transaction")

    try:
        yield db_session
        db_session.commit()
        logger.debug("Database transaction committed successfully")

    except Exception as e:
        logger.error("Database transaction failed: %s", str(e))
        try:
            db_session.rollback()
            logger.debug("Database transaction rolled back")
        except Exception as rollback_error:
            logger.error("Failed to rollback transaction: %s", str(rollback_error))

        # 根据异常类型选择错误码
        error_code = (
            DatabaseErrorCode.QUERY_FAILED
            if isinstance(e, SQLAlchemyError)
            else DatabaseErrorCode.TRANSACTION_FAILED
        )

        raise DatabaseException(
            error_code, f"Database transaction failed: {str(e)}"
        ) from e


def dispose_engine() -> None:
    """
    Dispose database engine and close all connections.

    Should be called during application shutdown for graceful cleanup.
    Useful for FastAPI shutdown events or application lifecycle management.

    Example:
        @app.on_event("shutdown")
        async def shutdown_event():
            dispose_engine()
    """
    try:
        engine.dispose()
        logger.info("Database engine disposed successfully")
    except Exception as e:
        logger.error("Failed to dispose database engine: %s", str(e))


def test_connection() -> Dict[str, Any]:
    """
    Test database connection and return status information.

    Returns:
        Dict[str, Any]: Connection test results and pool status

    Raises:
        DatabaseException: If connection test fails

    Example:
        try:
            status = test_connection()
            logger.info("Database ready: %s", status)
        except DatabaseException as e:
            logger.error("Database not ready: %s", e.message)
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test_value"))
            test_value = result.scalar()

        pool_status = get_pool_status()

        # Log pool status for monitoring
        logger.info(
            "Database connection test - Pool status: Size=%d, Checked out=%d, "
            "Overflow=%d",
            pool_status.size,
            pool_status.checked_out,
            pool_status.overflow,
        )

        # 安全地渲染 URL
        try:
            safe_url = engine.url.set(password="***").render_as_string(
                hide_password=False
            )
        except Exception:
            # 如果 URL 渲染失败，使用简化版本
            safe_url = (
                f"{engine.url.drivername}://***@{engine.url.host}:"
                f"{engine.url.port}/{engine.url.database}"
            )

        status = {
            "connection_test": "passed",
            "test_query_result": test_value,
            "pool_status": {
                "size": pool_status.size,
                "checked_out": pool_status.checked_out,
                "overflow": pool_status.overflow,
            },
            "engine_url": safe_url,
        }

        logger.info("Database connection test successful")
        return status

    except (OperationalError, DatabaseError, InterfaceError) as e:
        # 捕获更多的 SQLAlchemy 数据库相关异常
        logger.error("Database connection test failed: %s", str(e))
        raise DatabaseException(
            DatabaseErrorCode.CONNECTION_FAILED,
            f"Database connection test failed: {str(e)}",
            details={"error_type": type(e).__name__},
        ) from e

    except Exception as e:
        logger.error("Unexpected error during connection test: %s", str(e))
        raise DatabaseException(
            DatabaseErrorCode.CONNECTION_FAILED,
            f"Database connection test failed: {str(e)}",
            details={"error_type": type(e).__name__},
        ) from e
