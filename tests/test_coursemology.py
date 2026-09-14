"""Tests for daily_brief.coursemology module."""


class TestCoursemology:
    """Test the Coursemology scraper."""

    def test_imports(self):
        """Test imports work correctly."""
        from daily_brief.coursemology import fetch_coursemology_data

        assert fetch_coursemology_data is not None
