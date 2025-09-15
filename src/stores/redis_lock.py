"""
Redis Distributed Lock Utility

Session-level distributed lock implementation for AI Agents project.
Provides simple API for acquiring and releasing locks to prevent concurrent
resume data modification.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from src.core.config import settings
from src.core.error_codes import RedisErrorCode
from src.core.exceptions import RedisException
from src.core.logger import get_logger

# Fast-failing imports from core and stores
from src.stores.redis_client import get_redis_client

logger = get_logger(__name__)


class SessionLock:
    """
    Session-level distributed lock for resume data protection.

    This class provides a high-level interface for acquiring and releasing
    distributed locks using Redis, specifically designed for protecting
    resume data from concurrent modifications.
    """

    def __init__(self, session_id: str, timeout: int = 30):
        """
        Initialize session lock.

        Args:
            session_id: Session identifier
            timeout: Lock timeout in seconds (uses settings default if None)
        """
        self.session_id = session_id
        self.timeout = timeout
        self.lock_key = f"resume_lock:{session_id}"
        self._redis_client = get_redis_client()
        self._identifier: Optional[str] = None

    @property
    def identifier(self) -> Optional[str]:
        """Get the current lock identifier if acquired."""
        return self._identifier

    async def acquire(self, wait_timeout: int = 10) -> bool:
        """
        Acquire distributed lock for the session.

        Args:
            wait_timeout: Maximum time to wait for lock acquisition in seconds

        Returns:
            bool: True if lock acquired successfully, False otherwise

        Raises:
            RedisException: If Redis operation fails
        """
        try:
            start_time = time.monotonic()

            # Try to acquire lock with retries
            while (time.monotonic() - start_time) < wait_timeout:
                self._identifier = await self._redis_client.acquire_lock(
                    self.lock_key, self.timeout
                )

                if self._identifier:
                    logger.info(
                        "Session lock acquired successfully for session: %s",
                        self.session_id,
                    )
                    return True

                # Wait before retry
                await asyncio.sleep(settings.redis_lock__retry_sleep_interval)
            logger.warning(
                "Failed to acquire session lock for session: %s within %d seconds",
                self.session_id,
                wait_timeout,
            )
            return False

        except Exception as e:
            logger.error(
                "Error acquiring session lock for session: %s, error: %s",
                self.session_id,
                str(e),
            )
            raise RedisException(
                RedisErrorCode.LOCK_FAILED, f"Failed to acquire session lock: {str(e)}"
            ) from e

    async def release(self) -> bool:
        """
        Release distributed lock for the session.

        Returns:
            bool: True if lock released successfully, False otherwise

        Raises:
            RedisException: If Redis operation fails
        """
        if not self._identifier:
            logger.warning(
                "Attempting to release lock without identifier for session: %s",
                self.session_id,
            )
            return False
        try:
            success = await self._redis_client.release_lock(
                self.lock_key, self._identifier
            )

            if success:
                logger.info(
                    "Session lock released successfully for session: %s",
                    self.session_id,
                )
            else:
                logger.warning(
                    "Failed to release session lock for session: %s", self.session_id
                )

            self._identifier = None
            return success

        except Exception as e:
            logger.error(
                "Error releasing session lock for session: %s, error: %s",
                self.session_id,
                str(e),
            )
            raise RedisException(
                RedisErrorCode.LOCK_FAILED, f"Failed to release session lock: {str(e)}"
            ) from e

    @asynccontextmanager
    async def acquire_context(
        self, wait_timeout: int = 10
    ) -> AsyncGenerator[Optional[str], None]:
        """
        Context manager for automatic lock acquisition and release.

        Args:
            wait_timeout: Maximum time to wait for lock acquisition in seconds

        Yields:
            str: Lock identifier

        Raises:
            RedisException: If lock cannot be acquired or Redis operation fails

        Example:
            async with SessionLock(session_id).acquire_context() as lock_id:
                # Perform protected operations
                logger.info(f"Operating with lock {lock_id}")
        """
        acquired = await self.acquire(wait_timeout)

        if not acquired:
            raise RedisException(
                RedisErrorCode.LOCK_FAILED,
                f"Failed to acquire session lock for {self.session_id} "
                f"within {wait_timeout} seconds",
            )

        try:
            yield self.identifier
        finally:
            await self.release()


# Legacy functions removed - use SessionLock class instead
#
# The following functions have been removed in favor of the SessionLock class:
# - acquire_session_lock() -> Use SessionLock(session_id).acquire()
# - release_session_lock() -> Use SessionLock(session_id).release()
#
# For context manager usage, use SessionLock(session_id).acquire_context()
# or the session_lock_context() function below.


# Convenience function for session lock context management
@asynccontextmanager
async def session_lock_context(
    session_id: str, timeout: int = 30, wait_timeout: int = 10
) -> AsyncGenerator[Optional[str], None]:
    """
    Convenient context manager for session-level distributed lock.

    This is a high-level convenience function that combines lock creation,
    acquisition, and release in a single context manager call.

    Args:
        session_id: Session identifier
        timeout: Lock timeout in seconds (how long the lock stays valid)
        wait_timeout: Maximum time to wait for lock acquisition in seconds

    Yields:
        str: Lock identifier

    Raises:
        RedisException: If lock cannot be acquired within wait_timeout

    Example:
        async with session_lock_context("user_123", timeout=60) as lock_id:
            logger.info(f"Processing user data with lock {lock_id}")
            # Perform protected operations
            await update_user_data()

    Note:
        For more control over lock lifecycle, use SessionLock class directly.
    """
    session_lock = SessionLock(session_id, timeout)

    async with session_lock.acquire_context(wait_timeout):
        yield session_lock.identifier
