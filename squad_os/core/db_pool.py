import asyncio
import os
import aiosqlite
import functools
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")

_LOCKED_ERRORS = ("database is locked", "database disk image is malformed")

_MAX_RETRIES = int(os.environ.get("SQUAD_OS_DB_MAX_RETRIES", 5))
_INITIAL_BACKOFF = float(os.environ.get("SQUAD_OS_DB_BACKOFF", "0.1"))
_POOL_SIZE = int(os.environ.get("SQUAD_OS_DB_POOL_SIZE", 5))


def retry_on_locked(max_retries: int = _MAX_RETRIES, initial_backoff: float = _INITIAL_BACKOFF):
    """Decorator that retries an async function on SQLite 'database is locked' errors.

    Uses exponential backoff: initial_backoff * (2 ** attempt).
    Only retries on known locking errors; all other exceptions propagate immediately.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            backoff = initial_backoff
            last_error: Optional[Exception] = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except aiosqlite.Error as e:
                    error_msg = str(e).lower()
                    if any(msg in error_msg for msg in _LOCKED_ERRORS):
                        if attempt < max_retries:
                            await asyncio.sleep(backoff)
                            backoff *= 2
                            last_error = e
                            continue
                    raise
                except Exception:
                    raise
            raise last_error  # type: ignore[misc]
        return wrapper
    return decorator


class AsyncDBPool:
    """Simple async SQLite connection pool.

    Maintains a pool of reusable aiosqlite connections to reduce
    connection overhead under concurrent load.
    """

    def __init__(self, db_path: str, pool_size: int = _POOL_SIZE):
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool: asyncio.Queue[aiosqlite.Connection] = asyncio.Queue(maxsize=pool_size)
        self._initialized = False

    async def initialize(self):
        """Pre-create connections and fill the pool."""
        if self._initialized:
            return
        for _ in range(self.pool_size):
            conn = await aiosqlite.connect(self.db_path)
            await conn.execute("PRAGMA journal_mode=WAL;")
            await conn.execute("PRAGMA busy_timeout=5000;")
            await self._pool.put(conn)
        self._initialized = True

    async def acquire(self) -> aiosqlite.Connection:
        """Get a connection from the pool, creating one if necessary."""
        if not self._initialized:
            await self.initialize()
        try:
            return self._pool.get_nowait()
        except asyncio.QueueEmpty:
            conn = await aiosqlite.connect(self.db_path)
            await conn.execute("PRAGMA journal_mode=WAL;")
            await conn.execute("PRAGMA busy_timeout=5000;")
            return conn

    async def release(self, conn: aiosqlite.Connection):
        """Return a connection to the pool."""
        if self._pool.full():
            await conn.close()
        else:
            await self._pool.put(conn)

    async def close_all(self):
        """Close all connections in the pool."""
        while not self._pool.empty():
            conn = self._pool.get_nowait()
            await conn.close()
        self._initialized = False

    async def execute_with_retry(self, sql: str, params: tuple = (), max_retries: int = _MAX_RETRIES) -> aiosqlite.Cursor:
        """Execute a statement with automatic retry on locked errors."""
        conn = await self.acquire()
        try:
            cursor = await conn.execute(sql, params)
            await conn.commit()
            return cursor
        except aiosqlite.Error as e:
            await conn.rollback()
            raise
        finally:
            await self.release(conn)

    async def fetchone_with_retry(self, sql: str, params: tuple = (), max_retries: int = _MAX_RETRIES) -> Optional[tuple]:
        """Fetch one row with automatic retry on locked errors."""
        conn = await self.acquire()
        try:
            cursor = await conn.execute(sql, params)
            return await cursor.fetchone()
        except aiosqlite.Error as e:
            await conn.rollback()
            raise
        finally:
            await self.release(conn)

    async def fetchall_with_retry(self, sql: str, params: tuple = (), max_retries: int = _MAX_RETRIES) -> list:
        """Fetch all rows with automatic retry on locked errors."""
        conn = await self.acquire()
        try:
            cursor = await conn.execute(sql, params)
            return await cursor.fetchall()
        except aiosqlite.Error as e:
            await conn.rollback()
            raise
        finally:
            await self.release(conn)
