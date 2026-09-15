"""Tests for daily_brief.utils timezone helpers."""

from datetime import datetime, timedelta, timezone


class TestToSgt:
    """Test to_sgt conversion."""

    def test_aware_utc_converted_to_sgt(self):
        from daily_brief.utils import to_sgt

        dt = datetime(2026, 9, 14, 15, 59, 59, tzinfo=timezone.utc)
        result = to_sgt(dt)

        assert result == datetime(
            2026, 9, 14, 23, 59, 59, tzinfo=timezone(timedelta(hours=8))
        )
        assert result.utcoffset() == timedelta(hours=8)

    def test_aware_sgt_is_identity(self):
        from daily_brief.utils import to_sgt

        dt = datetime(2026, 9, 14, 18, 0, 0, tzinfo=timezone(timedelta(hours=8)))
        result = to_sgt(dt)

        assert result.hour == 18
        assert result.day == 14

    def test_naive_assumed_utc_by_default(self):
        from daily_brief.utils import to_sgt

        dt = datetime(2026, 9, 14, 22, 0, 0)
        result = to_sgt(dt)

        assert result.day == 15
        assert result.hour == 6

    def test_naive_assumed_sgt_when_specified(self):
        from daily_brief.utils import SGT, to_sgt

        dt = datetime(2026, 9, 14, 18, 0, 0)
        result = to_sgt(dt, SGT)

        assert result.day == 14
        assert result.hour == 18

    def test_none_returns_none(self):
        from daily_brief.utils import to_sgt

        assert to_sgt(None) is None


class TestParseSgtDatetime:
    """Test parse_sgt_datetime string parsing."""

    def test_utc_z_suffix(self):
        from daily_brief.utils import parse_sgt_datetime

        result = parse_sgt_datetime("2026-09-14T15:59:59Z")

        assert result is not None
        assert result.day == 14
        assert result.hour == 23
        assert result.minute == 59
        assert result.utcoffset() == timedelta(hours=8)

    def test_date_rolls_over_midnight(self):
        from daily_brief.utils import parse_sgt_datetime

        result = parse_sgt_datetime("2026-09-14T22:00:00Z")

        assert result.day == 15
        assert result.hour == 6

    def test_offset_string_passthrough(self):
        from daily_brief.utils import parse_sgt_datetime

        result = parse_sgt_datetime("2026-09-14T15:00:00+08:00")

        assert result.day == 14
        assert result.hour == 15

    def test_invalid_returns_none(self):
        from daily_brief.utils import parse_sgt_datetime

        assert parse_sgt_datetime("not-a-date") is None
        assert parse_sgt_datetime("") is None
        assert parse_sgt_datetime(None) is None


class TestFormatSgt:
    """Test format_sgt string formatting."""

    def test_utc_z_suffix_converted(self):
        from daily_brief.utils import format_sgt

        assert format_sgt("2026-09-14T15:59:59Z") == "2026-09-14T23:59:59+08:00"

    def test_none_passthrough(self):
        from daily_brief.utils import format_sgt

        assert format_sgt(None) is None

    def test_empty_passthrough(self):
        from daily_brief.utils import format_sgt

        assert format_sgt("") == ""


class TestParseDueDate:
    """Test parse_due_date SGT behavior."""

    def test_returns_sgt_datetime(self):
        from daily_brief.utils import parse_due_date

        due, days = parse_due_date("2026-09-14T15:59:59Z")

        assert due is not None
        assert due.utcoffset() == timedelta(hours=8)
        assert due.hour == 23
        assert days is not None

    def test_local_day_difference(self):
        from datetime import date

        from daily_brief.utils import SGT, parse_due_date

        # 2026-09-21T22:00:00Z is 2026-09-22 06:00 SGT: a UTC-time floor
        # would undercount vs the SGT calendar day difference.
        due, days = parse_due_date("2026-09-21T22:00:00Z")

        expected = (date(2026, 9, 22) - datetime.now(SGT).date()).days
        assert days == expected
        assert due.day == 22

    def test_none_returns_none(self):
        from daily_brief.utils import parse_due_date

        assert parse_due_date(None) == (None, None)
        assert parse_due_date("") == (None, None)

    def test_invalid_returns_none(self):
        from daily_brief.utils import parse_due_date

        assert parse_due_date("garbage") == (None, None)
