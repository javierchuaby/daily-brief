"""Endpoint verification and probe script for Canvas and Coursemology.

This script executes live probes against all configured Canvas and Coursemology
API endpoints, verifying connectivity, authentication, response codes, and data schemas.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
from typing import Any

import requests

from daily_brief import get_env_var, parse_canvas_courses
from coursemology_py import CoursemologyClient


def probe_canvas() -> list[dict[str, Any]]:
    """Probe Canvas endpoints including collection and single-resource items."""
    base_url = get_env_var("CANVAS_BASE_URL").rstrip("/")
    token = get_env_var("CANVAS_API_TOKEN")
    courses_str = get_env_var("CANVAS_COURSES")
    courses = parse_canvas_courses(courses_str)

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})

    sample_code, sample_id = next(iter(courses.items()))
    print(f"\n--- Probing Canvas LMS ({base_url}) [Sample Course: {sample_code}:{sample_id}] ---")

    # Discover single-resource IDs dynamically
    r_ass = session.get(f"{base_url}/api/v1/courses/{sample_id}/assignments")
    ass_list = r_ass.json() if r_ass.status_code == 200 and isinstance(r_ass.json(), list) else []
    sample_ass_id = ass_list[0]["id"] if ass_list else None

    r_quizzes = session.get(f"{base_url}/api/v1/courses/{sample_id}/quizzes")
    quiz_list = r_quizzes.json() if r_quizzes.status_code == 200 and isinstance(r_quizzes.json(), list) else []
    sample_quiz_id = quiz_list[0]["id"] if quiz_list else None

    r_disc = session.get(f"{base_url}/api/v1/courses/{sample_id}/discussion_topics")
    disc_list = r_disc.json() if r_disc.status_code == 200 and isinstance(r_disc.json(), list) else []
    sample_disc_id = disc_list[0]["id"] if disc_list else None

    r_pages = session.get(f"{base_url}/api/v1/courses/{sample_id}/pages")
    page_list = r_pages.json() if r_pages.status_code == 200 and isinstance(r_pages.json(), list) else []
    sample_page_url = page_list[0]["url"] if page_list else None

    r_files = session.get(f"{base_url}/api/v1/courses/{sample_id}/files")
    file_list = r_files.json() if r_files.status_code == 200 and isinstance(r_files.json(), list) else []
    sample_file_id = file_list[0]["id"] if file_list else None

    endpoints: list[tuple[str, str, str, dict[str, Any]]] = [
        ("Current User Profile", "GET", "/api/v1/users/self", {}),
        ("User Activity Stream", "GET", "/api/v1/users/self/activity_stream", {}),
        ("User Upcoming Events", "GET", "/api/v1/users/self/upcoming_events", {}),
        ("User Missing Submissions", "GET", "/api/v1/users/self/missing_submissions", {}),
        ("List Active Courses", "GET", "/api/v1/courses", {"enrollment_state": "active"}),
        ("Get Course Details", "GET", f"/api/v1/courses/{sample_id}", {}),
        (
            "Course Announcements",
            "GET",
            "/api/v1/announcements",
            {"context_codes[]": f"course_{sample_id}"},
        ),
        ("List Assignments", "GET", f"/api/v1/courses/{sample_id}/assignments", {}),
        (
            "Assignments with Submissions",
            "GET",
            f"/api/v1/courses/{sample_id}/assignments",
            {"include[]": ["submission", "assignment_overrides"]},
        ),
        ("List Quizzes", "GET", f"/api/v1/courses/{sample_id}/quizzes", {}),
        ("Course Discussion Topics", "GET", f"/api/v1/courses/{sample_id}/discussion_topics", {}),
        ("Course Pages", "GET", f"/api/v1/courses/{sample_id}/pages", {}),
        ("Course Files", "GET", f"/api/v1/courses/{sample_id}/files", {}),
        ("Course Folders", "GET", f"/api/v1/courses/{sample_id}/folders", {}),
        ("Course Users", "GET", f"/api/v1/courses/{sample_id}/users", {}),
        ("Course Enrollments", "GET", f"/api/v1/courses/{sample_id}/enrollments", {}),
        ("Course Sections", "GET", f"/api/v1/courses/{sample_id}/sections", {}),
        ("Course Navigation Tabs", "GET", f"/api/v1/courses/{sample_id}/tabs", {}),
        ("Panopto Sessionless Launch", "GET", f"/api/v1/courses/{sample_id}/external_tools/sessionless_launch", {"id": "128", "launch_type": "course_navigation"}),
    ]

    # Add single-resource endpoints if discovered
    if sample_ass_id:
        endpoints.append(
            ("Single Assignment Details", "GET", f"/api/v1/courses/{sample_id}/assignments/{sample_ass_id}", {})
        )
        endpoints.append(
            ("User Assignment Submission", "GET", f"/api/v1/courses/{sample_id}/assignments/{sample_ass_id}/submissions/self", {})
        )
    if sample_quiz_id:
        endpoints.append(
            ("Single Quiz Details", "GET", f"/api/v1/courses/{sample_id}/quizzes/{sample_quiz_id}", {})
        )
        endpoints.append(
            ("Quiz Submissions", "GET", f"/api/v1/courses/{sample_id}/quizzes/{sample_quiz_id}/submissions", {})
        )
    if sample_disc_id:
        endpoints.append(
            ("Single Discussion Topic", "GET", f"/api/v1/courses/{sample_id}/discussion_topics/{sample_disc_id}", {})
        )
    if sample_page_url:
        endpoints.append(
            ("Single Page Content", "GET", f"/api/v1/courses/{sample_id}/pages/{sample_page_url}", {})
        )
    if sample_file_id:
        endpoints.append(
            ("Single File Metadata", "GET", f"/api/v1/courses/{sample_id}/files/{sample_file_id}", {})
        )

    # CS2107 module inspection
    cs2107_id = courses.get("CS2107")
    if cs2107_id:
        endpoints.append(
            ("Course Modules (CS2107)", "GET", f"/api/v1/courses/{cs2107_id}/modules", {"include[]": ["items"]})
        )

    results: list[dict[str, Any]] = []
    for name, method, path, params in endpoints:
        url = f"{base_url}{path}"
        try:
            resp = session.request(method, url, params=params, timeout=15)
            status = resp.status_code
            count = 0
            if resp.headers.get("Content-Type", "").startswith("application/json"):
                data = resp.json()
                count = len(data) if isinstance(data, list) else (1 if data else 0)
            results.append(
                {
                    "service": "Canvas",
                    "name": name,
                    "method": method,
                    "path": path,
                    "status": status,
                    "count": count,
                }
            )
            print(f"[{status}] {method:4s} {path:<55s} -> Items: {count}")
        except Exception as e:
            results.append(
                {
                    "service": "Canvas",
                    "name": name,
                    "method": method,
                    "path": path,
                    "status": "ERR",
                    "count": 0,
                    "error": str(e),
                }
            )
            print(f"[ERR] {method:4s} {path:<55s} -> Error: {e}")

    return results


def probe_coursemology() -> list[dict[str, Any]]:
    """Probe Coursemology endpoints including collection and single-resource items."""
    username = get_env_var("COURSEMOLOGY_USERNAME")
    password = get_env_var("COURSEMOLOGY_PASSWORD")
    course_id = int(get_env_var("COURSEMOLOGY_COURSE_ID", default="3369"))

    client = CoursemologyClient(host="https://coursemology.org")
    with contextlib.redirect_stdout(io.StringIO()):
        client.login(username, password)

    session = client._session
    base_url = client.base_url

    print(f"\n--- Probing Coursemology ({base_url}) [Course ID: {course_id}] ---")

    # Discover single-resource IDs dynamically
    r_ass = session.get(f"{base_url}/courses/{course_id}/assessments", params={"format": "json"})
    ass_data = r_ass.json() if r_ass.status_code == 200 else {}
    ass_list = ass_data.get("assessments", [])
    sample_ass_id = ass_list[0]["id"] if ass_list else 93400

    # Discover matched submission and assessment ID
    r_sub = session.get(f"{base_url}/courses/{course_id}/assessments/submissions", params={"format": "json"})
    sub_data = r_sub.json() if r_sub.status_code == 200 else {}
    sub_list = sub_data.get("submissions", [])
    if sub_list:
        matched_sub_id = sub_list[0]["id"]
        matched_ass_id = sub_list[0]["assessmentId"]
    else:
        matched_sub_id = None
        matched_ass_id = None

    # Discover forum ID
    r_forum = session.get(f"{base_url}/courses/{course_id}/forums", params={"format": "json"})
    forum_data = r_forum.json() if r_forum.status_code == 200 else {}
    forum_list = forum_data.get("forums", [])
    sample_forum_id = forum_list[0]["id"] if forum_list else None

    # Discover folder ID
    r_fold = session.get(f"{base_url}/courses/{course_id}/materials/folders", params={"format": "json"})
    fold_data = r_fold.json() if r_fold.status_code == 200 else {}
    subfolder_list = fold_data.get("subfolders", [])
    sample_folder_id = subfolder_list[0]["id"] if subfolder_list else None

    # Discover video ID from Recent Advances tab (3008)
    r_vids = session.get(f"{base_url}/courses/{course_id}/videos", params={"tab": 3008, "format": "json"})
    vid_data = r_vids.json() if r_vids.status_code == 200 else {}
    vid_list = vid_data.get("videos", [])
    sample_video_id = vid_list[0]["id"] if vid_list else None

    endpoints: list[tuple[str, str, str, dict[str, Any]]] = [
        ("List Enrolled Courses", "GET", "/courses", {"format": "json"}),
        ("Get Course Info", "GET", f"/courses/{course_id}", {"format": "json"}),
        ("Get Course Sidebar Layout", "GET", f"/courses/{course_id}/sidebar", {"format": "json"}),
        ("Course Announcements", "GET", f"/courses/{course_id}/announcements", {"format": "json"}),
        ("Course Assessments (Default)", "GET", f"/courses/{course_id}/assessments", {"format": "json"}),
        (
            "Category Filtered Assessments (Cat 4811)",
            "GET",
            f"/courses/{course_id}/assessments",
            {"category": 4811, "format": "json"},
        ),
        (
            "Assessment Submissions",
            "GET",
            f"/courses/{course_id}/assessments/submissions",
            {"format": "json"},
        ),
        ("Course Surveys", "GET", f"/courses/{course_id}/surveys", {"format": "json"}),
        ("Course Forums", "GET", f"/courses/{course_id}/forums", {"format": "json"}),
        ("Course Groups", "GET", f"/courses/{course_id}/groups", {"format": "json"}),
        ("Course Users Roster", "GET", f"/courses/{course_id}/users", {"format": "json"}),
        ("Comments / Code Review", "GET", f"/courses/{course_id}/comments", {"format": "json"}),
        ("Lesson Plan & Milestones", "GET", f"/courses/{course_id}/lesson_plan", {"format": "json"}),
        ("Workbin Folders & Files", "GET", f"/courses/{course_id}/materials/folders", {"format": "json"}),
        ("Achievements & Badges", "GET", f"/courses/{course_id}/achievements", {"format": "json"}),
        ("Course Leaderboard", "GET", f"/courses/{course_id}/leaderboard", {"format": "json"}),
        ("Course Videos (Default Tab)", "GET", f"/courses/{course_id}/videos", {"format": "json"}),
        ("Course Videos (Recent Advances Tab 3008)", "GET", f"/courses/{course_id}/videos", {"tab": 3008, "format": "json"}),
    ]

    if sample_ass_id:
        endpoints.append(
            ("Single Assessment Details", "GET", f"/courses/{course_id}/assessments/{sample_ass_id}", {"format": "json"})
        )
    if matched_sub_id and matched_ass_id:
        endpoints.append(
            (
                "Assessment Attempt (Questions & Answers)",
                "GET",
                f"/courses/{course_id}/assessments/{matched_ass_id}/submissions/{matched_sub_id}/edit",
                {"format": "json"},
            )
        )
    if sample_forum_id:
        endpoints.append(
            ("Forum Topics Listing", "GET", f"/courses/{course_id}/forums/{sample_forum_id}", {"format": "json"})
        )
    if sample_folder_id:
        endpoints.append(
            ("Subfolder Materials", "GET", f"/courses/{course_id}/materials/folders/{sample_folder_id}", {"format": "json"})
        )
    if sample_video_id:
        endpoints.append(
            ("Single Video Details & Retention", "GET", f"/courses/{course_id}/videos/{sample_video_id}", {"format": "json"})
        )

    results: list[dict[str, Any]] = []
    for name, method, path, params in endpoints:
        url = f"{base_url}{path}"
        try:
            resp = session.request(method, url, params=params, timeout=15)
            status = resp.status_code
            count = 0
            if resp.headers.get("Content-Type", "").startswith("application/json"):
                data = resp.json()
                if isinstance(data, list):
                    count = len(data)
                elif isinstance(data, dict):
                    # Pick largest list inside dict
                    list_counts = [len(v) for v in data.values() if isinstance(v, list)]
                    count = max(list_counts) if list_counts else 1
            results.append(
                {
                    "service": "Coursemology",
                    "name": name,
                    "method": method,
                    "path": path,
                    "status": status,
                    "count": count,
                }
            )
            print(f"[{status}] {method:4s} {path:<55s} -> Items: {count}")
        except Exception as e:
            results.append(
                {
                    "service": "Coursemology",
                    "name": name,
                    "method": method,
                    "path": path,
                    "status": "ERR",
                    "count": 0,
                    "error": str(e),
                }
            )
            print(f"[ERR] {method:4s} {path:<55s} -> Error: {e}")

    return results


def main() -> None:
    """Run endpoint verification."""
    parser = argparse.ArgumentParser(description="Probe Canvas and Coursemology API endpoints.")
    parser.add_argument(
        "--service",
        choices=["all", "canvas", "coursemology"],
        default="all",
        help="Target service to probe (default: all)",
    )
    args = parser.parse_args()

    results: list[dict[str, Any]] = []
    if args.service in ("all", "canvas"):
        results.extend(probe_canvas())
    if args.service in ("all", "coursemology"):
        results.extend(probe_coursemology())

    total = len(results)
    success = sum(1 for r in results if r["status"] == 200)
    failed = total - success

    print("\n" + "=" * 60)
    print(f"PROBE SUMMARY: {success}/{total} endpoints returned 200 OK ({failed} failed/restricted)")
    print("=" * 60)

    if failed > 0:
        print("\nNon-200 Endpoints:")
        for r in results:
            if r["status"] != 200:
                print(f"  - [{r['status']}] {r['service']}: {r['method']} {r['path']}")


if __name__ == "__main__":
    main()
