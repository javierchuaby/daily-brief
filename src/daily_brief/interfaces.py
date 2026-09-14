"""Core interfaces for service abstractions.

This module defines the seams where the application interacts with external services.
Each interface is designed for testability, with minimal surface area and clear contracts.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol


class EmailSender(ABC):
    """Interface for sending emails.

    This abstraction allows the application to send emails without being coupled to
    a specific email provider (Gmail, SendGrid, etc.) or implementation details (SMTP).
    """

    @abstractmethod
    def send(self, to: str, subject: str, content: str) -> bool:
        """Send an email.

        Args:
            to: Recipient email address
            subject: Email subject line
            content: Plain text email body

        Returns:
            True if email was sent successfully, False otherwise

        Invariants:
            - The method should not raise exceptions on failure
            - Return False on any error (authentication, network, etc.)
        """


class StorageInterface(ABC):
    """Interface for file system operations.

    This abstraction allows the application to save and load data without being
    coupled to the specific file format or storage location.
    """

    @abstractmethod
    def save_json(self, path: Path, data: dict) -> None:
        """Save data as JSON to a file.

        Args:
            path: Path to the file
            data: Dictionary to serialize as JSON
        """


class AIService(ABC):
    """Interface for AI synthesis services.

    This abstraction allows the application to use different AI providers
    (OpenCode, GPT, etc.) without changing business logic.
    """

    @abstractmethod
    def synthesize(self, data: dict, prompt: str) -> str:
        """Synthesize content using AI.

        Args:
            data: Raw data to be used as context
            prompt: Instruction prompt for the AI

        Returns:
            Generated content as a string

        Invariants:
            - Should raise RuntimeError on failure
            - May raise FileNotFoundError if OpenCode CLI not available
        """


class DataSource(Protocol):
    """Protocol for data source implementations.

    This protocol defines the interface for fetching and formatting data from
    different sources (Canvas, Coursemology, etc.). Implementations can vary
    significantly in their internal logic while maintaining a consistent interface.
    """

    def fetch(self) -> dict:  # type: ignore[empty-body]
        """Fetch raw data from the source.

        Returns:
            Dictionary containing the fetched data
        """

    def format_markdown(self, data: dict) -> str:  # type: ignore[empty-body]
        """Format data as Markdown.

        Args:
            data: Raw data from fetch()

        Returns:
            Markdown formatted string
        """

    def extract_fine_grained(self, data: dict) -> dict:  # type: ignore[empty-body]
        """Extract fine-grained data for AI processing.

        Args:
            data: Raw data from fetch()

        Returns:
            Dictionary with structured data suitable for AI synthesis
        """
