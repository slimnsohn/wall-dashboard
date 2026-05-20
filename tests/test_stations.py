import pytest

from wall_dashboard.stations import AmbiguousStation, resolve_station

SAMPLE_STOPS = [
    {"stop_id": "GLENVIEW", "stop_name": "Glenview"},
    {"stop_id": "GLENNGLEN", "stop_name": "Glen of North Glenview"},
    {"stop_id": "CUS", "stop_name": "Chicago Union Station"},
    {"stop_id": "NBROOK", "stop_name": "Northbrook"},
]


def test_exact_stop_id_wins():
    r = resolve_station(SAMPLE_STOPS, "GLENVIEW")
    assert r["stop_id"] == "GLENVIEW"


def test_substring_matches_returns_list_when_ambiguous():
    with pytest.raises(AmbiguousStation) as exc:
        resolve_station(SAMPLE_STOPS, "Glenview")
    assert len(exc.value.matches) == 2
    ids = {m["stop_id"] for m in exc.value.matches}
    assert ids == {"GLENVIEW", "GLENNGLEN"}


def test_case_insensitive_single_match():
    r = resolve_station(SAMPLE_STOPS, "northbrook")
    assert r["stop_id"] == "NBROOK"


def test_no_match_raises():
    with pytest.raises(KeyError):
        resolve_station(SAMPLE_STOPS, "Nowhere")
