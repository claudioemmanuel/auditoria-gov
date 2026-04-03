from datetime import date, datetime, timezone

import pytest

from shared.utils.time import utc_now, parse_br_date, date_range


class TestUtcNow:
    def test_has_timezone(self):
        result = utc_now()
        assert result.tzinfo is not None

    def test_is_utc(self):
        result = utc_now()
        assert result.tzinfo == timezone.utc

    def test_is_recent(self):
        before = datetime.now(timezone.utc)
        result = utc_now()
        after = datetime.now(timezone.utc)
        assert before <= result <= after


class TestParseBrDate:
    def test_dd_mm_yyyy(self):
        result = parse_br_date("15/03/2024")
        assert result.day == 15
        assert result.month == 3
        assert result.year == 2024

    def test_dd_mm_yyyy_with_time(self):
        result = parse_br_date("15/03/2024 10:30:00")
        assert result.hour == 10
        assert result.minute == 30

    def test_iso_date(self):
        result = parse_br_date("2024-03-15")
        assert result.day == 15
        assert result.month == 3

    def test_iso_datetime(self):
        result = parse_br_date("2024-03-15T10:30:00")
        assert result.hour == 10

    def test_has_utc_timezone(self):
        result = parse_br_date("15/03/2024")
        assert result.tzinfo == timezone.utc

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Cannot parse date"):
            parse_br_date("not-a-date")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_br_date("")


class TestDateRange:
    def test_single_day(self):
        ranges = list(date_range(date(2024, 1, 1), date(2024, 1, 2)))
        assert len(ranges) == 1
        assert ranges[0] == (date(2024, 1, 1), date(2024, 1, 2))

    def test_multi_day(self):
        ranges = list(date_range(date(2024, 1, 1), date(2024, 1, 4)))
        assert len(ranges) == 3
        assert ranges[0] == (date(2024, 1, 1), date(2024, 1, 2))
        assert ranges[2] == (date(2024, 1, 3), date(2024, 1, 4))

    def test_step_days(self):
        ranges = list(date_range(date(2024, 1, 1), date(2024, 1, 10), step_days=5))
        assert len(ranges) == 2
        assert ranges[0] == (date(2024, 1, 1), date(2024, 1, 6))
        assert ranges[1] == (date(2024, 1, 6), date(2024, 1, 10))

    def test_same_start_end(self):
        ranges = list(date_range(date(2024, 1, 1), date(2024, 1, 1)))
        assert len(ranges) == 0

    def test_step_larger_than_range(self):
        ranges = list(date_range(date(2024, 1, 1), date(2024, 1, 3), step_days=10))
        assert len(ranges) == 1
        assert ranges[0] == (date(2024, 1, 1), date(2024, 1, 3))
