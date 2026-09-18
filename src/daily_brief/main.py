"""
Daily Brief Automation - Canvas & Coursemology Only

Fetches and generates daily brief from Canvas and Coursemology data.
"""

import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

import json

from daily_brief import DATA_DIR, ensure_directories, get_env_var, parse_canvas_courses
from daily_brief.canvas import fetch_canvas_data
from daily_brief.coursemology import (
    extract_assessments_data,
    extract_categories_data,
    fetch_coursemology_data,
)
from daily_brief.interfaces import AIService, EmailSender, StorageInterface
from daily_brief.services import FileStorage, GmailSender, GeminiAIService
from daily_brief.utils import SGT, parse_sgt_datetime, strip_html_preserve_urls


def _extract_deadlines(content: str, source_name: str) -> tuple[list[str], list[str]]:
    """Extract deadlines from markdown content for a given source.

    Handles format:
        - **Assignment Name**
          Due: ... | Points: ...

    Returns:
        Tuple of (urgent_items, upcoming_items)
    """
    urgent = []
    upcoming = []
    lines = content.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("- **") and "Due:" in line:
            assignment = line.split("Due:")[0].strip()
            assignment = assignment.replace("- **", "").split("**")[0]
            due_text = line.split("Due:")[1].strip()
            if "in 0 days" in line or "Today" in line:
                urgent.append(f"- **{source_name}** (Today): {assignment}")
            elif "in 1 days" in line:
                urgent.append(f"- **{source_name}** (Tomorrow): {assignment}")
            elif "in" in line:
                upcoming.append(f"- **{source_name}**: {assignment} ({due_text})")
        elif line.startswith("- **"):
            assignment = line.replace("- **", "").split("**")[0]
            if i + 1 < len(lines) and "Due:" in lines[i + 1]:
                due_line = lines[i + 1]
                due_text = (
                    due_line.split("Due:")[1].strip() if "Due:" in due_line else ""
                )
                if "in 0 days" in due_line or "Today" in due_line:
                    urgent.append(f"- **{source_name}** (Today): {assignment}")
                elif "in 1 days" in due_line:
                    urgent.append(f"- **{source_name}** (Tomorrow): {assignment}")
                elif "in" in due_line:
                    upcoming.append(f"- **{source_name}**: {assignment} ({due_text})")
        i += 1

    return urgent, upcoming


@dataclass
class OrchestrationServices:
    """Grouped dependencies for orchestration logic."""

    email_sender: EmailSender
    storage: StorageInterface
    ai_service: AIService


class BriefOrchestrator:
    """Orchestrates the daily brief generation and distribution flow."""

    def __init__(self, services: OrchestrationServices, dry_run: bool = False):
        self.services = services
        self.dry_run = dry_run

    def run(self, data_folder: Path) -> bool:
        try:
            print("\n[2/4] 📥 Extracting structured data from learning platforms...")
            fine_grained_data = self._fetch_fine_grained_data(data_folder)
            self._save_fine_grained_data(data_folder, fine_grained_data)
            
            print("\n[3/4] 🧠 Synthesizing insights with Gemini AI (Model: 3.1-flash-lite)...")
            print("   ⏳ Generating your daily brief (applying custom schemas)...")
            brief_content = self._synthesize_brief(fine_grained_data, data_folder)
            print("   ✓ AI synthesis complete")
            
            print("\n[4/4] ✉️  Formatting and dispatching daily brief via email...")
            return self._send_brief(brief_content, data_folder)
        except Exception as e:
            logging.error(f"Orchestration failed: {e}", exc_info=True)
            return False

    def _fetch_fine_grained_data(self, data_folder: Path) -> Dict[str, Any]:
        return fetch_fine_grained_data_impl(data_folder)

    def _save_fine_grained_data(self, data_folder: Path, data: Dict[str, Any]) -> None:
        self.services.storage.save_json(data_folder / "fine_grained.json", data)

    def _synthesize_brief(self, data: Dict[str, Any], data_folder: Path) -> str:
        # Extract current date from folder name (YYYY-MM-DD format)
        current_date_str = data_folder.name
        brief_md = self.services.ai_service.synthesize(data, current_date_str)
        
        # Save brief.md
        brief_path = data_folder / "brief.md"
        with open(brief_path, "w", encoding="utf-8") as f:
            f.write(brief_md)
            
        return brief_md

    def _send_brief(self, content: str, data_folder: Path) -> bool:
        subject = f"Daily Brief - {datetime.now(SGT).strftime('%Y-%m-%d')}"
        recipient = get_env_var("RECIPIENT_EMAIL")
        
        # Save email.html (for debugging and transparency)
        from daily_brief.utils import markdown_to_html
        
        html_content = markdown_to_html(content)
        html_path = data_folder / "email.html"
        
        # We can add some basic boilerplate so the standalone file renders nicely in a browser
        boilerplate_html = f"<html><body style='font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;'>{html_content}</body></html>"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(boilerplate_html)
            
        return self.services.email_sender.send(recipient, subject, content)


def generate_brief(data_folder: Path) -> str:
    """Generate daily brief from Canvas and Coursemology data."""
    today = datetime.now(SGT).strftime("%Y-%m-%d")
    lines = [f"# Daily Brief - {today}", ""]

    lines.append("## 🚨 Urgent Deadlines (Today/Tomorrow)")
    lines.append("")

    urgent_items: list[str] = []

    for course_file in sorted(data_folder.glob("canvas-*.md")):
        content = course_file.read_text()
        course_code = course_file.stem.replace("canvas-", "").upper()
        urgent_from_canvas, _ = _extract_deadlines(content, course_code)
        urgent_items.extend(urgent_from_canvas)

    coursemology_file = data_folder / "coursemology.md"
    if coursemology_file.exists():
        content = coursemology_file.read_text()
        urgent_from_cm, _ = _extract_deadlines(content, "Coursemology")
        urgent_items.extend(urgent_from_cm)

    if urgent_items:
        lines.extend(urgent_items[:10])
    else:
        lines.append("No urgent deadlines found.")

    lines.append("")

    lines.append("## 📚 Course Updates")
    lines.append("")

    updates = []

    for course_file in sorted(data_folder.glob("canvas-*.md")):
        content = course_file.read_text()
        course_code = course_file.stem.replace("canvas-", "").upper()

        if "## Announcements" in content:
            for line in content.split("\n"):
                if line.startswith("- **") and "Announcements" not in line:
                    title = line.replace("- **", "").split("**")[0]
                    updates.append(f"- **{course_code}**: {title}")
                    break

    if coursemology_file.exists():
        content = coursemology_file.read_text()
        if "## Announcements" in content:
            for line in content.split("\n"):
                if line.startswith("- **") and "Announcements" not in line:
                    title = line.replace("- **", "").split("**")[0]
                    updates.append(f"- **Coursemology**: {title}")
                    break

    if updates:
        lines.extend(updates[:10])
    else:
        lines.append("No new course updates.")

    lines.append("")

    lines.append("## 📅 Upcoming Deadlines (This Week)")
    lines.append("")

    upcoming: list[str] = []

    for course_file in sorted(data_folder.glob("canvas-*.md")):
        content = course_file.read_text()
        course_code = course_file.stem.replace("canvas-", "").upper()
        _, upcoming_from_canvas = _extract_deadlines(content, course_code)
        upcoming.extend(upcoming_from_canvas)

    if coursemology_file.exists():
        content = coursemology_file.read_text()
        _, upcoming_from_cm = _extract_deadlines(content, "Coursemology")
        upcoming.extend(upcoming_from_cm)

    if upcoming:
        lines.extend(upcoming[:20])
    else:
        lines.append("No upcoming deadlines.")

    lines.append("")

    lines.append("---")
    lines.append(f"*Generated on {datetime.now(SGT).strftime('%Y-%m-%d %H:%M:%S')}*")

    return "\n".join(lines)


def generate_raw_data(data_folder: Path) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "generated_at": datetime.now(SGT).isoformat(),
        "canvas": {},
        "coursemology": "",
    }

    fine_grained_file = data_folder / "fine_grained.json"
    if fine_grained_file.exists():
        with open(fine_grained_file, "r") as f:
            fine_grained_data = json.load(f)
        data["canvas"] = fine_grained_data.get("canvas", {})
    else:
        for course_file in sorted(data_folder.glob("canvas-*.md")):
            content = course_file.read_text()
            course_code = course_file.stem.replace("canvas-", "").upper()
            data["canvas"][course_code] = content

    if fine_grained_file.exists():
        data["coursemology"] = fine_grained_data.get("coursemology", "")
    else:
        coursemology_file = data_folder / "coursemology.md"
        if coursemology_file.exists():
            data["coursemology"] = coursemology_file.read_text()

    return data


def fetch_fine_grained_data() -> Dict[str, Any]:
    from daily_brief.canvas import (
        CanvasClient,
        extract_announcements_data,
        extract_assignments_data,
        extract_quizzes_data,
    )

    data: Dict[str, Any] = {"canvas": {}, "coursemology": {}}

    try:
        canvas_token = get_env_var("CANVAS_API_TOKEN")
        canvas_courses_str = get_env_var("CANVAS_COURSES", default="")
        canvas_courses = (
            parse_canvas_courses(canvas_courses_str) if canvas_courses_str else {}
        )

        client = CanvasClient(get_env_var("CANVAS_BASE_URL"), canvas_token)

        for course_code, course_id in canvas_courses.items():
            course_data: Dict[str, Any] = {}

            announcements = client.get_announcements(course_id)
            if isinstance(announcements, dict):
                announcements = announcements.get("announcements", [])
            course_data["announcements"] = extract_announcements_data(announcements)

            assignments = client.get_assignments(
                course_id, ["assignment_overrides", "submission"]
            )
            if isinstance(assignments, dict):
                assignments = assignments.get("assignments", [])
            course_data["assignments"] = extract_assignments_data(assignments)

            quizzes = client.get_quizzes(course_id)
            if isinstance(quizzes, dict):
                quizzes = quizzes.get("quizzes", [])
            course_data["quizzes"] = extract_quizzes_data(quizzes)

            data["canvas"][course_code] = course_data
    except Exception as e:
        print(f"   ✗ Failed to fetch Canvas fine-grained data: {e}")

    try:
        from coursemology_py import CoursemologyClient

        client = CoursemologyClient(host="https://coursemology.org")
        client.login(
            get_env_var("COURSEMOLOGY_USERNAME"), get_env_var("COURSEMOLOGY_PASSWORD")
        )

        course_id_str = get_env_var("COURSEMOLOGY_COURSE_ID", default="0")
        course_id = int(course_id_str) if course_id_str.isdigit() else 0

        courses = client.courses.index()
        if courses.courses:
            if course_id == 0:
                course_id = courses.courses[0].id
            course_api = client.course(course_id)

            announcements = course_api.announcements.index()
            print(
                f"DEBUG fetch_fine_grained_data: announcements type = {type(announcements)}, has_announcements = {hasattr(announcements, 'announcements')}"
            )
            if hasattr(announcements, "announcements"):
                print(
                    f"DEBUG: announcements.announcements type = {type(announcements.announcements)}"
                )
                print(
                    f"DEBUG: First item type = {type(announcements.announcements[0]) if announcements.announcements else 'empty'}"
                )
            data["coursemology"]["announcements"] = extract_announcements_data(
                announcements.announcements
                if hasattr(announcements, "announcements")
                else announcements
            )
    except Exception as e:
        print(f"   ✗ Failed to fetch Coursemology fine-grained data: {e}")
        print(f"   Debug: course_id used = {course_id}")

    return data


def fetch_fine_grained_data_impl(data_folder: Path) -> Dict[str, Any]:
    from daily_brief.canvas import (
        CanvasClient,
        extract_announcements_data,
        extract_assignments_data,
        extract_quizzes_data,
    )
    from daily_brief.coursemology import (
        extract_announcements_data as cm_extract_announcements,
    )

    data: Dict[str, Any] = {"canvas": {}, "coursemology": {}}

    try:
        print("   --- Canvas ---")
        canvas_token = get_env_var("CANVAS_API_TOKEN")
        canvas_courses_str = get_env_var("CANVAS_COURSES", default="")
        canvas_courses = (
            parse_canvas_courses(canvas_courses_str) if canvas_courses_str else {}
        )

        client = CanvasClient(get_env_var("CANVAS_BASE_URL"), canvas_token)

        for course_code, course_id in canvas_courses.items():
            course_data: Dict[str, Any] = {}

            announcements = client.get_announcements(course_id)
            if isinstance(announcements, dict):
                announcements = announcements.get("announcements", [])
            course_data["announcements"] = extract_announcements_data(announcements)

            assignments = client.get_assignments(
                course_id, ["assignment_overrides", "submission"]
            )
            if isinstance(assignments, dict):
                assignments = assignments.get("assignments", [])
            course_data["assignments"] = extract_assignments_data(assignments)

            quizzes = client.get_quizzes(course_id)
            if isinstance(quizzes, dict):
                quizzes = quizzes.get("quizzes", [])
            course_data["quizzes"] = extract_quizzes_data(quizzes)

            data["canvas"][course_code] = course_data
            print(f"   ✓ [{course_code}] Canvas data extracted")
    except Exception as e:
        print(f"   ✗ Failed to fetch Canvas fine-grained data: {e}")

    try:
        print("   --- Coursemology ---")
        from coursemology_py import CoursemologyClient
        import contextlib
        import io

        print("   ⏳ Authenticating with Coursemology (this may take a few seconds)...")
        client = CoursemologyClient(host="https://coursemology.org")
        
        # Suppress the raw "Logging in... Login successful." prints from the library
        with contextlib.redirect_stdout(io.StringIO()):
            client.login(
                get_env_var("COURSEMOLOGY_USERNAME"), get_env_var("COURSEMOLOGY_PASSWORD")
            )
        print("   🔓 Coursemology authentication successful")

        course_id_str = get_env_var("COURSEMOLOGY_COURSE_ID", default="0")
        course_id = int(course_id_str) if course_id_str.isdigit() else 0

        course_code = f"Course {course_id}"
        if course_id != 0:
            # Bypass coursemology_py Pydantic validation errors by doing a raw GET
            url = f"{client.courses._base_url}/courses/{course_id}"
            try:
                resp = client.courses._session.get(url, params={"format": "json"})
                if resp.status_code == 200:
                    raw_course_data = resp.json()
                    title = raw_course_data.get("course", {}).get("title", "")
                    if title:
                        # e.g., "CS2109S - Introduction to AI..." -> "CS2109S"
                        course_code = title.split()[0]
            except Exception:
                pass
            
            course_api = client.course(course_id)

            # Fetch announcements
            announcements = course_api.announcements.index()
            data["coursemology"]["announcements"] = cm_extract_announcements(
                announcements
            )

            # Fetch assessments
            assessments = course_api.assessment.assessments.index()
            data["coursemology"]["assessments"] = extract_assessments_data(
                assessments.assessments
            )

            # Fetch Lecture Trainings (Category 4811)
            try:
                lecture_trainings = course_api.assessment.assessments.index(
                    category_id=4811
                )
                data["coursemology"]["lecture_trainings"] = extract_assessments_data(
                    lecture_trainings.assessments
                )
            except Exception as e:
                print(f"   ✗ Failed to fetch Lecture Trainings: {e}")
                data["coursemology"]["lecture_trainings"] = []

            # Fetch Surveys (Direct API Call)
            try:
                base_url = course_api.assessment._base_url
                url = f"{base_url.rstrip('/')}/courses/{course_id}/surveys"
                raw_resp = course_api.assessment._session.get(
                    url, params={"format": "json"}
                )
                if raw_resp.status_code == 200:
                    raw_data = raw_resp.json()

                    filtered_surveys = []
                    for survey in raw_data.get("surveys", []):
                        if survey.get("response") is not None:
                            continue

                        end_at = survey.get("end_at")
                        if end_at:
                            due_dt = parse_sgt_datetime(end_at)
                            if due_dt:
                                days_old = (
                                    datetime.now(SGT).date() - due_dt.date()
                                ).days
                                if days_old > 7:
                                    continue

                        desc = survey.get("description", "")
                        if desc:
                            survey["description"] = strip_html_preserve_urls(desc)
                        filtered_surveys.append(survey)

                    data["coursemology"]["surveys"] = filtered_surveys
                else:
                    data["coursemology"]["surveys"] = []
            except Exception as e:
                print(f"   ✗ Failed to fetch Surveys: {e}")
                data["coursemology"]["surveys"] = []

            # Fetch submissions - handle Pydantic validation issues
            try:
                submissions = course_api.submissions.index()
                # Extract raw data to avoid model validation errors
                if hasattr(submissions, "model_dump"):
                    raw = submissions.model_dump(by_alias=True, exclude_none=True)
                elif isinstance(submissions, dict):
                    raw = submissions
                else:
                    raw = {}
                data["coursemology"]["submissions"] = raw.get("submissions", [])
            except Exception:
                # If validation fails, try to get raw data from the response
                try:
                    # Make a raw HTTP request to bypass validation
                    base_url = course_api.submissions._base_url
                    prefix = course_api.submissions._url_prefix
                    url = f"{base_url.rstrip('/')}/{prefix.lstrip('/')}"
                    raw_resp = course_api.submissions._session.get(
                        url, params={"format": "json"}
                    )
                    if raw_resp.status_code == 200:
                        raw_data = raw_resp.json()
                        data["coursemology"]["submissions"] = raw_data.get(
                            "submissions", []
                        )
                    else:
                        data["coursemology"]["submissions"] = []
                except Exception:
                    data["coursemology"]["submissions"] = []

            # Fetch categories (top-level)
            try:
                categories = course_api.assessment.categories.index()
                data["coursemology"]["categories"] = extract_categories_data(
                    categories.categories
                )
            except Exception:
                data["coursemology"]["categories"] = []
                
            print(f"   ✓ [{course_code}] Coursemology data extracted")
    except Exception as e:
        import traceback

        print(f"   ✗ Failed to fetch Coursemology fine-grained data: {e}")
        print(f"   Debug: course_id used = {course_id}")
        traceback.print_exc()

    return data


def save_fine_grained_data(data_folder: Path, data: Dict[str, Any]) -> None:
    filepath = data_folder / "fine_grained.json"
    with open(filepath, "w") as f:
        import json

        json.dump(data, f, indent=2, default=str)
    print("   ✓ Fine-grained data saved to fine_grained.json")


def main(dry_run: bool = False, verbose: bool = False) -> int:
    print(f"\n{'=' * 60}")
    print(f"Daily Brief Automation - {datetime.now(SGT).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}\n")

    print("[1/4] 📂 Setting up workspace...")
    ensure_directories()
    
    # Cleanup old data folders to prevent bloat
    import shutil
    retention_days = 3
    cutoff_date = (datetime.now(SGT) - timedelta(days=retention_days)).date()
    
    for item in DATA_DIR.iterdir():
        if item.is_dir() and not item.is_symlink():
            try:
                folder_date = datetime.strptime(item.name, "%Y-%m-%d").date()
                if folder_date < cutoff_date:
                    shutil.rmtree(item)
                    print(f"   Removed old data folder: {item.name}")
            except ValueError:
                pass # Not a YYYY-MM-DD folder

    today = datetime.now(SGT).strftime("%Y-%m-%d")
    date_folder = DATA_DIR / today
    date_folder.mkdir(exist_ok=True)
    latest = DATA_DIR / "latest"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(today)
    print(f"   ✓ Workspace ready at {date_folder}\n")

    services = OrchestrationServices(
        email_sender=GmailSender(),
        storage=FileStorage(),
        ai_service=GeminiAIService(),
    )

    orchestrator = BriefOrchestrator(services, dry_run=dry_run)
    success = orchestrator.run(date_folder)

    if success:
        print(f"\n✨ Daily brief successfully delivered to: {get_env_var('RECIPIENT_EMAIL')}\n")
        return 0
    else:
        print("\n❌ Daily brief automation failed!\n")
        return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Daily Brief Automation")
    parser.add_argument("--dry-run", action="store_true", help="Don't send email")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    sys.exit(main(dry_run=args.dry_run, verbose=args.verbose))
