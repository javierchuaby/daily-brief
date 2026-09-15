"""Tests for daily_brief.coursemology module."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace


class TestCoursemology:
    """Test the Coursemology scraper."""

    def test_imports(self):
        """Test imports work correctly."""
        from daily_brief.coursemology import fetch_coursemology_data

        assert fetch_coursemology_data is not None


class TestSgtNormalization:
    """Test that extracted Coursemology data is normalized to SGT."""

    def test_extract_assessments_data_converts_utc_to_sgt(self):
        from daily_brief.coursemology.api import extract_assessments_data

        utc = timezone.utc
        assessment = SimpleNamespace(
            id=1,
            title="Problem Set 2",
            description=None,
            end_at=SimpleNamespace(
                effective_time=datetime(2026, 9, 19, 15, 59, tzinfo=utc)
            ),
            start_at=SimpleNamespace(
                effective_time=datetime(2026, 9, 3, 10, 0, tzinfo=utc)
            ),
            time_limit=None,
            published=True,
            autograded=False,
            status="attempting",
            base_exp=4200,
            time_bonus_exp=None,
        )

        data = extract_assessments_data(SimpleNamespace(assessments=[assessment]))

        assert data[0]["due_date"] == "2026-09-19T23:59:00+08:00"
        assert data[0]["start_date"] == "2026-09-03T18:00:00+08:00"

    def test_extract_assessments_data_keeps_sgt_offset(self):
        from daily_brief.coursemology.api import extract_assessments_data

        sgt = timezone(timedelta(hours=8))
        assessment = SimpleNamespace(
            id=1,
            title="Capstone",
            description=None,
            end_at=SimpleNamespace(
                effective_time=datetime(2026, 11, 13, 23, 59, tzinfo=sgt)
            ),
            start_at=None,
            time_limit=None,
            published=True,
            autograded=False,
            status="attempting",
            base_exp=None,
            time_bonus_exp=None,
        )

        data = extract_assessments_data(SimpleNamespace(assessments=[assessment]))

        assert data[0]["due_date"] == "2026-11-13T23:59:00+08:00"
        assert data[0]["start_date"] is None

    def test_extract_announcements_data_converts_utc_to_sgt(self):
        from daily_brief.coursemology.api import extract_announcements_data

        utc = timezone.utc
        announcement = SimpleNamespace(
            id=1,
            title="Examplify",
            content="<p>...</p>",
            start_time=datetime(2026, 9, 14, 7, 0, tzinfo=utc),
            end_time=datetime(2026, 9, 21, 7, 0, tzinfo=utc),
            is_unread=False,
            is_sticky=False,
            creator=None,
            permissions=None,
        )

        data = extract_announcements_data(SimpleNamespace(announcements=[announcement]))

        assert data[0]["start_time"] == "2026-09-14T15:00:00+08:00"
        assert data[0]["end_time"] == "2026-09-21T15:00:00+08:00"

    def test_extract_submissions_data_converts_to_sgt(self):
        from daily_brief.coursemology.api import extract_submissions_data

        utc = timezone.utc
        submission = SimpleNamespace(
            id=1,
            course_user_id=1,
            course_user_name="Test",
            assessment_id=1,
            assessment_title="PS1",
            submitted_at=datetime(2026, 9, 9, 12, 18, 54, tzinfo=utc),
            status="published",
            current_grade="36.0",
            max_grade="36.0",
            is_graded_not_published=False,
            points_awarded=4200,
        )

        data = extract_submissions_data(SimpleNamespace(submissions=[submission]))

        assert data[0]["submitted_at"] == "2026-09-09T20:18:54+08:00"
