# Daily Brief API Integrations & Documentation

This directory contains complete, verified technical documentation for the external learning management system (LMS) APIs integrated into `daily-brief`:
- **Canvas LMS API Reference**: [canvas.md](file:///Users/javier/Projects/daily-brief/docs/api/canvas.md)
- **Coursemology API & SDK Reference**: [coursemology.md](file:///Users/javier/Projects/daily-brief/docs/api/coursemology.md)

---

## Probing & Verification Methodology

Every single endpoint documented here was personally probed and verified against live upstream servers:
- **Canvas LMS**: Probed against National University of Singapore Canvas (`https://canvas.nus.edu.sg`) with live bearer authentication and course IDs.
- **Coursemology**: Probed against `https://coursemology.org` (CS2109S course ID `3369`) using live session authentication, exploring both raw JSON Rails responses and `coursemology-py` SDK calls.

### Running Live Probes

You can re-probe and verify all endpoints at any time using the bundled verification script:

```bash
# Probe all endpoints across both services (Canvas + Coursemology)
python scripts/probe_endpoints.py

# Probe only Canvas LMS
python scripts/probe_endpoints.py --service canvas

# Probe only Coursemology
python scripts/probe_endpoints.py --service coursemology
```

### Verification Summary

```text
============================================================
PROBE SUMMARY: 50/50 endpoints returned 200 OK (0 failed/restricted)
============================================================
```

- **Canvas LMS (27 Endpoints Verified 200 OK)**:
  - User identity, personal profile, activity stream, activity stream summary, upcoming events, missing submissions, dashboard colors
  - Active course listing, single course details, front page
  - Announcements
  - Course assignments, single assignment instructions, assignments with submission details & overrides, batch course submissions (`/students/submissions`)
  - Assignment groups (gradebook weighting categories)
  - Quizzes index, single quiz details, quiz submissions
  - Course modules, module items
  - Discussion topics index, single topic details, full threaded topic view (`/view`)
  - Pages, files, folders, course roster, and sections
  - Course navigation tabs (`/tabs`), Panopto LTI sessionless launch (`/external_tools/sessionless_launch?id=128`)
- **Coursemology (23 Endpoints Verified 200 OK)**:
  - User profile, user courses index, single course details, sidebar navigation layout
  - Announcements
  - Assessments (default, category-filtered, tab-filtered), single assessment metadata
  - Submissions index (across all assessments)
  - Student attempt inspection and editing route (`/edit` with questions, answers, annotations, feedback)
  - Surveys, single survey details
  - Forums index, forum topics list
  - Groups, course roster (427 users), comments / code review, lesson plan & milestones
  - Workbin root folders, subfolder materials, direct file download streaming
  - Gamification achievements / badges, EXP and badge count leaderboards
  - Course video tabs, tab-filtered video list, and single video metadata with second-by-second watch frequency heatmap

---

## Documentation Index

| Documentation Guide | Target Service | Key Topics Covered |
| :--- | :--- | :--- |
| [Canvas LMS API](file:///Users/javier/Projects/daily-brief/docs/api/canvas.md) | Canvas (`https://canvas.nus.edu.sg`) | Bearer Auth, Link header pagination, Rate limits (`X-Request-Cost`), ISO-8601 to SGT conversion, 27 verified endpoints, Quizzes 404 handling, module completion quirks, batch submission optimization, 3-step file upload workflow, standalone reference client, cURL cheatsheet. |
| [Coursemology API](file:///Users/javier/Projects/daily-brief/docs/api/coursemology.md) | Coursemology (`https://coursemology.org`) | Session Cookie Auth, CSRF token extraction, `?format=json` requirement, Student vs Staff RBAC matrix, `coursemology-py` Pydantic model drifts & monkey-patches, 23 verified endpoints, attempt inspection & autograding, workbin binary download streaming, standalone reference client, cURL cheatsheet. |

---

## Architectural Comparison Matrix

| Dimension | Canvas LMS | Coursemology |
| :--- | :--- | :--- |
| **Backend Framework** | Ruby on Rails (API-first service mesh) | Ruby on Rails (Monolithic SPA backend) |
| **Authentication** | Bearer Token (`Authorization: Bearer <token>`) | Session Cookie (`_coursemology2_session`) + CSRF Token (`X-CSRF-Token`) |
| **API Format Negotiation** | Standard JSON via URL prefix (`/api/v1/*`) | **Mandatory query param**: `?format=json` (or returns HTML SPA shell) |
| **Pagination Strategy** | RFC 5988 `Link` headers with `rel="next"` & `per_page=100` | Unpaginated full dumps or tab-filtered category subsets (`?category=X&tab=Y`) |
| **Rate Limiting** | Leaky bucket via response headers (`X-Rate-Limit-Remaining`, `X-Request-Cost`) | Standard Rails / Cloudflare application rate limiting |
| **Date & Time Formats** | Strict ISO-8601 UTC with `Z` suffix (`2026-09-19T11:50:29Z`) | ISO-8601 strings or nested objects (`{"isFixed": bool, "effectiveTime": "..."}`) |
| **Data Types Quirk** | Pure typed numeric/boolean values | Numeric grades frequently encoded as strings (e.g. `"22.0"`) |
| **Binary Downloads** | S3 signed redirect URLs (`verifier` query param) | Direct stream over authenticated session (`stream=True`) |
| **Batch Optimization** | `/students/submissions?student_ids[]=self` (all course assignments at once) | Single-call assessment and submission indexes |

---

## Step-by-Step Guide: Rebuilding an LMS Integration from Scratch

Any engineer building a new sync engine or CLI tool for Canvas and Coursemology can follow this 5-stage architecture:

```
  +--------------------+         +------------------------+
  |  Canvas LMS API    |         |  Coursemology Rails    |
  | (Bearer Token REST)|         | (Session Cookie + CSRF)|
  +---------+----------+         +-----------+------------+
            |                                |
            v                                v
  [CanvasAPIClient]               [CoursemologyAPIClient]
  (docs/api/canvas.md)            (docs/api/coursemology.md)
            |                                |
            +----------------+---------------+
                             |
                             v
                +-------------------------+
                | Normalized Data Models  |
                | - Course                |
                | - Assignment / Task     |
                | - Announcement          |
                | - Submission Status     |
                +------------+------------+
                             |
                             v
                +-------------------------+
                | Daily Brief / CLI / UI  |
                | - Deadline Countdown    |
                | - Submission Verifier   |
                | - File Sync Engine      |
                +-------------------------+
```

### 1. Initialize Clients
- **Canvas**: Instantiate [`CanvasAPIClient`](file:///Users/javier/Projects/daily-brief/docs/api/canvas.md#8-standalone-reference-client-implementation-python) with `CANVAS_BASE_URL` and `CANVAS_API_TOKEN`. No login step required.
- **Coursemology**: Instantiate [`CoursemologyAPIClient`](file:///Users/javier/Projects/daily-brief/docs/api/coursemology.md#8-standalone-reference-client-implementation-python). Perform `login(email, password)` which visits `/users/sign_in`, extracts the CSRF token from HTML, and executes the credential POST.

### 2. Discover Courses & IDs
- Fetch active Canvas courses via `get_courses(enrollment_state="active")`.
- Fetch Coursemology enrolled courses via `get_courses()`.
- Map user course codes (e.g. `CS2102`, `CS2109S`) to system IDs.

### 3. Normalize Tasks & Deadlines
- For Canvas:
  - Query `get_assignments(course_id)` and `get_quizzes(course_id)`.
  - To minimize latency, query `get_batch_submissions(course_id, student_ids=["self"])` to resolve `submitted_at`, `score`, and `workflow_state` across all assignments in one call.
- For Coursemology:
  - Query `get_assessments(course_id)` to retrieve all tasks across categories.
  - Query `get_submissions(course_id)` to resolve student status (`attempted`, `submitted`, `graded`).
  - Use [`daily_brief.patches.coursemology`](file:///Users/javier/Projects/daily-brief/src/daily_brief/patches/coursemology.py) logic to safely cast `"22.0"` strings to float grades.
- Normalize all timestamps to UTC/SGT using standard ISO-8601 parsers.

### 4. Ingest Announcements & Feedback
- Canvas: Query `get_announcements(context_codes=["course_<id>", ...], start_date=...)`.
- Coursemology: Query `get_announcements(course_id)`.
- Strip HTML tags or render Markdown previews for desktop notification.

### 5. Media & File Handling
- For lecture videos: Use Canvas sessionless launch to open Panopto SSO streams, or Coursemology `/videos` for native video streams and audience retention statistics.
- For file downloads: Stream files from Canvas files API or Coursemology materials folders using standard chunked writes.

---

---

## Required Environment Variables

To execute live requests or run the probe script, ensure the following keys are populated in your `.env` file (see [`.env.example`](file:///Users/javier/Projects/daily-brief/.env.example)):

```bash
# Canvas LMS
CANVAS_BASE_URL=https://canvas.nus.edu.sg
CANVAS_API_TOKEN=<your_bearer_token>
CANVAS_COURSES="CS2102:93752,CS2107:93790,CS2109S:96985,CS3103:93794,CS4226:97020"

# Coursemology
COURSEMOLOGY_USERNAME=<your_email>
COURSEMOLOGY_PASSWORD=<your_password>
COURSEMOLOGY_COURSE_ID=3369
```
