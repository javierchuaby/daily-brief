#!/usr/bin/env python3
"""
Daily Brief Automation - Main Entry Point

Usage:
    python3 -m daily_brief
    python3 -m daily_brief --dry-run
    python3 -m daily_brief --verbose
"""

import argparse
import sys
from pathlib import Path

from daily_brief.main import main

if __name__ == "__main__":
    # Add project root to path
    PROJECT_ROOT = Path(__file__).parent.parent.resolve()
    sys.path.insert(0, str(PROJECT_ROOT))

    parser = argparse.ArgumentParser(description="Daily Brief Automation")
    parser.add_argument(
        "--dry-run", action="store_true", help="Test without sending emails"
    )
    parser.add_argument("--verbose", action="store_true", help="Show detailed progress")
    args = parser.parse_args()

    sys.exit(main(args.dry_run, args.verbose))
