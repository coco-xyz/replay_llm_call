"""
Redis Client Manager

Redis connection management and basic operations for AI Agents project.
"""

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional
from urllib.parse import quote

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

# Fast-failing imports from core
from src.core.config import settings
from src.core.error_codes import RedisErrorCode
from src.core.exceptions import RedisException
from src.core.logger import get_logger

logger = get_logger(__name__)


class RedisClient:
    """
    Redis client wrapper with connection pooling and common operations.
    """

    def __init__(self) -> None:
        """Initialize Redis client with connection pool."""
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._lock = asyncio.Lock()

    async def _ensure_connection(self) -> redis.Redis:
        """
        Ensure Redis connection is established.

        Returns:
            redis.Redis: Redis client instance

        Raises:
            RedisException: If connection fails
        """
        if self._client is not None:
            return self._client

        async with self._lock:
            if self._client is not None:
                return self._client  # type: ignore[unreachable]

            try:
                # Build Redis connection URL from settings with proper password encoding
                scheme = "rediss" if settings.redis__ssl else "redis"
                auth = (
                    f":{quote(settings.redis__password)}@"
                    if settings.redis__password
                    else ""
                )
                redis_url = (
                    f"{scheme}://{auth}{settings.redis__host}:"
                    f"{settings.redis__port}/{settings.redis__db}"
                )

                # Create connection pool with settings (only use defined config items)
                pool_kwargs = {
                    "encoding": "utf-8",
                    "decode_responses": True,
                    "retry_on_timeout": True,
                    "socket_connect_timeout": settings.redis__connect_timeout,
                    "socket_timeout": settings.redis__socket_timeout,
                }

                # Add SSL configuration if enabled
                if settings.redis__ssl:
                    pool_kwargs["connection_class"] = redis.SSLConnection
                    pool_kwargs["ssl_check_hostname"] = False
                    pool_kwargs["ssl_cert_reqs"] = None

                self._pool = ConnectionPool.from_url(redis_url, **pool_kwargs)

                # Create Redis client
                self._client = redis.Redis(connection_pool=self._pool)

                # Test connection
                await self._client.ping()
                logger.info("Redis connection established successfully")

                return self._client

            except Exception as e:
                logger.error("Failed to connect to Redis: %s", str(e))
                raise RedisException(
                    RedisErrorCode.CONNECTION_FAILED,
                    f"Redis connection failed: {str(e)}",
                ) from e

    async def close(self) -> None:
        """Close Redis connection and cleanup resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
        logger.info("Redis connection closed")

    # Basic Key-Value Operations
    async def get(self, key: str) -> Optional[str]:
        """
        Get value by key.

        Args:
            key: Redis key

        Returns:
            Value or None if key doesn't exist
        """
        client = await self._ensure_connection()
        result = await client.get(key)
        return str(result) if result is not None else None

    async def set(
        self, key: str, value: str, ex: Optional[int] = None, nx: bool = False
    ) -> bool:
        """
        Set key-value pair.

        Args:
            key: Redis key
            value: Value to set
            ex: Expiration time in seconds
            nx: Only set if key doesn't exist

        Returns:
            True if successful, False otherwise
        """
        client = await self._ensure_connection()
        result = await client.set(key, value, ex=ex, nx=nx)
        return bool(result)

    async def delete(self, *keys: str) -> int:
        """
        Delete keys.

        Args:
            keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        client = await self._ensure_connection()
        result = await client.delete(*keys)
        return int(result)

    async def exists(self, key: str) -> bool:
        """
        Check if key exists.

        Args:
            key: Redis key

        Returns:
            True if key exists, False otherwise
        """
        client = await self._ensure_connection()
        return bool(await client.exists(key))

    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration time for key.

        Args:
            key: Redis key
            seconds: Expiration time in seconds

        Returns:
            True if successful, False otherwise
        """
        client = await self._ensure_connection()
        result = await client.expire(key, seconds)
        return bool(result)

    # JSON Operations
    async def set_json(self, key: str, data: Any, ex: Optional[int] = None) -> bool:
        """
        Set JSON data.

        Args:
            key: Redis key
            data: Data to serialize and store
            ex: Expiration time in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            json_str = json.dumps(data, ensure_ascii=False)
            return await self.set(key, json_str, ex=ex)
        except (TypeError, ValueError) as e:
            logger.error("Failed to serialize data for key %s: %s", key, str(e))
            return False

    async def get_json(self, key: str) -> Optional[Any]:
        """
        Get JSON data.

        Args:
            key: Redis key

        Returns:
            Deserialized data or None if key doesn't exist
        """
        json_str = await self.get(key)
        if json_str is None:
            return None

        try:
            return json.loads(json_str)
        except (TypeError, ValueError) as e:
            logger.error("Failed to deserialize data for key %s: %s", key, str(e))
            return None

    # Hash Operations
    async def hset(self, name: str, mapping: Dict[str, str]) -> int:
        """
        Set hash fields.

        Args:
            name: Hash name
            mapping: Field-value mapping

        Returns:
            Number of fields set
        """
        client = await self._ensure_connection()
        result = await client.hset(name, mapping=mapping)  # type: ignore[misc]
        return int(result) if result is not None else 0

    async def hget(self, name: str, key: str) -> Optional[str]:
        """
        Get hash field value.

        Args:
            name: Hash name
            key: Field name

        Returns:
            Field value or None
        """
        client = await self._ensure_connection()
        result = await client.hget(name, key)  # type: ignore[misc]
        return str(result) if result is not None else None

    async def hgetall(self, name: str) -> Dict[str, str]:
        """
        Get all hash fields and values.

        Args:
            name: Hash name

        Returns:
            Dictionary of field-value pairs
        """
        client = await self._ensure_connection()
        result = await client.hgetall(name)  # type: ignore[misc]
        return {str(k): str(v) for k, v in result.items()}

    async def hdel(self, name: str, *keys: str) -> int:
        """
        Delete hash fields.

        Args:
            name: Hash name
            keys: Field names to delete

        Returns:
            Number of fields deleted
        """
        client = await self._ensure_connection()
        result = await client.hdel(name, *keys)  # type: ignore[misc]
        return int(result)

    # List Operations
    async def lpush(self, name: str, *values: str) -> int:
        """
        Push values to the left of list.

        Args:
            name: List name
            values: Values to push

        Returns:
            List length after push
        """
        client = await self._ensure_connection()
        result = await client.lpush(name, *values)  # type: ignore[misc]
        return int(result)

    async def rpush(self, name: str, *values: str) -> int:
        """
        Push values to the right of list.

        Args:
            name: List name
            values: Values to push

        Returns:
            List length after push
        """
        client = await self._ensure_connection()
        result = await client.rpush(name, *values)  # type: ignore[misc]
        return int(result)

    async def lpop(self, name: str) -> Optional[str]:
        """
        Pop value from the left of list.

        Args:
            name: List name

        Returns:
            Popped value or None
        """
        client = await self._ensure_connection()
        result = await client.lpop(name)  # type: ignore[misc]
        return str(result) if result is not None else None

    async def rpop(self, name: str) -> Optional[str]:
        """
        Pop value from the right of list.

        Args:
            name: List name

        Returns:
            Popped value or None
        """
        client = await self._ensure_connection()
        result = await client.rpop(name)  # type: ignore[misc]
        return str(result) if result is not None else None

    async def lrange(self, name: str, start: int = 0, end: int = -1) -> List[str]:
        """
        Get list range.

        Args:
            name: List name
            start: Start index
            end: End index (-1 for end of list)

        Returns:
            List of values
        """
        client = await self._ensure_connection()
        result = await client.lrange(name, start, end)  # type: ignore[misc]
        return [str(item) for item in result]

    # Distributed Lock Operations
    async def acquire_lock(
        self, lock_key: str, timeout: int = 30, identifier: Optional[str] = None
    ) -> Optional[str]:
        """
        Acquire distributed lock.

        Args:
            lock_key: Lock key
            timeout: Lock timeout in seconds
            identifier: Lock identifier (auto-generated if None)

        Returns:
            Lock identifier if acquired, None otherwise
        """

        if identifier is None:
            identifier = str(uuid.uuid4())

        client = await self._ensure_connection()

        # Try to acquire lock with expiration
        acquired = await client.set(lock_key, identifier, nx=True, ex=timeout)

        if acquired:
            logger.debug("Lock acquired: %s with identifier: %s", lock_key, identifier)
            return identifier

        logger.debug("Failed to acquire lock: %s", lock_key)
        return None

    async def release_lock(self, lock_key: str, identifier: str) -> bool:
        """
        Release distributed lock.

        Args:
            lock_key: Lock key
            identifier: Lock identifier

        Returns:
            True if lock was released, False otherwise
        """
        client = await self._ensure_connection()

        # Lua script to ensure atomic check-and-delete
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        try:
            result = await client.eval(lua_script, 1, lock_key, identifier)  # type: ignore[misc]
            result_int = int(result) if result is not None else 0
            if result_int:
                logger.debug(
                    "Lock released: %s with identifier: %s", lock_key, identifier
                )
                return True

            logger.warning(
                "Lock release failed: %s with identifier: %s", lock_key, identifier
            )
            return False
        except Exception as e:
            logger.error("Error releasing lock %s: %s", lock_key, str(e))
            return False

    @asynccontextmanager
    async def lock(
        self, lock_key: str, timeout: int = 30, wait_timeout: int = 10
    ) -> AsyncGenerator[str, None]:
        """
        Context manager for distributed lock.

        Args:
            lock_key: Lock key
            timeout: Lock timeout in seconds
            wait_timeout: Maximum time to wait for lock acquisition

        Yields:
            Lock identifier if acquired

        Raises:
            RedisException: If lock cannot be acquired
        """
        start_time = time.time()
        identifier = None

        # Try to acquire lock with retries
        while time.time() - start_time < wait_timeout:
            identifier = await self.acquire_lock(lock_key, timeout)
            if identifier:
                break
            await asyncio.sleep(settings.redis_lock__retry_sleep_interval)

        if not identifier:
            raise RedisException(
                RedisErrorCode.LOCK_FAILED,
                f"Failed to acquire lock {lock_key} within {wait_timeout} seconds",
            )

        try:
            yield identifier
        finally:
            await self.release_lock(lock_key, identifier)

    # Health Check
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform Redis health check.

        Returns:
            Health check result
        """
        try:
            client = await self._ensure_connection()

            # Test basic operations
            start_time = time.time()
            await client.ping()
            ping_time = time.time() - start_time

            # Get Redis info
            info = await client.info("server")

            # Get connection pool info
            pool_info = {}
            if self._pool:
                try:
                    pool_info = {
                        "max_connections": getattr(
                            self._pool, "max_connections", "N/A"
                        ),
                        "created_connections": getattr(
                            self._pool, "created_connections", "N/A"
                        ),
                        "available_connections": len(
                            getattr(self._pool, "_available_connections", [])
                        ),
                        "in_use_connections": len(
                            getattr(self._pool, "_in_use_connections", [])
                        ),
                    }
                except Exception as e:
                    pool_info = {"error": f"Failed to get pool info: {str(e)}"}

            return {
                "status": "healthy",
                "ping_time_ms": round(ping_time * 1000, 2),
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "uptime_in_seconds": info.get("uptime_in_seconds"),
                "connection_pool": pool_info,
                "config": {
                    "ssl_enabled": settings.redis__ssl,
                    "database": settings.redis__db,
                    "host": settings.redis__host,
                    "port": settings.redis__port,
                    "connect_timeout_seconds": settings.redis__connect_timeout,
                    "socket_timeout_seconds": settings.redis__socket_timeout,
                    "lock_retry_sleep_interval": settings.redis_lock__retry_sleep_interval,
                },
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


class _RedisClientManager:
    """Thread-safe Redis client manager using singleton pattern."""

    def __init__(self) -> None:
        self._client: Optional[RedisClient] = None
        self._lock = asyncio.Lock()

    @property
    def client(self) -> Optional[RedisClient]:
        """Get the current client instance (may be None)."""
        return self._client

    def get_client_sync(self) -> RedisClient:
        """
        Get Redis client instance synchronously with lazy initialization.

        Returns:
            RedisClient: Redis client instance

        Note:
            This method is for synchronous contexts only.
            The actual connection is established lazily when first used.
        """
        if self._client is None:
            self._client = RedisClient()
        return self._client

    async def get_client(self) -> RedisClient:
        """
        Get Redis client instance with lazy initialization.

        Returns:
            RedisClient: Redis client instance
        """
        if self._client is not None:
            return self._client

        async with self._lock:
            if self._client is None:
                self._client = RedisClient()
            return self._client

    async def close_client(self) -> None:
        """Close Redis client and cleanup resources."""
        async with self._lock:
            if self._client:
                await self._client.close()
                self._client = None


# Module-level client manager instance
_client_manager = _RedisClientManager()


def get_redis_client() -> RedisClient:
    """
    Get Redis client instance.

    Returns:
        RedisClient: Redis client instance

    Note:
        This function returns a client that may not be connected yet.
        The actual connection is established lazily when first used.
    """
    return _client_manager.get_client_sync()


async def get_redis_client_async() -> RedisClient:
    """
    Get Redis client instance asynchronously with proper connection handling.

    Returns:
        RedisClient: Connected Redis client instance
    """
    return await _client_manager.get_client()


async def close_redis_client() -> None:
    """Close Redis client and cleanup resources."""
    await _client_manager.close_client()


async def test_redis_connection() -> Dict[str, Any]:
    """Test Redis connection and return status."""
    try:
        client = await get_redis_client_async()
        result = await client.health_check()

        if result.get("status") == "healthy":
            logger.info("Redis connection test successful")
        else:
            logger.warning("Redis connection test failed: %s", result.get("error"))

        return result

    except Exception as e:
        logger.error("Redis connection test failed: %s", str(e))
        raise RedisException(
            RedisErrorCode.CONNECTION_FAILED, f"Redis connection test failed: {str(e)}"
        ) from e
