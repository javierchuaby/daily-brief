"""File system storage implementation."""

import json
from pathlib import Path

from daily_brief.interfaces import StorageInterface


class FileStorage(StorageInterface):
    """Storage adapter for file system operations."""

    def save_json(self, path: Path, data: dict) -> None:
        """Save data as JSON to a file.

        Args:
            path: Path to the file
            data: Dictionary to serialize as JSON
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
