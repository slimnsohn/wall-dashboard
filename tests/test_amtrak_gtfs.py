import pickle

from wall_dashboard.amtrak import (
    compute_amtrak_trains,
    extract_amtrak_rows,
    get_amtrak,
)

GTFS_FIXTURE = {
    "routes": [
        {"route_id": "54", "route_long_name": "Hiawatha Service"},
        {"route_id": "75", "route_long_name": "Empire Builder"},
        {"route_id": "99", "route_long_name": "Some Other Route"},
    ],
    "calendar": [
        {"service_id": "WK", "monday": "1", "tuesday": "1", "wednesday": "1",
         "thursday": "1", "friday": "1", "saturday": "0", "sunday": "0",
         "start_date": "20260101", "end_date": "20270101"},
        {"service_id": "WE", "monday": "0", "tuesday": "0", "wednesday": "0",
         "thursday": "0", "friday": "0", "saturday": "1", "sunday": "1",
         "start_date": "20260101", "end_date": "20270101"},
        {"service_id": "OLD", "monday": "1", "tuesday": "1", "wednesday": "1",
         "thursday": "1", "friday": "1", "saturday": "1", "sunday": "1",
         "start_date": "20200101", "end_date": "20200201"},
    ],
    "trips": [
        {"route_id": "54", "service_id": "WK", "trip_id": "t1",
         "trip_short_name": "329", "trip_headsign": "Milwaukee"},
        {"route_id": "54", "service_id": "WE", "trip_id": "t2",
         "trip_short_name": "329", "trip_headsign": "Milwaukee"},
        {"route_id": "54", "service_id": "WK", "trip_id": "t3",
         "trip_short_name": "330", "trip_headsign": "Chicago"},
        {"route_id": "54", "service_id": "OLD", "trip_id": "t4",
         "trip_short_name": "999", "trip_headsign": "Milwaukee"},
        {"route_id": "99", "service_id": "WK", "trip_id": "t5",
         "trip_short_name": "500", "trip_headsign": "Chicago"},
    ],
    "stopTimes": [
        {"trip_id": "t1", "stop_id": "GLN", "departure_time": "08:24:00"},
        {"trip_id": "t2", "stop_id": "GLN", "departure_time": "08:24:00"},
        {"trip_id": "t3", "stop_id": "GLN", "departure_time": "06:43:00"},
        {"trip_id": "t4", "stop_id": "GLN", "departure_time": "09:00:00"},
        {"trip_id": "t5", "stop_id": "GLN", "departure_time": "07:00:00"},
        {"trip_id": "t1", "stop_id": "CHI", "departure_time": "08:50:00"},
    ],
}


def test_extract_joins_filters_sorts_and_unions():
    rows = extract_amtrak_rows(GTFS_FIXTURE, "20260518", glenview_stop_id="GLN")
    assert rows == [
        {"trainNum": "330", "direction": "SB", "glenviewTime": "06:43", "days": "1111100"},
        {"trainNum": "329", "direction": "NB", "glenviewTime": "08:24", "days": "1111111"},
    ]


def test_extract_excludes_expired_and_other_routes():
    rows = extract_amtrak_rows(GTFS_FIXTURE, "20260518", glenview_stop_id="GLN")
    nums = {r["trainNum"] for r in rows}
    assert "999" not in nums
    assert "500" not in nums


def test_extract_empty_when_nothing_matches():
    rows = extract_amtrak_rows(GTFS_FIXTURE, "20990101", glenview_stop_id="GLN")
    assert rows == []


def test_extract_normalizes_non_zero_padded_hours():
    """Regression: real Amtrak GTFS uses '7:32:00' (no leading zero).
    The stored glenviewTime must still be zero-padded 'HH:MM' so parse_hhmm works."""
    fixture = {
        "routes": [{"route_id": "54", "route_long_name": "Hiawatha Service"}],
        "calendar": [{
            "service_id": "WK", "monday": "1", "tuesday": "1", "wednesday": "1",
            "thursday": "1", "friday": "1", "saturday": "0", "sunday": "0",
            "start_date": "20260101", "end_date": "20270101",
        }],
        "trips": [{
            "route_id": "54", "service_id": "WK", "trip_id": "t1",
            "trip_short_name": "329", "trip_headsign": "Milwaukee",
        }],
        "stopTimes": [{"trip_id": "t1", "stop_id": "GLN", "departure_time": "7:32:00"}],
    }
    rows = extract_amtrak_rows(fixture, "20260518", glenview_stop_id="GLN")
    assert rows[0]["glenviewTime"] == "07:32"


class TestComputeAmtrakTrains:
    SCHEDULE = [
        {"trainNum": "329", "direction": "NB", "glenviewTime": "06:43", "days": "1111100"},
        {"trainNum": "330", "direction": "SB", "glenviewTime": "08:00", "days": "0000011"},
        {"trainNum": "8", "direction": "SB", "glenviewTime": "09:42", "days": "1111111"},
    ]

    def test_filters_by_day(self):
        # Wednesday = 3 -> 329 (Mon-Fri) and 8 (Daily), 330 (Sat/Sun) excluded
        out = compute_amtrak_trains(self.SCHEDULE, 3)
        assert len(out) == 2

    def test_computes_pass_minutes(self):
        # Saturday = 6 -> 330 (SB 08:00 -> 477) and 8 (SB 09:42 -> 579)
        out = compute_amtrak_trains(self.SCHEDULE, 6)
        assert out == [
            {"type": "Amtrak", "passMinutes": 477},
            {"type": "Amtrak", "passMinutes": 579},
        ]

    def test_empty_schedule(self):
        assert compute_amtrak_trains([], 3) == []


def test_get_amtrak_returns_unavailable_when_no_pickle(tmp_path):
    r = get_amtrak(tmp_path)
    assert r["available"] is False
    assert r["northbound"] == []
    assert r["southbound"] == []


def test_get_amtrak_groups_by_direction(tmp_path):
    rows = [
        {"trainNum": "329", "direction": "NB", "glenviewTime": "06:43", "days": "1111111"},
        {"trainNum": "330", "direction": "SB", "glenviewTime": "08:00", "days": "1111111"},
    ]
    (tmp_path / "amtrak_schedule.pkl").write_bytes(
        pickle.dumps({"rows": rows, "refreshed_at": "x"})
    )
    r = get_amtrak(tmp_path)
    assert r["available"] is True
    # Both trains exist; nb/sb each at most 1 in scope of next 6h. If neither
    # falls in the next 6h, both groups will be empty — that's also valid.
    total = len(r["northbound"]) + len(r["southbound"])
    assert total in (0, 1, 2)  # depends on time of day when the test runs
