
from wall_dashboard.amtrak import (
    calendar_bitstring,
    date_in_window,
    headsign_direction,
    northbrook_minutes,
    parse_csv,
    parse_days,
    union_bits,
)


class TestParseDays:
    def test_weekday(self):
        assert parse_days("1111100") == [1, 2, 3, 4, 5]

    def test_weekend(self):
        assert parse_days("0000011") == [0, 6]

    def test_all_seven(self):
        assert parse_days("1111111") == [0, 1, 2, 3, 4, 5, 6]

    def test_sunday_only(self):
        assert parse_days("0000001") == [0]

    def test_monday_only(self):
        assert parse_days("1000000") == [1]


class TestNorthbrookMinutes:
    def test_nb_adds_3(self):
        assert northbrook_minutes("06:43", "NB") == 406

    def test_sb_subtracts_3(self):
        assert northbrook_minutes("06:43", "SB") == 400

    def test_wraps_past_midnight(self):
        assert northbrook_minutes("00:01", "SB") == 1438


class TestParseCsv:
    def test_header_keyed(self):
        assert parse_csv("a,b\n1,2\n3,4") == [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]

    def test_crlf(self):
        assert parse_csv("a,b\r\n1,2\r\n") == [{"a": "1", "b": "2"}]

    def test_quoted_with_comma(self):
        assert parse_csv('a,b\n"x,y",z') == [{"a": "x,y", "b": "z"}]

    def test_header_only(self):
        assert parse_csv("a,b") == []

    def test_extra_fields_ignored(self):
        assert parse_csv("a,b\n1,2,3") == [{"a": "1", "b": "2"}]

    def test_empty(self):
        assert parse_csv("") == []


class TestHeadsignDirection:
    def test_chicago_sb(self):
        assert headsign_direction("Chicago") == "SB"

    def test_milwaukee_nb(self):
        assert headsign_direction("Milwaukee") == "NB"

    def test_seattle_nb(self):
        assert headsign_direction("Seattle") == "NB"


class TestCalendarBitstring:
    def test_weekday(self):
        row = {"monday": "1", "tuesday": "1", "wednesday": "1", "thursday": "1",
               "friday": "1", "saturday": "0", "sunday": "0"}
        assert calendar_bitstring(row) == "1111100"

    def test_all_days(self):
        row = {"monday": "1", "tuesday": "1", "wednesday": "1", "thursday": "1",
               "friday": "1", "saturday": "1", "sunday": "1"}
        assert calendar_bitstring(row) == "1111111"


class TestUnionBits:
    def test_or(self):
        assert union_bits("1111100", "0000011") == "1111111"

    def test_idempotent(self):
        assert union_bits("1000001", "1000001") == "1000001"


class TestDateInWindow:
    def test_inside(self):
        assert date_in_window("20260518", "20260517", "20270517") is True

    def test_before(self):
        assert date_in_window("20260516", "20260517", "20270517") is False

    def test_inclusive_ends(self):
        assert date_in_window("20260517", "20260517", "20270517") is True
        assert date_in_window("20270517", "20260517", "20270517") is True
