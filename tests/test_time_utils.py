import pytest

from wall_dashboard.time_utils import (
    format_clock_time,
    format_countdown,
    gtfs_time_to_minutes,
    minutes_to_hhmm,
    parse_hhmm,
)


class TestParseHHMM:
    def test_zero_padded(self):
        assert parse_hhmm("06:43") == 403

    def test_non_padded_hour(self):
        assert parse_hhmm("6:43") == 403

    def test_bad_string_raises(self):
        with pytest.raises(ValueError, match="Bad time"):
            parse_hhmm("not a time")


class TestMinutesToHHMM:
    def test_zero_pads_hour(self):
        assert minutes_to_hhmm(451) == "07:31"

    def test_afternoon(self):
        assert minutes_to_hhmm(1032) == "17:12"

    def test_midnight(self):
        assert minutes_to_hhmm(0) == "00:00"


class TestGtfsTimeToMinutes:
    def test_zero_padded(self):
        assert gtfs_time_to_minutes("07:31:00") == 451

    def test_non_padded_hour(self):
        assert gtfs_time_to_minutes("7:31:00") == 451

    def test_wraps_hours_past_24(self):
        assert gtfs_time_to_minutes("65:12:00") == 1032

    def test_bad_string_raises(self):
        with pytest.raises(ValueError, match="Bad GTFS time"):
            gtfs_time_to_minutes("nope")


class TestFormatCountdown:
    def test_under_hour(self):
        assert format_countdown(9) == "9 min"

    def test_at_zero(self):
        assert format_countdown(0) == "0 min"

    def test_at_59(self):
        assert format_countdown(59) == "59 min"

    def test_at_exactly_one_hour(self):
        assert format_countdown(60) == "1h 0m"

    def test_over_an_hour(self):
        assert format_countdown(69) == "1h 9m"


class TestFormatClockTime:
    def test_morning(self):
        assert format_clock_time(403) == "6:43 AM"

    def test_midnight(self):
        assert format_clock_time(0) == "12:00 AM"

    def test_noon(self):
        assert format_clock_time(720) == "12:00 PM"

    def test_evening_pads_minutes(self):
        assert format_clock_time(1382) == "11:02 PM"

    def test_wraps_tomorrow_values(self):
        assert format_clock_time(1446) == "12:06 AM"
