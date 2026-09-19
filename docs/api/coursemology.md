# Coursemology API & SDK Documentation

This document provides complete, verified documentation for Coursemology's internal REST API endpoints and SDK integration based on live probing against `https://coursemology.org` and analysis of [`coursemology-py`](https://github.com/rizkiarm/coursemology-py.git).

It is structured to serve as an authoritative reference for current daily brief operations and future application development (such as automated submission verification, forum notifications, material downloads, and gamification tracking).

---

## Table of Contents
1. [Architecture & Web Framework](#1-architecture--web-framework)
2. [Authentication & Session Management](#2-authentication--session-management)
3. [The Mandatory `?format=json` Contract](#3-the-mandatory-formatjson-contract)
4. [Role-Based Access Control (RBAC) Matrix](#4-role-based-access-control-rbac-matrix)
5. [Complete Endpoints Reference](#5-complete-endpoints-reference)
   - [Authentication & User Profile](#authentication--user-profile)
   - [Course Discovery & Navigation](#course-discovery--navigation)
   - [Announcements](#announcements)
   - [Assessments (Tabs & Categories)](#assessments-tabs--categories)
   - [Submissions & Student Attempts](#submissions--student-attempts)
   - [Surveys & Feedback](#surveys--feedback)
   - [Forums & Discussions](#forums--discussions)
   - [Comments & Code Review](#comments--code-review)
   - [Workbin Materials & File Downloads](#workbin-materials--file-downloads)
   - [Lesson Plan & Milestones](#lesson-plan--milestones)
   - [Course Roster & Groups](#course-roster--groups)
   - [Course Videos & Lecture Media](#course-videos--lecture-media)
   - [Staff-Only Endpoints (403 Forbidden)](#staff-only-endpoints-403-forbidden)
6. [SDK Integration & Schema Drift Handling](#6-sdk-integration--schema-drift-handling)
7. [Project Implementation Mapping](#7-project-implementation-mapping)
8. [Standalone Reference Client Implementation (Python)](#8-standalone-reference-client-implementation-python)
9. [Quick Reference cURL Commands](#9-quick-reference-curl-commands)

---

## 1. Architecture & Web Framework

Coursemology runs on a **Ruby on Rails** backend paired with a React frontend. Unlike standard REST APIs that use Bearer tokens or dedicated API gateways, Coursemology serves both human users and programmatic clients through its Rails controllers.

- **Base URL**: `https://coursemology.org`
- **Protocol**: HTTPS / REST
- **Session State**: Cookie-backed HTTP sessions (`_coursemology2_session`)
- **CSRF Protection**: Rails authenticity tokens (`X-CSRF-Token`)
- **Format Parameter**: **Mandatory** `?format=json` on all requests

---

## 2. Authentication & Session Management

Coursemology uses cookie-based session authentication with Rails CSRF validation.

### Login Handshake Flow
1. **GET `/users/sign_in`**:
   Extract the authenticity token from `<meta name="csrf-token" content="...">` or `<input name="authenticity_token" ...>`.
2. **POST `/users/sign_in`**:
   Submit credentials with headers:
   - `Content-Type: application/x-www-form-urlencoded`
   - `X-CSRF-Token: <token>`
   Payload:
   ```text
   user[email]=<EMAIL>&user[password]=<PASSWORD>&authenticity_token=<TOKEN>
   ```
3. **Session Cookie**:
   Coursemology issues a `Set-Cookie: _coursemology2_session=...; HttpOnly; Secure; SameSite=Lax`.
   All subsequent requests must send this session cookie.

### Logout Flow
- **DELETE `/users/sign_out`**:
  Terminates the active session and clears the session cookie.

---

## 3. The Mandatory `?format=json` Contract

Coursemology controllers render HTML by default. To receive JSON payloads, programmatic requests **MUST** append `?format=json` (or include `Accept: application/json`).

```http
GET /courses/3369/assessments?format=json HTTP/1.1
Host: coursemology.org
Cookie: _coursemology2_session=...
```

> [!WARNING]
> Omitting `?format=json` causes Rails to return a `200 OK` HTML document containing the Single Page Application wrapper (`<!DOCTYPE html>...`), which fails JSON deserialization.

---

## 4. Role-Based Access Control (RBAC) Matrix

Coursemology enforces strict role boundaries:

| Resource Path | Student Role | Staff / Instructor Role |
| :--- | :---: | :---: |
| `/courses` | `200 OK` | `200 OK` |
| `/courses/{id}/assessments` | `200 OK` (Published only) | `200 OK` (Drafts + Published) |
| `/courses/{id}/assessments/submissions` | `200 OK` (Own submissions) | `200 OK` (All student submissions) |
| `/courses/{id}/assessments/{aid}/submissions/{sid}/edit` | `200 OK` (Own attempt) | `200 OK` (Any attempt + grading) |
| `/courses/{id}/materials/folders/{fid}` | `200 OK` (Read & download) | `200 OK` (Upload & delete) |
| `/courses/{id}/categories` | **`403 Forbidden`** | `200 OK` |
| `/courses/{id}/assessments/skills` | **`403 Forbidden`** | `200 OK` |
| `/courses/{id}/statistics/*` | **`403 Forbidden`** | `200 OK` |
| `/courses/{id}/experience_points_records` | **`403 Forbidden`** | `200 OK` |

---

## 5. Complete Endpoints Reference

### Authentication & User Profile

#### `GET /user/profile?format=json`
Returns personal account details for the authenticated user.
- **Status**: `200 OK`
- **Output Schema**:
  - `id`: `int`
  - `name`: `str`
  - `imageUrl`: `str | null`
  - `primaryEmail`: `str`

---

### Course Discovery & Navigation

#### `GET /courses?format=json`
Lists all public and enrolled courses accessible to the user.
- **Status**: `200 OK`
- **Output Schema**: Array of course records:
  - `id`: `int` (e.g. `3369`)
  - `title`: `str` (e.g. `"CS2109S AY2025-26 Sem 1"`)
  - `description`: `str` (HTML formatted)
  - `logoUrl`: `str | null`
  - `registrationInfo`: `dict` (`isEnrolled`, `role`)

#### `GET /courses/{course_id}?format=json`
Course homepage overview and active announcements banner.
- **Status**: `200 OK`
- **Output Schema**: Course metadata and user permissions.

#### `GET /courses/{course_id}/sidebar?format=json`
Returns sidebar navigation items enabled by course instructors.
- **Status**: `200 OK`
- **Output Schema**: Array of navigation items:
  - `id`: `str` (e.g. `"announcements"`, `"assessments_4811"`, `"materials"`, `"forums"`)
  - `title`: `str`
  - `type`: `str`
  - `weight`: `int`

---

### Announcements

#### `GET /courses/{course_id}/announcements?format=json`
Lists course announcements ordered newest first.
- **Status**: `200 OK`
- **Output Schema**:
  ```json
  {
    "announcements": [
      {
        "id": 10447,
        "title": "Problem Set 2 Available",
        "content": "<p>Problem Set 2 is now open...</p>",
        "startTime": "2026-09-03T10:00:00.000+08:00",
        "endTime": "2026-09-22T23:59:00.000+08:00",
        "isCurrentlyActive": true,
        "isSticky": false,
        "isUnread": false,
        "markAsReadUrl": "/courses/3369/announcements/10447/mark_as_read",
        "creator": { "name": "Instructor Name" }
      }
    ],
    "permissions": { "canCreate": false }
  }
  ```

> [!NOTE]
> Coursemology does not provide a single announcement route (`GET /announcements/{id}` returns `404 Not Found`). All announcements are embedded in the index endpoint.

---

### Assessments (Tabs & Categories)

#### `GET /courses/{course_id}/assessments?format=json`
Lists assessments in the default tab.
- **Status**: `200 OK`

#### `GET /courses/{course_id}/assessments?category={category_id}&format=json`
Filters assessments by category (e.g. Problem Sets `4810`, Lecture Trainings `4811`).
- **Status**: `200 OK`

#### `GET /courses/{course_id}/assessments?category={category_id}&tab={tab_id}&format=json`
Filters assessments by specific sub-tab (e.g. Extra Practice `9409`, Python Practice `9410`).
- **Status**: `200 OK`

#### `GET /courses/{course_id}/assessments/{assessment_id}?format=json`
Retrieves assessment configuration and instructions.
- **Status**: `200 OK`
- **Assessment Schema**:
  - `id`: `int`
  - `title`: `str`
  - `description`: `str` (HTML)
  - `startAt`, `endAt`, `bonusEndAt`: Serialized as nested objects:
    ```json
    {
      "isFixed": false,
      "effectiveTime": "2026-09-03T10:00:00.000+08:00",
      "referenceTime": "2026-09-03T10:00:00.000+08:00"
    }
    ```
  - `baseExp`: `int`
  - `timeBonusExp`: `int`
  - `autograded`: `bool`
  - `status`: `"attempted"` | `"submitted"` | `"opening"`

#### `POST /courses/{course_id}/assessments/{assessment_id}/submissions?format=json`
Starts a new assessment attempt for the student, creating a submission.
- **Status**: `200 OK` or `302 Redirect` to the attempt edit URL.

---

### Submissions & Student Attempts

#### `GET /courses/{course_id}/assessments/submissions?format=json`
Returns all submissions made by the user across all course assessments.
- **Status**: `200 OK`
- **Output Schema**:
  ```json
  {
    "submissions": [
      {
        "id": 2843513,
        "assessmentId": 93406,
        "title": "Problem Set 2: Search",
        "workflowState": "published",
        "grade": 22.0,
        "currentGrade": "22.0",
        "maxGrade": "22.0",
        "pointsAwarded": 2200,
        "bonusPoints": 0,
        "startedAt": "2026-09-03T10:05:00+08:00",
        "submittedAt": "2026-09-18T20:15:00+08:00"
      }
    ]
  }
  ```

#### `GET /courses/{course_id}/assessments/{assessment_id}/submissions/{submission_id}/edit?format=json`
**The Core Attempt Inspection & Working Endpoint**: Fetches questions, student answers, feedback, and grading for a submission.
- **Status**: `200 OK`
- **Output Structure (9 top-level keys)**:
  `['submission', 'assessment', 'questions', 'answers', 'topics', 'annotations', 'posts', 'history', 'getHelpCounts']`
- **Question Schema**:
  - `id`: `int`
  - `type`: `"TextResponse"` | `"MultipleChoice"` | `"MultipleResponse"` | `"Programming"`
  - `maximumGrade`: `float`
  - `questionNumber`: `int`
  - `questionTitle`: `str`
  - `description`: `str` (HTML question prompt)
  - `answerId`: `int`
  - `topicId`: `int` (linked discussion topic for questions)
- **Answer Schema**:
  - `id`: `int`
  - `questionId`: `int`
  - `fields`: `{"answer_text": str}` (or `files` for programming questions)
  - `grading`: `{"id": int, "grade": float}`
  - `explanation`: `{"correct": bool, "explanations": list}`

> [!CRITICAL]
> 1. Requesting `GET .../submissions/{id}` without `/edit` returns **`404 Not Found`**.
> 2. `{assessment_id}` in the path **MUST** match the submission's parent assessment. Supplying a mismatched assessment ID returns **`404 Not Found`**.

#### `POST /courses/{course_id}/assessments/{assessment_id}/submissions/{submission_id}/questions/{q_id}/answers?format=json`
Saves student answer drafts for a specific question during an active attempt.
- **Status**: `200 OK`
- **Request Body (Text / Code / MCQ)**:
  ```json
  {
    "answer": {
      "fields": {
        "answer_text": "def solve():\n    return 42"
      }
    }
  }
  ```
- **Response**: Updated `answer` object reflecting saved status and timestamps.

#### `POST /courses/{course_id}/assessments/{assessment_id}/submissions/{submission_id}/questions/{q_id}/run_code?format=json`
Triggers execution of autograded test suites against student code in Coursemology's sandboxed evaluator.
- **Status**: `200 OK`
- **Request Body**:
  ```json
  {
    "answer": {
      "fields": {
        "files": [
          {
            "filename": "submission.py",
            "content": "def search(problem):\n    return []"
          }
        ]
      }
    }
  }
  ```
- **Response**: May return evaluation results immediately or a polling job descriptor:
  ```json
  {
    "stdout": "Running tests...\nAll public tests passed.\n",
    "stderr": "",
    "testCases": [
      {
        "identifier": "public_test_1",
        "description": "Base case graph search",
        "passed": true,
        "expected": "[1, 2, 3]",
        "output": "[1, 2, 3]"
      }
    ]
  }
  ```

#### `PUT /courses/{course_id}/assessments/{assessment_id}/submissions/{submission_id}?format=json`
Finalizes student submission for an assessment attempt (transitions workflow state from `"attempting"` to `"submitted"`).
- **Status**: `200 OK`
- **Request Body**:
  ```json
  {
    "submission": {
      "finalise": true
    }
  }
  ```
- **Response**: Updated submission object with `workflowState: "submitted"`, `submittedAt: "<ISO_TIMESTAMP>"`, and provisional grade (if autograded).

---

### Surveys & Feedback

#### `GET /courses/{course_id}/surveys?format=json`
Lists course feedback surveys.
- **Status**: `200 OK`
- **Output Schema**: Array of surveys with `id`, `title`, `base_exp`, `start_at`, `end_at`, and the user's `response` object (`submitted_at`, `canSubmit`, `canModify`).

#### `GET /courses/{course_id}/surveys/{survey_id}?format=json`
Retrieves survey sections, questions, and submission status.
- **Status**: `200 OK`

#### `GET /courses/{course_id}/surveys/{survey_id}/responses/{response_id}/edit?format=json`
Views or edits a survey response. Returns `403 Forbidden` if submitted and `allow_modify_after_submit: false`.

---

### Forums & Discussions

#### `GET /courses/{course_id}/forums?format=json`
Lists discussion boards in the course.
- **Status**: `200 OK`
- **Output Schema**:
  - `id`: `int` (e.g. `4254`)
  - `name`: `str`
  - `description`: `str`
  - `topicCount`: `int`
  - `topicPostCount`: `int`
  - `topicUnreadCount`: `int`
  - `forumUrl`: `str`

#### `GET /courses/{course_id}/forums/{forum_id}?format=json`
Lists topics within a forum.
- **Status**: `200 OK`
- **Output Schema**: Array of topics (`id`, `title`, `postCount`, `viewCount`, `isUnread`, `isLocked`, `topicUrl`).

#### `GET /courses/{course_id}/forums/{forum_id}/topics/{topic_id}?format=json`
Returns full post thread of a discussion topic.
- **Status**: `200 OK`
- **Output Schema**:
  - `topic`: `dict`
  - `posts`: Array of post objects (`id`, `text`, `createdAt`, `creator`).

#### `POST /courses/{course_id}/forums/{forum_id}/topics?format=json`
Creates a new discussion topic.

#### `POST /courses/{course_id}/forums/{forum_id}/topics/{topic_id}/posts?format=json`
Replies to an existing topic thread.

---

### Comments & Code Review

#### `GET /courses/{course_id}/comments?format=json`
Lists unread inline comments and code reviews.
- **Status**: `200 OK`
- **Query Parameters**:
  - `tab`: `"all_student"` or `"my_students"`

---

### Workbin Materials & File Downloads

#### `GET /courses/{course_id}/materials/folders?format=json`
Lists root folders in course materials.
- **Status**: `200 OK`
- **Output Schema**:
  - `subfolders`: Array of folders (`id`, `name`, `itemCount`, `startAt`).

#### `GET /courses/{course_id}/materials/folders/{folder_id}?format=json`
Retrieves files within a folder.
- **Status**: `200 OK`
- **Output Schema**:
  - `materials`: Array of files:
    - `id`: `int` (e.g. `200310`)
    - `name`: `str` (e.g. `"CS2109S AY2025-26 Sem 1 - Final Exam - Solution.pdf"`)
    - `materialUrl`: `str` (e.g. `"/courses/3369/materials/folders/120993/files/200310"`)
    - `updatedAt`: `str`

#### `GET /courses/{course_id}/materials/folders/{folder_id}/files/{file_id}`
Directly downloads file contents with authenticated session cookie.
- **Status**: `200 OK` (Streams raw file binary, e.g. PDF, ZIP, code).
- **Download Semantics**:
  - **Omit** `?format=json` on download requests.
  - The server returns HTTP 200 with headers:
    - `Content-Type: application/pdf` (or `application/octet-stream`)
    - `Content-Disposition: attachment; filename="CS2109S AY2025-26 Sem 1 - Final Exam - Solution.pdf"`
  - Clients should stream the response directly to disk (`stream=True` in Python `requests`).

---

### Lesson Plan & Milestones

#### `GET /courses/{course_id}/lesson_plan?format=json`
Returns semester milestones, weekly topics, and release dates.
- **Status**: `200 OK`
- **Output Schema**:
  - `milestones`: Array of milestones (`id`, `title`, `start_at`).
  - `items`: Array of lesson plan items (`id`, `title`, `start_at`, `end_at`, `item_path`, `lesson_plan_item_type`).

> [!NOTE]
> Unlike assessments which use camelCase (`startAt`), `lesson_plan` uses snake_case (`start_at`, `end_at`, `bonus_end_at`).

---

### Gamification (Badges & Leaderboard)

#### `GET /courses/{course_id}/achievements?format=json`
Lists unlockable course badges and current completion status.
- **Status**: `200 OK`
- **Output Schema**:
  - `achievements`: Array of badges:
    - `id`: `int`
    - `title`: `str` (e.g. `"Fresh Student"`)
    - `badge`: `{"name": str, "url": "https://coursemology3.s3.ap-southeast-1.amazonaws.com/..."}`
    - `achievementStatus`: `"granted"` | `"locked"`
    - `conditions`: Array of requirements (e.g. `{"description": "Level 1"}`).

#### `GET /courses/{course_id}/leaderboard?format=json`
Returns top students ranked by EXP and achievement counts.
- **Status**: `200 OK`
- **Output Schema**:
  - `leaderboardByExpPoints`: Array of `{"id": int, "name": str, "level": int, "experience": int}`.
  - `leaderboardByAchievementCount`: Array of `{"id": int, "name": str, "level": int, "achievementCount": int}`.

---

### Course Roster & Groups

#### `GET /courses/{course_id}/users?format=json`
Lists course members (students, tutors, professors).
- **Status**: `200 OK` (427 users enrolled in CS2109S).
- **Output Schema**: Array of user records (`id`, `name`, `role`, `courseUserId`).

#### `GET /courses/{course_id}/groups?format=json`
Lists student tutorial and project groups.
- **Status**: `200 OK`
- **Output Schema**: Array of groups (`id`, `name`, `members`).

---

### Course Videos & Lecture Media

Coursemology natively hosts and tracks course video lectures, breaktime clips, and supplemental video materials. Videos can be categorized across multiple tabs and integrated with watch-completion tracking.

#### `GET /courses/{course_id}/videos?format=json`
Lists available video tabs and videos for the default active tab.
- **Status**: `200 OK`
- **Top-Level Schema**:
  - `videoTitle`: `str` (e.g. `"Videos"`)
  - `videoTabs`: Array of tab descriptors:
    ```json
    [
      { "id": 3007, "title": "Lecture" },
      { "id": 3008, "title": "Recent Advances" },
      { "id": 3009, "title": "Breaktime Clips" }
    ]
    ```
  - `videos`: Array of video objects in the default tab.
  - `metadata`: Pagination and filtering metadata.
  - `permissions`: `{"canManage": bool, "canCreate": bool}`.

#### `GET /courses/{course_id}/videos?tab={tab_id}&format=json`
Retrieves videos specifically under a chosen tab ID (e.g. `tab=3008` for Recent Advances).
- **Status**: `200 OK`
- **Video Item Schema**:
  ```json
  {
    "id": 26276,
    "tabId": 3008,
    "title": "AlphaStar: The inside story",
    "description": "",
    "url": "https://www.youtube.com/embed/UuhECwm31dM",
    "published": true,
    "hasPersonalTimes": false,
    "affectsPersonalTimes": false,
    "startTimeInfo": {
      "isFixed": false,
      "effectiveTime": "2026-08-09T10:00:00.000+08:00",
      "referenceTime": "2026-08-09T10:00:00.000+08:00"
    },
    "videoSubmissionId": null,
    "permissions": {
      "canAttempt": true,
      "canManage": false
    }
  }
  ```

#### `GET /courses/{course_id}/videos/{video_id}?format=json`
Retrieves single video details along with audience retention and watch frequency analytics across the entire student cohort.
- **Status**: `200 OK`
- **Output Schema**:
  - `video`: Video metadata including `videoStatistics`:
    ```json
    {
      "id": 26276,
      "title": "AlphaStar: The inside story",
      "url": "https://www.youtube.com/embed/UuhECwm31dM",
      "videoSubmissionId": null,
      "videoStatistics": {
        "video": {
          "videoUrl": "https://www.youtube.com/embed/UuhECwm31dM"
        },
        "statistics": {
          "watchFrequency": [6, 6, 6, 6, 5, 5, 5, 4, 4, 4, ...]
        }
      }
    }
    ```
  - `watchFrequency`: Array of viewer counts per second/timestamp throughout the video, providing a cohort heat-map of student engagement.

#### Video Watch Tracking & Submissions
- **Student Watch Attempt**: When a student opens and plays a video, an attempt is created via `POST /courses/{course_id}/videos/{video_id}/submissions?format=json`. When recorded, the video object populates `videoSubmissionId: <id>` to mark completion.
- **Cohort Submissions Inspection**: `GET /courses/{course_id}/videos/{video_id}/submissions?format=json` is restricted to teaching staff and returns `403 Forbidden` for students.

---

### Staff-Only Endpoints (403 Forbidden)

The following endpoints exist in Coursemology's Rails controllers but are restricted to teaching staff:

- `GET /courses/{id}/categories`: Category management
- `GET /courses/{id}/assessments/skills`: Skills mastery configuration
- `GET /courses/{id}/statistics/*`: Performance analytics
- `GET /courses/{id}/experience_points_records`: EXP transaction logs
- `GET /courses/{id}/user_invitations`: Enrollment invite tokens
- `GET /courses/{id}/users/disbursements`: Bulk EXP point awards

---

## 6. SDK Integration & Schema Drift Handling

The upstream [`coursemology-py`](https://github.com/rizkiarm/coursemology-py.git) library provides Pydantic models for Coursemology. However, because Coursemology's frontend evolves rapidly, several models have drifted from the live backend:

1. **Submission Grade Parsing**:
   Upstream expects `currentGrade` and `maxGrade` as floats, but live Rails JSON returns formatted decimal strings (`"22.0"`).
   - **Fix**: Patched with string-to-float pre-validators in [`daily_brief.patches.coursemology`](file:///Users/javier/Projects/daily-brief/src/daily_brief/patches/coursemology.py).
2. **Assessment Time Objects**:
   Upstream expects `startAt` and `endAt` as ISO strings, but live Coursemology nests them in `{"isFixed": bool, "effectiveTime": str}` objects.
   - **Fix**: Normalized via fallback extraction in [`extract_assessments_data`](file:///Users/javier/Projects/daily-brief/src/daily_brief/coursemology/api.py#L182).
3. **Session Re-use**:
   The SDK's internal `_session` carries authenticated cookies and CSRF headers, allowing direct REST requests to endpoints not yet modeled in the SDK.

---

## 7. Project Implementation Mapping

| Purpose | Coursemology Endpoint | Implementation Reference |
| :--- | :--- | :--- |
| **Authentication** | `GET /users/sign_in`, `POST /users/sign_in` | [`coursemology_py.CoursemologyClient.login`](https://github.com/rizkiarm/coursemology-py.git) |
| **Announcements** | `GET /courses/{id}/announcements` | [`fetch_coursemology_data`](file:///Users/javier/Projects/daily-brief/src/daily_brief/coursemology/api.py#L52) |
| **Assessments** | `GET /courses/{id}/assessments` | [`fetch_coursemology_data`](file:///Users/javier/Projects/daily-brief/src/daily_brief/coursemology/api.py#L55) |
| **Submissions** | `GET /courses/{id}/assessments/submissions` | [`fetch_coursemology_data`](file:///Users/javier/Projects/daily-brief/src/daily_brief/coursemology/api.py#L58) |
| **Attempt Inspection** | `GET /courses/{id}/assessments/{aid}/submissions/{sid}/edit` | [`fetch_coursemology_data`](file:///Users/javier/Projects/daily-brief/src/daily_brief/coursemology/api.py#L82) |
| **Schema Patching** | Pydantic model validation | [`daily_brief.patches.coursemology`](file:///Users/javier/Projects/daily-brief/src/daily_brief/patches/coursemology.py) |
| **Materials & Files** | `GET /courses/{id}/materials/folders/{fid}` | Documented for future automated file syncing. |
| **Forums & Discussions** | `GET /courses/{id}/forums/{fid}/topics/{tid}` | Documented for future forum digests and replies. |
| **Surveys** | `GET /courses/{id}/surveys/{sid}` | Documented for future survey reminders. |

---

## 8. Standalone Reference Client Implementation (Python)

Below is a complete, self-contained Python reference client (`CoursemologyAPIClient`) built exclusively with the standard `requests` library. It does not require `coursemology-py` or any third-party SDK. It implements the Rails CSRF/session cookie login handshake, automatic `?format=json` enforcement, CSRF token header synchronization, and high-level methods for all verified endpoints.

```python
import os
import re
from typing import Any, Optional
import requests


class CoursemologyAPIError(Exception):
    """Base exception for Coursemology API errors."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"Coursemology API HTTP {status_code}: {message}")
        self.status_code = status_code


class CoursemologyAPIClient:
    """Production-ready standalone client for Coursemology LMS API."""

    def __init__(self, base_url: str = "https://coursemology.org", timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (DailyBrief/1.0)",
            "Accept": "application/json, text/plain, */*",
        })
        self.csrf_token: Optional[str] = None
        self.timeout = timeout

    def login(self, email: str, password: str) -> None:
        """Executes the Rails CSRF and cookie authentication handshake."""
        # Step 1: GET /users/sign_in to obtain initial authenticity token & session cookie
        sign_in_url = f"{self.base_url}/users/sign_in"
        resp = self.session.get(sign_in_url, timeout=self.timeout)
        if resp.status_code != 200:
            raise CoursemologyAPIError(resp.status_code, "Failed to load sign-in page")

        # Extract CSRF token from HTML meta tags or hidden inputs
        match = re.search(r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']', resp.text)
        if not match:
            match = re.search(r'name=["\']authenticity_token["\']\s+value=["\']([^"\']+)["\']', resp.text)
        if not match:
            raise CoursemologyAPIError(500, "Could not extract CSRF authenticity token from sign_in page")

        self.csrf_token = match.group(1)

        # Step 2: POST /users/sign_in with user credentials
        login_data = {
            "user[email]": email,
            "user[password]": password,
            "authenticity_token": self.csrf_token,
        }
        post_resp = self.session.post(
            sign_in_url,
            data=login_data,
            timeout=self.timeout,
            allow_redirects=True,
        )

        # Verify authenticated state (cookies must contain _coursemology2_session)
        if "_coursemology2_session" not in self.session.cookies:
            raise CoursemologyAPIError(401, "Login failed: missing _coursemology2_session cookie")

        # Step 3: Refresh CSRF token for subsequent API mutations
        self.session.headers.update({"X-CSRF-Token": self.csrf_token})

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
        as_json: bool = True,
    ) -> requests.Response:
        url = f"{self.base_url}{path}" if path.startswith("/") else path
        req_params = dict(params or {})

        # Coursemology requires ?format=json for API endpoints (unless downloading raw binaries)
        if as_json and "format" not in req_params:
            req_params["format"] = "json"

        resp = self.session.request(
            method,
            url,
            params=req_params,
            json=json_data,
            timeout=self.timeout,
        )

        if resp.status_code >= 400:
            raise CoursemologyAPIError(resp.status_code, resp.text[:300])

        return resp

    # --- Profile & Identity ---
    def get_user_profile(self) -> dict[str, Any]:
        return self._request("GET", "/user/profile").json()

    # --- Courses ---
    def get_courses(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/courses").json()
        return data.get("courses", [])

    def get_course(self, course_id: int) -> dict[str, Any]:
        return self._request("GET", f"/courses/{course_id}").json()

    def get_sidebar(self, course_id: int) -> list[dict[str, Any]]:
        data = self._request("GET", f"/courses/{course_id}/sidebar").json()
        return data.get("sidebar", [])

    # --- Announcements ---
    def get_announcements(self, course_id: int) -> list[dict[str, Any]]:
        data = self._request("GET", f"/courses/{course_id}/announcements").json()
        return data.get("announcements", [])

    # --- Assessments ---
    def get_assessments(
        self,
        course_id: int,
        category_id: Optional[int] = None,
        tab_id: Optional[int] = None,
    ) -> dict[str, Any]:
        params = {}
        if category_id:
            params["category"] = category_id
        if tab_id:
            params["tab"] = tab_id
        return self._request("GET", f"/courses/{course_id}/assessments", params=params).json()

    # --- Submissions & Attempts ---
    def get_submissions(self, course_id: int) -> list[dict[str, Any]]:
        data = self._request("GET", f"/courses/{course_id}/assessments/submissions").json()
        return data.get("submissions", [])

    def get_submission_edit(self, course_id: int, assessment_id: int, submission_id: int) -> dict[str, Any]:
        """Core attempt inspection endpoint containing questions, answers, and feedback."""
        return self._request(
            "GET",
            f"/courses/{course_id}/assessments/{assessment_id}/submissions/{submission_id}/edit",
        ).json()

    def save_draft_answer(
        self,
        course_id: int,
        assessment_id: int,
        submission_id: int,
        question_id: int,
        answer_text: str,
    ) -> dict[str, Any]:
        payload = {"answer": {"fields": {"answer_text": answer_text}}}
        return self._request(
            "POST",
            f"/courses/{course_id}/assessments/{assessment_id}/submissions/{submission_id}/questions/{question_id}/answers",
            json_data=payload,
        ).json()

    def run_autograder_code(
        self,
        course_id: int,
        assessment_id: int,
        submission_id: int,
        question_id: int,
        files: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Executes sandbox testcases. Files format: [{'filename': 'main.py', 'content': '...'}]"""
        payload = {"answer": {"fields": {"files": files}}}
        return self._request(
            "POST",
            f"/courses/{course_id}/assessments/{assessment_id}/submissions/{submission_id}/questions/{question_id}/run_code",
            json_data=payload,
        ).json()

    def finalize_submission(self, course_id: int, assessment_id: int, submission_id: int) -> dict[str, Any]:
        payload = {"submission": {"finalise": True}}
        return self._request(
            "PUT",
            f"/courses/{course_id}/assessments/{assessment_id}/submissions/{submission_id}",
            json_data=payload,
        ).json()

    # --- Workbin Materials & File Downloads ---
    def get_materials_folders(self, course_id: int) -> dict[str, Any]:
        return self._request("GET", f"/courses/{course_id}/materials/folders").json()

    def get_folder_materials(self, course_id: int, folder_id: int) -> dict[str, Any]:
        return self._request("GET", f"/courses/{course_id}/materials/folders/{folder_id}").json()

    def download_material(self, course_id: int, folder_id: int, file_id: int, target_file_path: str) -> None:
        """Streams a raw binary file to disk."""
        url = f"{self.base_url}/courses/{course_id}/materials/folders/{folder_id}/files/{file_id}"
        resp = self.session.get(url, stream=True, timeout=self.timeout)
        resp.raise_for_status()
        os.makedirs(os.path.dirname(os.path.abspath(target_file_path)), exist_ok=True)
        with open(target_file_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    # --- Videos & Lecture Media ---
    def get_videos(self, course_id: int, tab_id: Optional[int] = None) -> list[dict[str, Any]]:
        params = {"tab": tab_id} if tab_id else {}
        data = self._request("GET", f"/courses/{course_id}/videos", params=params).json()
        return data.get("videos", [])

    def get_video_details(self, course_id: int, video_id: int) -> dict[str, Any]:
        return self._request("GET", f"/courses/{course_id}/videos/{video_id}").json()

    # --- Gamification & Leaderboard ---
    def get_leaderboard(self, course_id: int) -> dict[str, Any]:
        return self._request("GET", f"/courses/{course_id}/leaderboard").json()

    def get_achievements(self, course_id: int) -> list[dict[str, Any]]:
        data = self._request("GET", f"/courses/{course_id}/achievements").json()
        return data.get("achievements", [])
```

---

## 9. Quick Reference cURL Commands

Automating Coursemology from the terminal requires maintaining a cookie jar across invocations.

```bash
# 1. Step 1: Request sign-in page to extract authenticity token & initial session cookie
curl -s -c cookies.txt "https://coursemology.org/users/sign_in" > sign_in.html
CSRF_TOKEN=$(grep -o 'name="csrf-token" content="[^"]*"' sign_in.html | cut -d'"' -f4)

# 2. Step 2: POST credentials with CSRF token and save session cookie
curl -s -b cookies.txt -c cookies.txt \
  -d "user[email]=student@example.com" \
  -d "user[password]=secret_password" \
  -d "authenticity_token=${CSRF_TOKEN}" \
  -L "https://coursemology.org/users/sign_in" > /dev/null

# 3. List Enrolled Courses (JSON)
curl -s -b cookies.txt "https://coursemology.org/courses?format=json"

# 4. Fetch Course Assessments
curl -s -b cookies.txt "https://coursemology.org/courses/3369/assessments?format=json"

# 5. Fetch Full Submission Attempt (Questions, Student Answers, Rubric)
curl -s -b cookies.txt \
  "https://coursemology.org/courses/3369/assessments/11090/submissions/325776/edit?format=json"

# 6. Stream and Save a Material File (Binary PDF)
curl -s -b cookies.txt \
  -OJ "https://coursemology.org/courses/3369/materials/folders/120993/files/200310"

# 7. Fetch Lecture Videos and Statistics
curl -s -b cookies.txt "https://coursemology.org/courses/3369/videos?format=json"
```
