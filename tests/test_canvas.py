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

        assignment = {
            "name": "Assignment 2",
            "due_at": "2026-09-20T23:59:59Z",
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
