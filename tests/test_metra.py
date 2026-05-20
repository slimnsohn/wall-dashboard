import time

import httpx
import pytest
import respx
from google.transit import gtfs_realtime_pb2

from wall_dashboard import client as client_mod
from wall_dashboard import config as cfg_mod
from wall_dashboard.metra import fetch_tripupdates, get_metra_arrivals_for_stop


@pytest.fixture(autouse=True)
def reset_state():
    client_mod._client = None
    client_mod._cache = None
    cfg_mod._settings = None
    yield
    client_mod._client = None
    client_mod._cache = None
    cfg_mod._settings = None


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("METRA_TOKEN", "tok-abcdef-12345678")
    monkeypatch.setenv("NORTHBROOK_STOP_ID", "NBROOK")
    monkeypatch.setenv("CUS_STOP_ID", "CUS")
    monkeypatch.setenv("NWS_LAT", "0")
    monkeypatch.setenv("NWS_LON", "0")
    monkeypatch.setenv("NWS_USER_AGENT", "wd test")


def _build_feed(entries: list[tuple[str, str, str, int]]) -> bytes:
    """entries: list of (trip_id, route_id, stop_id, arrival_epoch)."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    for trip_id, route_id, stop_id, arrival in entries:
        e = feed.entity.add()
        e.id = trip_id
        tu = e.trip_update
        tu.trip.trip_id = trip_id
        tu.trip.route_id = route_id
        stu = tu.stop_time_update.add()
        stu.stop_id = stop_id
        stu.arrival.time = arrival
    return feed.SerializeToString()


@pytest.mark.asyncio
@respx.mock
async def test_fetch_tripupdates_sends_bearer_token(env):
    future = int(time.time()) + 600
    feed_bytes = _build_feed([("T1", "MD-N", "NBROOK", future)])
    respx.get("https://gtfspublic.metrarr.com/gtfs/public/tripupdates").mock(
        return_value=httpx.Response(200, content=feed_bytes)
    )
    feed = await fetch_tripupdates()
    assert feed.entity[0].trip_update.trip.trip_id == "T1"
    sent = respx.calls.last.request
    assert sent.headers["authorization"].startswith("Bearer ")


@pytest.mark.asyncio
@respx.mock
async def test_get_metra_arrivals_filters_by_stop(env):
    future = int(time.time()) + 600
    feed_bytes = _build_feed([
        ("T1", "MD-N", "NBROOK", future),
        ("T2", "MD-N", "OTHER", future + 80),
    ])
    respx.get("https://gtfspublic.metrarr.com/gtfs/public/tripupdates").mock(
        return_value=httpx.Response(200, content=feed_bytes)
    )
    arrivals = await get_metra_arrivals_for_stop("NBROOK")
    assert len(arrivals) == 1
    assert arrivals[0]["trip_id"] == "T1"
    assert arrivals[0]["arrival_epoch"] == future


@pytest.mark.asyncio
@respx.mock
async def test_get_metra_arrivals_drops_already_passed(env):
    past = int(time.time()) - 600
    feed_bytes = _build_feed([
        ("T_PAST", "MD-N", "NBROOK", past),
    ])
    respx.get("https://gtfspublic.metrarr.com/gtfs/public/tripupdates").mock(
        return_value=httpx.Response(200, content=feed_bytes)
    )
    arrivals = await get_metra_arrivals_for_stop("NBROOK")
    assert arrivals == []
