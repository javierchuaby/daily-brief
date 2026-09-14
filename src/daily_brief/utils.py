"""Utility functions for common operations."""

from datetime import datetime, timezone

import mistune


def parse_due_date(due_at: str | None) -> tuple[datetime | None, int | None]:
    """Parse ISO date string and return (datetime, days remaining).

    Args:
        due_at: ISO format date string (e.g., "2024-01-15T23:59:59Z")

    Returns:
        Tuple of (datetime object or None, days remaining or None)
    """
    if not due_at:
        return None, None
    try:
        due_date = datetime.fromisoformat(due_at.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
        now_utc = datetime.now(timezone.utc)
        return due_date, (due_date - now_utc).days
    except (ValueError, TypeError):
        return None, None


def safe_get_list(response: list | dict, key: str | None = None) -> list:
    """Extract list from API response that may be dict or list.

    Args:
        response: API response (either list or dict)
        key: Key to extract from dict if response is a dict

    Returns:
        List of items, empty if not found
    """
    if isinstance(response, dict):
        return response.get(key, []) if key else []
    return response if isinstance(response, list) else []


def safe_get_field(obj: dict | object, field: str, default: object = None) -> object:
    """Extract field from dict or object safely.

    Args:
        obj: Dictionary or object to extract field from
        field: Field name to extract
        default: Default value if field not found

    Returns:
        Field value or default
    """
    if isinstance(obj, dict):
        return obj.get(field, default)
    return getattr(obj, field, default)


def markdown_to_html(markdown_text: str) -> str:
    """Convert markdown text to HTML.

    Args:
        markdown_text: Markdown formatted string

    Returns:
        HTML formatted string
    """
    renderer = mistune.create_markdown(
        renderer=mistune.HTMLRenderer(), plugins=["strikethrough", "footnotes", "table"]
    )
    result = renderer(markdown_text)
    return result if isinstance(result, str) else str(result)
