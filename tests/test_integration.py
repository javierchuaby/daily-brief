"""Integration tests for daily_brief."""


class TestIntegration:
    """Integration tests for the entire automation flow."""

    def test_project_structure(self):
        """Test that project has required structure."""
        from pathlib import Path

        project_root = Path(__file__).parent.parent

        # Check required directories exist
        assert (project_root / "src").exists()
        assert (project_root / "src/daily_brief").exists()
        assert (project_root / "tests").exists()

        # Check required files exist
        assert (project_root / "src/daily_brief/__init__.py").exists()
        assert (project_root / "src/daily_brief/main.py").exists()
        assert (project_root / "pyproject.toml").exists()
        assert (project_root / "requirements.txt").exists()

    def test_env_file_exists(self):
        """Test that .env.example exists (for user to copy)."""
        from pathlib import Path

        project_root = Path(__file__).parent.parent

        # .env.example should exist for users to copy
        assert (project_root / ".env.example").exists()

        # .env should exist (gitignored, but created by user)
        # This might not exist in CI, so we skip if not found
        env_path = project_root / ".env"
        if env_path.exists():
            assert env_path.is_file()
