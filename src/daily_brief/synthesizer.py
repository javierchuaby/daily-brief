#!/usr/bin/env python3
"""
OpenCode AI Synthesizer for Daily Brief

Reads raw data from fine_grained.json and uses OpenCode's AI to synthesize
a comprehensive daily brief, then emails it to the user.
"""

import datetime
import json
import sys
from pathlib import Path


def load_fine_grained_data(data_folder: Path) -> dict:
    """Load fine-grained data from JSON file."""
    filepath = data_folder / "fine_grained.json"
    if not filepath.exists():
        raise FileNotFoundError(f"Fine-grained data not found: {filepath}")

    with open(filepath, "r") as f:
        return json.load(f)


def synthesize_brief_with_opencode(
    raw_data: dict, current_date_str: str, data_folder: Path
) -> str:
    """
    Use OpenCode's AI to synthesize the daily brief with pre-computed date anchors.

    Args:
        raw_data: Dictionary containing Canvas and Coursemology data
        current_date_str: Current date in YYYY-MM-DD format for relative date resolution
        data_folder: Path to the data folder (used for working directory)

    Returns:
        Generated brief as a markdown string
    """
    # Pre-calculate calendar anchors in Python
    ref_date = datetime.date.fromisoformat(current_date_str)
    day_name = ref_date.strftime("%A")
    tomorrow = ref_date + datetime.timedelta(days=1)
    end_of_week = ref_date + datetime.timedelta(days=(6 - ref_date.weekday()))
    past_cutoff = ref_date - datetime.timedelta(days=7)

    # Embed the raw data directly in the prompt (no file path references)
    data_json = json.dumps(raw_data, indent=2, default=str)

    # Rigid system template with strict output formatting
    system_prompt = f"""You are a precise data extraction assistant. Your task is to synthesize a daily brief from course data.

TEMPORAL ANCHORS:
- Reference Date (Today): {ref_date.isoformat()} ({day_name})
- Tomorrow: {tomorrow.isoformat()}
- End of Current Week (Sunday): {end_of_week.isoformat()}
- Recent Updates Cutoff: {past_cutoff.isoformat()}

CLASSIFICATION RULES:
1. URGENT:
   - Assignments or tasks due on Today ({ref_date.isoformat()}) or Tomorrow ({tomorrow.isoformat()}).
2. IMPORTANT:
   - Actionable items, surveys, or assignments due between {ref_date.isoformat()} and {end_of_week.isoformat()}.
3. INFO - Recent Updates & Announcements:
   - Include announcements or status changes posted on or after {past_cutoff.isoformat()}.
   - Deduplication: Do not repeat items already listed under URGENT or IMPORTANT.
   - Event Expiry: Discard announcements regarding lectures, meetings, or consultations that concluded prior to {ref_date.isoformat()}.
   - Consolidation: If multiple announcements refer to the same assignment or topic, combine them into one consolidated bullet point.
   - Summarise each entry into a single actionable sentence.
4. INFO - Later Deadlines:
   - Assignments or tasks due strictly after {end_of_week.isoformat()}.
   - Sort in chronological order.

OUTPUT FORMAT (STRICT):
- Start directly with: # Daily Brief - {ref_date.isoformat()}
- Section 1: ## URGENT (Today/Tomorrow)
  - Format: - [Source] Title (Due: YYYY-MM-DD): Key action or requirement
- Section 2: ## IMPORTANT (This Week)
  - Format: - [Source] Title (Due: YYYY-MM-DD): Key action or requirement
- Section 3: ## INFO (For Awareness)
  ### Recent Updates & Announcements
  - Format: - [Source] Title (Posted: YYYY-MM-DD): 1-sentence action item or takeaway
  ### Later Deadlines
  - Format: - [Source] Title (Due: YYYY-MM-DD)
- If any section or subsection has no qualifying items, output: - None
- NO conversational language, NO greetings, NO sign-offs.

DATA (embedded, do not reference file paths):
{data_json}

OUTPUT:"""

    # Write debug prompt before invoking OpenCode
    debug_prompt_path = data_folder / "debug_prompt.txt"
    debug_prompt_path.write_text(system_prompt, encoding="utf-8")

    try:
        import subprocess

        result = subprocess.run(
            ["opencode", "run", "-m", "soclaas/qwen3.8:27b", system_prompt],
            capture_output=True,
            text=True,
            cwd=str(data_folder),
        )

        if result.returncode == 0:
            output = result.stdout.strip()
            debug_output_path = data_folder / "debug_raw_output.md"
            debug_output_path.write_text(output, encoding="utf-8")
            return output
        else:
            print(f"OpenCode failed (code {result.returncode}): {result.stderr}")
            raise RuntimeError("OpenCode AI synthesis failed")
    except FileNotFoundError:
        print("OpenCode not found. Please install opencode CLI.")
        raise


def main() -> int:
    """Main entry point for synthesis."""
    print(f"Executing script from: {Path(__file__).resolve()}")
    print("Synthesizing daily brief with OpenCode AI...")

    # Get data folder
    project_root = Path.cwd()
    data_dir = project_root / "data"

    # Find today's data folder
    today = None
    for folder in sorted(data_dir.glob("20*")):
        today = folder

    if not today:
        print("No data folder found. Run the automation first.")
        return 1

    print(f"Using data folder: {today}")

    # Extract current_date_str from folder name (YYYY-MM-DD format)
    current_date_str = today.name

    # Load data
    raw_data = load_fine_grained_data(today)

    # Synthesize with reference date
    brief = synthesize_brief_with_opencode(raw_data, current_date_str, today)

    # Send email using the orchestrator pattern
    from daily_brief import get_env_var
    from daily_brief.services import GmailSender

    subject = f"Daily Brief - {current_date_str}"
    sender = GmailSender()
    sender.send(get_env_var("RECIPIENT_EMAIL"), subject, brief)

    print("✓ Daily brief synthesized and sent!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
