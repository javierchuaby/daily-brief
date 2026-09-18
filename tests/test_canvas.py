"""Tests for daily_brief.canvas module."""


class TestCanvasClient:
    """Test the CanvasClient class."""

    def test_init(self):
        """Test CanvasClient initialization."""
        from daily_brief.canvas import CanvasClient

        client = CanvasClient(
            base_url="https://canvas.nus.edu.sg", api_token="test_token"
        )

        assert client.base_url == "https://canvas.nus.edu.sg"
        assert client.api_token == "test_token"
        assert client.timeout == 30  # default


class TestCanvasAPIFunctions:
    """Test Canvas API utility functions."""

    def test_format_assignment(self):
        """Test assignment formatting."""
        from daily_brief.canvas.api import format_assignment

        assignment = {
            "name": "Assignment 1",
            "due_at": "2026-09-15T23:59:59Z",
            "points_possible": 100,
            "submissions_count": 5,
        }

        formatted = format_assignment(assignment)
        assert "Assignment 1" in formatted
        assert "Due:" in formatted

    def test_format_quiz(self):
        """Test quiz formatting."""
        from daily_brief.canvas.api import format_quiz

        quiz = {
            "title": "Quiz 1",
            "due_at": "2026-09-16T23:59:59Z",
            "question_count": 10,
            "time_limit": 30,
        }

        formatted = format_quiz(quiz)
        assert "Quiz 1" in formatted
        assert "Due:" in formatted

    def test_format_assignment_with_future_date(self):
        """Test assignment formatting with future due date."""
        from daily_brief.canvas.api import format_assignment
        from datetime import datetime, timedelta, timezone

        future_date = datetime.now(timezone.utc) + timedelta(days=7)
        due_at = future_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        assignment = {
            "name": "Assignment 2",
            "due_at": due_at,
            "points_possible": 50,
            "submissions_count": 0,
        }

        formatted = format_assignment(assignment)
        assert "Assignment 2" in formatted
        assert (
            "in 7 days" in formatted
            or "in 6 days" in formatted
            or "in 8 days" in formatted
        )

    def test_format_quiz_with_no_due_date(self):
        """Test quiz formatting with no due date."""
        from daily_brief.canvas.api import format_quiz

        quiz = {"title": "Quiz 2", "due_at": "", "question_count": 5, "time_limit": 15}

        formatted = format_quiz(quiz)
        assert "Quiz 2" in formatted
        assert "No due date" in formatted


class TestSgtConversion:
    """Test that extracted Canvas data is normalized to SGT."""

    def test_extract_assignments_due_at_converted_to_sgt(self):
        from daily_brief.canvas.api import extract_assignments_data

        assignments = [
            {
                "id": 1,
                "name": "Assignment2",
                "due_at": "2026-09-14T15:59:59Z",  # 23:59:59 SGT same day
                "points_possible": 25,
                "published": True,
            }
        ]

        data = extract_assignments_data(assignments)

        assert data[0]["due_at"] == "2026-09-14T23:59:59+08:00"
        assert data[0]["due_date"] == "2026-09-14T23:59:59+08:00"

    def test_extract_quizzes_due_date_rolls_over_midnight(self):
        from daily_brief.canvas.api import extract_quizzes_data

        quizzes = [
            {
                "id": 1,
                "title": "Lab 4 Pre-Lab Quiz",
                "due_at": "2026-09-14T22:00:00Z",  # 06:00 SGT next day
                "question_count": 4,
                "time_limit": 180,
                "allowed_attempts": 1,
                "published": True,
            }
        ]

        data = extract_quizzes_data(quizzes)

        assert data[0]["due_at"] == "2026-09-15T06:00:00+08:00"
        assert data[0]["due_date"].startswith("2026-09-15")

    def test_extract_announcements_posted_at_converted(self):
        from daily_brief.canvas.api import extract_announcements_data

        announcements = [
            {
                "id": 1,
                "title": "Announcement",
                "message": "Hello",
                "posted_at": "2026-09-13T11:23:37Z",  # 19:23 SGT same day
                "is_pinned": False,
                "created_at": "2026-09-13T11:23:37Z",
                "context_code": "course_1",
            }
        ]

        data = extract_announcements_data(announcements)

        assert data[0]["posted_at"] == "2026-09-13T19:23:37+08:00"
        assert data[0]["created_at"] == "2026-09-13T19:23:37+08:00"

    def test_format_assignment_shows_sgt_time(self):
        from daily_brief.canvas.api import format_assignment

        assignment = {
            "name": "Assignment 2",
            "due_at": "2026-09-14T15:59:59Z",
            "points_possible": 25,
            "submissions_count": 0,
        }

        formatted = format_assignment(assignment)
        assert "2026-09-14 23:59 SGT" in formatted

    def test_extract_assignments_filters_submitted_only_when_user_submitted(self):
        from daily_brief.canvas.api import extract_assignments_data

        assignments = [
            {
                "id": 1,
                "name": "Unsubmitted Assignment (cohort has submissions)",
                "due_at": "2026-09-18T10:00:00Z",
                "has_submitted_submissions": True,
                "submission": {
                    "workflow_state": "unsubmitted",
                    "submitted_at": None,
                },
            },
            {
                "id": 2,
                "name": "Actually Submitted Assignment",
                "due_at": "2026-09-18T10:00:00Z",
                "has_submitted_submissions": True,
                "submission": {
                    "workflow_state": "submitted",
                    "submitted_at": "2026-09-04T07:51:25Z",
                },
            },
        ]

        data = extract_assignments_data(assignments)
        assert len(data) == 1
        assert data[0]["name"] == "Unsubmitted Assignment (cohort has submissions)"
