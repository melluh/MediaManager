import asyncio
import time
from collections.abc import Awaitable, Callable


class AsyncTTLCache[K, V]:
    def __init__(self, ttl_seconds: float, max_size: int | None = None) -> None:
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._store: dict[K, tuple[float, V]] = {}
        self._locks: dict[K, asyncio.Lock] = {}
        self._locks_guard = asyncio.Lock()

    def _is_fresh(self, key: K) -> bool:
        entry = self._store.get(key)
        return entry is not None and (time.monotonic() - entry[0]) < self._ttl

    async def get_or_set(self, key: K, factory: Callable[[], Awaitable[V]]) -> V:
        if self._is_fresh(key):
            return self._store[key][1]

        async with self._locks_guard:
            lock = self._locks.setdefault(key, asyncio.Lock())

        async with lock:
            if self._is_fresh(key):
                return self._store[key][1]
            value = await factory()
            self._store[key] = (time.monotonic(), value)
            if self._max_size is not None and len(self._store) > self._max_size:
                oldest_key = min(self._store, key=lambda k: self._store[k][0])
                self._store.pop(oldest_key, None)
                self._locks.pop(oldest_key, None)
            return value

    def invalidate(self, key: K) -> None:
        self._store.pop(key, None)
        self._locks.pop(key, None)
