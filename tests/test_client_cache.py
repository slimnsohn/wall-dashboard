import pytest

from wall_dashboard.client import AsyncTTLCache


@pytest.mark.asyncio
async def test_returns_cached_value_on_second_call():
    cache = AsyncTTLCache()
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        return {"n": calls}

    r1 = await cache.get_or_fetch("k", 60, fetch)
    r2 = await cache.get_or_fetch("k", 60, fetch)
    assert r1 == {"n": 1}
    assert r2 == {"n": 1}
    assert calls == 1


@pytest.mark.asyncio
async def test_serves_last_good_when_fetch_raises():
    cache = AsyncTTLCache()

    async def first():
        return {"n": 1}

    async def boom():
        raise RuntimeError("network down")

    await cache.get_or_fetch("k", 0, first)
    # TTL=0 -> expired -> boom raises -> serve last-good
    result = await cache.get_or_fetch("k", 0, boom)
    assert result == {"n": 1}


@pytest.mark.asyncio
async def test_reraises_when_no_last_good():
    cache = AsyncTTLCache()

    async def boom():
        raise RuntimeError("network down")

    with pytest.raises(RuntimeError, match="network down"):
        await cache.get_or_fetch("k", 60, boom)
