from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class AsyncTTLCache:
    """In-memory TTL cache with last-good fallback when refresh fails."""

    def __init__(self) -> None:
        self._fresh: dict[str, tuple[float, Any]] = {}
        self._last_good: dict[str, Any] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    async def get_or_fetch(
        self,
        key: str,
        ttl_seconds: float,
        fetch: Callable[[], Awaitable[Any]],
    ) -> Any:
        now = time.monotonic()
        cached = self._fresh.get(key)
        if cached and (now - cached[0]) < ttl_seconds:
            return cached[1]

        async with self._lock(key):
            cached = self._fresh.get(key)
            if cached and (time.monotonic() - cached[0]) < ttl_seconds:
                return cached[1]
            try:
                value = await fetch()
            except Exception as exc:
                if key in self._last_good:
                    logger.warning("fetch failed for %s; serving last-good (%s)", key, exc)
                    return self._last_good[key]
                raise
            self._fresh[key] = (time.monotonic(), value)
            self._last_good[key] = value
            return value


_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0),
        )
    return _client


async def close_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


_cache: AsyncTTLCache | None = None


def get_cache() -> AsyncTTLCache:
    global _cache
    if _cache is None:
        _cache = AsyncTTLCache()
    return _cache
