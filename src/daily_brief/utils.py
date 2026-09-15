"""Utility functions for common operations."""

import re
from datetime import datetime, timezone, tzinfo
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

import mistune

SGT = ZoneInfo("Asia/Singapore")


def to_sgt(dt: datetime | None, assume_tz: tzinfo = timezone.utc) -> datetime | None:
    """Convert a datetime to SGT. Naive datetimes are assumed to be in assume_tz."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=assume_tz)
    return dt.astimezone(SGT)


def parse_sgt_datetime(value: str | None) -> datetime | None:
    """Parse an ISO timestamp string and convert it to SGT.

    Args:
        value: ISO format timestamp (e.g., "2024-01-15T23:59:59Z")

    Returns:
        SGT-aware datetime, or None if unparseable
    """
    if not value:
        return None
    try:
        return to_sgt(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except (ValueError, TypeError):
        return None


def format_sgt(value: str | None) -> str | None:
    """Format an ISO timestamp string as SGT ISO format, preserving the input if unparseable."""
    dt = parse_sgt_datetime(value)
    return dt.isoformat() if dt else value


def parse_due_date(due_at: str | None) -> tuple[datetime | None, int | None]:
    """Parse ISO date string and return (SGT datetime, days remaining).

    Args:
        due_at: ISO format date string (e.g., "2024-01-15T23:59:59Z")

    Returns:
        Tuple of (SGT datetime object or None, days remaining or None).
        Days remaining is the difference in SGT calendar days.
    """
    if not due_at:
        return None, None
    try:
        due_date = parse_sgt_datetime(due_at)
        if due_date is None:
            return None, None
        now_sgt = datetime.now(SGT)
        return due_date, (due_date.date() - now_sgt.date()).days
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


class TextURLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.in_a_tag = False
        self.current_url = ""
        self.link_text = []
        self.in_script_or_style = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.in_script_or_style = True
            return

        if tag == "a":
            self.in_a_tag = True
            self.link_text = []
            for attr in attrs:
                if attr[0] == "href":
                    self.current_url = attr[1]
                    break
        elif tag in ("br", "p", "div", "li"):
            self.result.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.in_script_or_style = False
            return

        if tag == "a":
            self.in_a_tag = False
            link_text_str = "".join(self.link_text).strip()
            if self.current_url and link_text_str:
                self.result.append(f"[{link_text_str}]({self.current_url})")
            elif link_text_str:
                self.result.append(link_text_str)
            elif self.current_url:
                self.result.append(f"[{self.current_url}]({self.current_url})")
            self.current_url = ""
            self.link_text = []
        elif tag in ("p", "div", "li"):
            self.result.append("\n")

    def handle_data(self, data):
        if self.in_script_or_style:
            return

        if self.in_a_tag:
            self.link_text.append(data)
        else:
            self.result.append(data)


def strip_html_preserve_urls(html_content: str | None) -> str:
    """Strip HTML tags but preserve URLs as markdown [text](url)."""
    if not html_content:
        return ""
    parser = TextURLParser()
    try:
        parser.feed(html_content)
        text = "".join(parser.result)
        # Clean up multiple newlines and spaces
        text = re.sub(r"\n\s*\n", "\n\n", text)
        return text.strip()
    except Exception:
        return html_content
