"""Tests for service implementations."""

from unittest.mock import MagicMock, patch

import pytest

from daily_brief.services.file_storage import FileStorage
from daily_brief.services.gmail_sender import GmailSender
from daily_brief.services.gemini_service import GeminiAIService


class TestGmailSender:
    """Tests for GmailSender service."""

    @pytest.fixture
    def sender(self):
        """Create a GmailSender instance."""
        return GmailSender()

    @patch("daily_brief.services.gmail_sender.get_env_var")
    @patch("daily_brief.services.gmail_sender.smtplib.SMTP")
    def test_send_success(self, mock_smtp, mock_get_env, sender):
        """Test successful email sending."""
        # Setup
        mock_get_env.side_effect = lambda key: {
            "GMAIL_SENDER": "sender@example.com",
            "GMAIL_APP_PASSWORD": "password",
        }.get(key)
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

        # Act
        result = sender.send("recipient@example.com", "Test Subject", "Test Content")

        # Assert
        assert result is True
        mock_smtp_instance.send_message.assert_called_once()

    @patch("daily_brief.services.gmail_sender.get_env_var")
    @patch("daily_brief.services.gmail_sender.smtplib.SMTP")
    def test_send_auth_failure(self, mock_smtp, mock_get_env, sender):
        """Test email sending with authentication failure."""
        # Setup
        mock_get_env.side_effect = lambda key: {
            "GMAIL_SENDER": "sender@example.com",
            "GMAIL_APP_PASSWORD": "wrong_password",
        }.get(key)
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
        mock_smtp_instance.send_message.side_effect = Exception("Auth failed")

        # Act
        result = sender.send("recipient@example.com", "Test Subject", "Test Content")

        # Assert
        assert result is False


class TestFileStorage:
    """Tests for FileStorage service."""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create a FileStorage instance with temp directory."""
        return FileStorage()

    def test_save_json(self, tmp_path, storage):
        """Test saving JSON data to file."""
        # Setup
        data = {"key": "value", "number": 42}
        filepath = tmp_path / "test" / "data.json"

        # Act
        storage.save_json(filepath, data)

        # Assert
        assert filepath.exists()
        import json

        with open(filepath) as f:
            loaded = json.load(f)
        assert loaded == data

    def test_save_json_creates_directory(self, tmp_path, storage):
        """Test that save_json creates parent directories."""
        # Setup
        data = {"test": "data"}
        filepath = tmp_path / "nested" / "deep" / "data.json"

        # Act
        storage.save_json(filepath, data)

        # Assert
        assert filepath.exists()


class TestGeminiAIService:
    """Tests for GeminiAIService."""

    @pytest.fixture
    def service(self):
        """Create a GeminiAIService instance."""
        from daily_brief.services.gemini_service import GeminiAIService
        with patch('daily_brief.services.gemini_service.genai.Client'):
            return GeminiAIService()

    def test_synthesize_success(self, service):
        """Test successful AI synthesis."""
        data = {"test": "data"}
        current_date_str = "2026-09-18"
        
        mock_interaction = MagicMock()
        mock_interaction.output_text = '{"urgent": [], "important": [{"source": "Canvas", "title": "HW", "date_str": "2026-09-20", "action_item": "Do it"}], "recent_updates": [], "later_deadlines": []}'
        service.client.interactions.create.return_value = mock_interaction
        
        result = service.synthesize(data, current_date_str)
        assert "## 📌 IMPORTANT (This Week)" in result
        assert "Canvas" in result
        assert "HW" in result

    def test_synthesize_failure(self, service):
        """Test AI synthesis failure."""
        data = {"test": "data"}
        current_date_str = "2026-09-18"
        
        service.client.interactions.create.side_effect = Exception("API error")
        
        with pytest.raises(RuntimeError, match="Gemini AI synthesis failed"):
            service.synthesize(data, current_date_str)
