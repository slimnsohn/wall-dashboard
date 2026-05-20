from datetime import datetime
from zoneinfo import ZoneInfo

from wall_dashboard.trains_view import build_trains_view

CHICAGO = ZoneInfo("America/Chicago")


def test_build_merges_and_sorts():
    metra = {"available": True, "arrivals": [
        {"trip_id": "M1", "route_id": "MD-N", "pass_minutes": 770,
         "time": "12:50 PM", "countdown_min": 8, "countdown_str": "8 min"},
    ]}
    amtrak = {"available": True, "northbound": [], "southbound": [
        {"type": "Amtrak", "passMinutes": 765},
    ]}
    now = datetime(2026, 5, 19, 12, 42, tzinfo=CHICAGO)
    view = build_trains_view(metra, amtrak, now=now, location="Northbrook")
    assert view["location"] == "Northbrook"
    assert len(view["trains"]) == 2
    # Amtrak at 12:45 (3 min) sorts before Metra at 12:50 (8 min)
    assert view["trains"][0]["type"] == "Amtrak"
    assert view["trains"][0]["countdown_str"] == "3 min"
    assert view["trains"][1]["type"] == "Metra"
    assert view["trains"][1]["countdown_str"] == "8 min"
    assert "updated_at" in view


def test_build_handles_metra_unavailable():
    metra = {"available": False, "arrivals": []}
    amtrak = {"available": True, "northbound": [], "southbound": [
        {"type": "Amtrak", "passMinutes": 765},
    ]}
    now = datetime(2026, 5, 19, 12, 42, tzinfo=CHICAGO)
    view = build_trains_view(metra, amtrak, now=now)
    assert len(view["trains"]) == 1
    assert view["trains"][0]["type"] == "Amtrak"


def test_build_drops_far_future_trains():
    """Train passing in 23 hours is not "upcoming" - countdown rolls over from negative."""
    metra = {"available": True, "arrivals": [
        {"trip_id": "M1", "route_id": "MD-N", "pass_minutes": 700,
         "time": "11:40 AM", "countdown_min": 1438, "countdown_str": "23h 58m"},
    ]}
    amtrak = {"available": True, "northbound": [], "southbound": []}
    now = datetime(2026, 5, 19, 12, 42, tzinfo=CHICAGO)
    view = build_trains_view(metra, amtrak, now=now, max_count=3)
    assert view["trains"] == []


def test_caps_at_max_count():
    metra = {"available": True, "arrivals": [
        {"trip_id": f"M{i}", "route_id": "MD-N",
         "pass_minutes": 770 + i, "time": "x", "countdown_min": i + 1,
         "countdown_str": f"{i + 1} min"}
        for i in range(8)
    ]}
    amtrak = {"available": False, "northbound": [], "southbound": []}
    now = datetime(2026, 5, 19, 12, 42, tzinfo=CHICAGO)
    view = build_trains_view(metra, amtrak, now=now, max_count=3)
    assert len(view["trains"]) == 3
