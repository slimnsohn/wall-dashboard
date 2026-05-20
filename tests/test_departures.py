from datetime import datetime

from wall_dashboard.departures import combine_scheduled_and_realtime


def _to_epoch(iso: str) -> int:
    return int(datetime.fromisoformat(iso).timestamp())


def test_returns_scheduled_when_no_realtime():
    scheduled = [{
        "trip_id": "T1",
        "scheduled_departure_iso": "2026-05-19T18:42:00-05:00",
        "destination_name": "Chicago Union Station",
    }]
    out = combine_scheduled_and_realtime(scheduled, {})
    assert out[0]["is_live"] is False
    assert out[0]["predicted_departure_iso"] is None
    assert out[0]["delay_minutes"] is None
    assert out[0]["status"] == "scheduled"


def test_marks_delayed_when_realtime_late():
    scheduled = [{
        "trip_id": "T1",
        "scheduled_departure_iso": "2026-05-19T18:42:00-05:00",
        "destination_name": "Chicago Union Station",
    }]
    realtime_by_trip = {"T1": {"predicted_epoch": _to_epoch("2026-05-19T18:46:00-05:00")}}
    out = combine_scheduled_and_realtime(scheduled, realtime_by_trip)
    assert out[0]["is_live"] is True
    assert out[0]["delay_minutes"] == 4
    assert out[0]["status"] == "delayed"


def test_dst_spring_forward_does_not_add_25_hours():
    """2026 DST spring-forward: Sunday March 8, 02:00 CST -> 03:00 CDT.
    A 06:00 train that morning should produce an ISO with offset -05:00 (CDT)."""
    scheduled = [{
        "trip_id": "T1",
        "scheduled_departure_iso": "2026-03-08T06:00:00-05:00",
        "destination_name": "CUS",
    }]
    out = combine_scheduled_and_realtime(scheduled, {})
    assert "-05:00" in out[0]["scheduled_departure_iso"]
    dt = datetime.fromisoformat(out[0]["scheduled_departure_iso"])
    assert dt.utcoffset().total_seconds() == -5 * 3600


def test_cancelled_status():
    scheduled = [{
        "trip_id": "T1",
        "scheduled_departure_iso": "2026-05-19T18:42:00-05:00",
        "destination_name": "CUS",
    }]
    out = combine_scheduled_and_realtime(scheduled, {"T1": {"canceled": True}})
    assert out[0]["status"] == "cancelled"
    assert out[0]["is_live"] is True


def test_on_time_when_realtime_matches_schedule():
    scheduled = [{
        "trip_id": "T1",
        "scheduled_departure_iso": "2026-05-19T18:42:00-05:00",
        "destination_name": "CUS",
    }]
    realtime_by_trip = {"T1": {"predicted_epoch": _to_epoch("2026-05-19T18:42:00-05:00")}}
    out = combine_scheduled_and_realtime(scheduled, realtime_by_trip)
    assert out[0]["status"] == "on_time"
    assert out[0]["delay_minutes"] == 0
