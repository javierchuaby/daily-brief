"""
Daily Brief Automation

A comprehensive daily brief system that aggregates data from:
- Canvas (NUS LMS) - Announcements, assignments, quizzes
- Coursemology - Assessments, submissions, announcements

The system generates a concise morning brief and emails it daily.

Usage:
    python3 -m daily_brief [--dry-run] [--verbose]
"""

import os
from pathlib import Path
from typing import Dict

# Apply patches before any other imports
from daily_brief.patches.coursemology import patch_coursemology

patch_coursemology()

# Determine project root (works for both installed and development modes)
# Always use cwd to find .env file for flexibility
PROJECT_ROOT = Path.cwd()

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Try parent directory (for installed packages)
        env_path = PROJECT_ROOT.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
except ImportError:
    # dotenv not installed, environment variables should be set manually
    pass

DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"


def get_env_var(name: str, required: bool = True, default: str = "") -> str:
    """Get environment variable, with optional default."""
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Required environment variable {name} is not set")
    return value


def parse_canvas_courses(courses_str: str) -> Dict[str, int]:
    """Parse comma-separated courses string to dict.

    Args:
        courses_str: Comma-separated string like "CS2102:93752,CS2107:93790"

    Returns:
        Dict mapping course code to course ID

    Raises:
        ValueError: If courses_str has invalid format
    """
    courses: Dict[str, int] = {}
    for item in courses_str.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            raise ValueError(f"Invalid course format: '{item}'. Expected 'CODE:ID'")
        code, id_ = item.split(":", 1)
        code = code.strip()
        id_str = id_.strip()
        try:
            courses[code] = int(id_str)
        except ValueError:
            raise ValueError(f"Course ID must be numeric, got: '{id_str}'")
    return courses


def ensure_directories() -> None:
    """Create necessary directories."""
    DATA_DIR.mkdir(exist_ok=True)
