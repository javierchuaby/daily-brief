# Canvas LMS API Documentation

This document provides complete, verified documentation for the Canvas LMS REST API endpoints based on live probing against the National University of Singapore (NUS) Canvas instance (`https://canvas.nus.edu.sg`) and the [official Canvas LMS API specification](https://developerdocs.instructure.com/services/canvas).

It is structured to serve as an authoritative reference for current daily brief operations and future application development (such as submission syncing, discussion scraping, file downloads, and course planning).

---

## Table of Contents
1. [Architecture & Protocol](#1-architecture--protocol)
2. [Authentication & Security](#2-authentication--security)
3. [Pagination, Rate Limiting & Headers](#3-pagination-rate-limiting--headers)
4. [Date, Time & Locale Handling](#4-date-time--locale-handling)
5. [Complete Endpoints Reference](#5-complete-endpoints-reference)
   - [User & Profile Endpoints](#user--profile-endpoints)
   - [Planner Endpoints](#planner-endpoints)
   - [Course Management Endpoints](#course-management-endpoints)
   - [Announcements Endpoints](#announcements-endpoints)
   - [Assignments & Assignment Groups Endpoints](#assignments--assignment-groups-endpoints)
   - [Submissions Endpoints (Single & Batch)](#submissions-endpoints-single--batch)
   - [Quizzes Endpoints](#quizzes-endpoints)
   - [Modules & Module Items Endpoints](#modules--module-items-endpoints)
   - [Discussion Topics & Thread Views](#discussion-topics--thread-views)
   - [Pages & Wiki Content](#pages--wiki-content)
   - [Files & Folders Endpoints](#files--folders-endpoints)
   - [Enrollments, Roster & Sections](#enrollments-roster--sections)
   - [Calendar Events Endpoints](#calendar-events-endpoints)
    - [Course Navigation Tabs & LTI External Tools (Panopto / Zoom)](#course-navigation-tabs--lti-external-tools-panopto--zoom)
    - [Lecture Videos & Panopto Integration Architecture](#lecture-videos--panopto-integration-architecture)
6. [Known Upstream Quirks & Error Responses](#6-known-upstream-quirks--error-responses)
7. [Project Implementation Mapping](#7-project-implementation-mapping)
8. [Standalone Reference Client Implementation (Python)](#8-standalone-reference-client-implementation-python)
9. [Quick Reference cURL Commands](#9-quick-reference-curl-commands)

---

## 1. Architecture & Protocol

Canvas LMS provides a JSON-based RESTful API namespaced under `/api/v1`.

- **Base URL**: `https://canvas.nus.edu.sg` (configured via `CANVAS_BASE_URL` in `.env`).
- **Data Exchange**: Requests and responses use UTF-8 JSON (`Content-Type: application/json; charset=utf-8`).
- **HTTP Methods**:
  - `GET`: Read resources, lists, and metadata.
  - `POST`: Create submissions, replies, and resources.
  - `PUT`: Update records, mark module items as complete.
  - `DELETE`: Remove enrollments or content (where permitted).

---

## 2. Authentication & Security

All requests require an OAuth2 Bearer token passed in the `Authorization` request header:

```http
Authorization: Bearer <CANVAS_API_TOKEN>
```

Tokens are provisioned in Canvas via:
**Account** &rarr; **Settings** &rarr; **Approved Integrations** &rarr; **+ New Access Token**.

### Authentication Errors (401 Unauthorized)
When a token is missing, expired, or revoked, Canvas returns:
```json
HTTP/1.1 401 Unauthorized
Content-Type: application/json; charset=utf-8

{
  "status": "unauthenticated",
  "errors": [
    { "message": "user authorisation required" }
  ]
}
```

### Authorization Errors (403 Forbidden)
When an endpoint is requested that the current user's role cannot access (e.g., student attempting to view quiz questions ahead of time):
```json
HTTP/1.1 403 Forbidden
Content-Type: application/json; charset=utf-8

{
  "status": "unauthorized",
  "errors": [
    { "message": "user not authorised to perform that action" }
  ]
}
```

---

## 3. Pagination, Rate Limiting & Headers

### RFC 5988 Pagination (Link Header)
Collections return a default page size (10 items). Pass `per_page=100` (max 100) to minimize round-trips. Always parse the `Link` header:

```http
Link: <https://canvas.nus.edu.sg/api/v1/courses?page=1&per_page=10>; rel="current",
      <https://canvas.nus.edu.sg/api/v1/courses?page=2&per_page=10>; rel="next",
      <https://canvas.nus.edu.sg/api/v1/courses?page=1&per_page=10>; rel="first",
      <https://canvas.nus.edu.sg/api/v1/courses?page=5&per_page=10>; rel="last"
```

### Leaky Bucket Rate Limiting
Canvas tracks client consumption using two response headers:
- `X-Rate-Limit-Remaining`: Remaining capacity before throttling (starts around `700.0`).
- `X-Request-Cost`: Estimated processing cost of the call (typically `0.05` to `0.30`).

---

## 4. Date, Time & Locale Handling

All timestamps returned by Canvas are in **ISO-8601 UTC** with a `Z` suffix:
```text
2026-09-19T11:50:29Z
```

In this project, dates are parsed and converted to **Singapore Standard Time (SGT, UTC+8)**:
- Conversion: `format_date_sgt()` in [`daily_brief.utils`](file:///Users/javier/Projects/daily-brief/src/daily_brief/utils.py).
- Remaining time: `get_time_until()` in [`daily_brief.utils`](file:///Users/javier/Projects/daily-brief/src/daily_brief/utils.py).

---

## 5. Complete Endpoints Reference

### User & Profile Endpoints

#### `GET /api/v1/users/self`
Retrieves identity and basic profile information for the authenticated user.
- **Status**: `200 OK`
- **Output Schema**:
  - `id`: `int` (e.g. `197839`)
  - `name`: `str`
  - `sortable_name`: `str`
  - `short_name`: `str`
  - `avatar_url`: `str`
  - `effective_locale`: `str` (e.g. `"en-GB"`)
  - `permissions`: `dict` (`can_update_name`, `can_update_avatar`)

#### `GET /api/v1/users/self/profile`
Returns extended profile details including bio and email addresses.
- **Status**: `200 OK`
- **Output Schema**:
  - `id`: `int`
  - `name`: `str`
  - `primary_email`: `str`
  - `login_id`: `str`
  - `time_zone`: `str` (e.g. `"Asia/Singapore"`)
  - `bio`: `str | null`

#### `GET /api/v1/users/self/activity_stream`
Returns an aggregated chronological activity stream across all enrolled courses.
- **Status**: `200 OK`
- **Item Count**: 21+ items
- **Output Schema**: Array of activity items:
  - `id`: `int`
  - `title`: `str`
  - `message`: `str`
  - `created_at`: `str` (ISO-8601)
  - `type`: `str` (`"Announcement"`, `"Submission"`, `"DiscussionTopic"`, `"Message"`)
  - `course_id`: `int`
  - `notification_category`: `str`

#### `GET /api/v1/users/self/activity_stream/summary`
Returns unread and total counts grouped by notification category.
- **Status**: `200 OK`
- **Output Schema**: Array of summary objects:
  - `type`: `str`
  - `count`: `int`
  - `unread_count`: `int`
  - `notification_category`: `str`

#### `GET /api/v1/users/self/todo`
Returns actionable to-do items (upcoming unsubmitted assignments, unread grading).
- **Status**: `200 OK`
- **Output Schema**: Array of to-do items.

#### `GET /api/v1/users/self/upcoming_events`
Returns calendar events and assignment deadlines scheduled in the near future.
- **Status**: `200 OK`
- **Output Schema**: Array of event/assignment records.

#### `GET /api/v1/users/self/missing_submissions`
Returns past-due assignments that the user has not yet submitted.
- **Status**: `200 OK`
- **Output Schema**: Array of assignment objects with `due_at`, `points_possible`, `course_id`.

#### `GET /api/v1/users/self/colors`
Retrieves custom UI dashboard colors set by the student for courses.
- **Status**: `200 OK`
- **Output Schema**: `{"custom_colors": {"course_93752": "#2C3E50", ...}}`

---

### Planner Endpoints

#### `GET /api/v1/planner/items`
Returns student agenda and calendar items with associated submission statuses.
- **Status**: `200 OK`
- **Query Parameters**:
  - `start_date`: ISO datetime
  - `end_date`: ISO datetime
  - `context_codes[]`: `course_{id}`
- **Output Schema**: Array of planner records:
  - `plannable_id`: `int`
  - `plannable_type`: `str` (`"assignment"`, `"quiz"`, `"discussion_topic"`, `"planner_note"`)
  - `plannable_date`: `str` (ISO-8601)
  - `submissions`: `dict` (`submitted`, `excused`, `graded`, `late`, `missing`, `feedback`)
  - `html_url`: `str`

---

### Course Management Endpoints

#### `GET /api/v1/courses`
Lists active course enrollments for the student.
- **Status**: `200 OK`
- **Query Parameters**:
  - `enrollment_state`: `active`
  - `include[]`: `term`, `total_scores`, `syllabus_body`
- **Keys Returned**: `id`, `name`, `course_code`, `enrollment_term_id`, `default_view`, `workflow_state`, `enrollments`, `calendar`, `time_zone`.

#### `GET /api/v1/courses/{course_id}`
Retrieves single course details.
- **Status**: `200 OK`

#### `GET /api/v1/courses/{course_id}/front_page`
Returns the designated wiki front/home page of a course.
- **Status**: `200 OK`
- **Output Schema**: `url`, `title`, `body` (HTML), `editing_roles`, `published`, `updated_at`.

#### `GET /api/v1/courses/{course_id}/course_progress`
- **Status**: `404 Not Found` (unless completion requirements are active on modules).
- **Behavior**: Handled gracefully by returning `{}` in [`CanvasClient.get_course_progress`](file:///Users/javier/Projects/daily-brief/src/daily_brief/canvas/api.py#L86).

---

### Announcements Endpoints

#### `GET /api/v1/announcements`
Fetches announcements for one or more courses.
- **Status**: `200 OK`
- **Query Parameters**:
  - `context_codes[]`: Array of `course_{id}` strings (e.g. `course_93752`)
  - `start_date`: ISO datetime
  - `end_date`: ISO datetime
- **Output Schema**:
  - `id`: `int`
  - `title`: `str`
  - `message`: `str` (HTML formatted announcement content)
  - `posted_at`: `str` (ISO-8601)
  - `author`: `dict` (`id`, `display_name`, `avatar_image_url`)
  - `url`: `str`
  - `context_code`: `str`

---

### Assignments & Assignment Groups Endpoints

#### `GET /api/v1/courses/{course_id}/assignments`
Lists course assignments.
- **Status**: `200 OK`
- **Query Parameters**:
  - `include[]`: `submission`, `assignment_overrides`
- **Verified Keys (63 fields)**:
  `id`, `name`, `description`, `due_at`, `unlock_at`, `lock_at`, `points_possible`, `grading_type`, `submission_types`, `has_submitted_submissions`, `published`, `html_url`, `submission`, `overrides`.
- **Observed `submission_types`**:
  - `online_upload`: File uploads (PDF, ZIP, source code)
  - `online_quiz`: Canvas online quizzes
  - `external_tool`: External LTI tools (Coursemology, Gradescope)
  - `none`: In-person participation or presentation

#### `GET /api/v1/courses/{course_id}/assignments/{assignment_id}`
Returns a single assignment with full instructions and configuration.
- **Status**: `200 OK`

#### `GET /api/v1/courses/{course_id}/assignment_groups`
Returns gradebook categories and group weights (e.g. Assignments 40%, Midterm 20%, Final 40%).
- **Status**: `200 OK`
- **Output Schema**: Array of `{"id": int, "name": str, "group_weight": float, "position": int}`.

---

### Submissions Endpoints (Single & Batch)

#### `GET /api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/self`
Retrieves current user's submission state for an assignment.
- **Status**: `200 OK`
- **Output Schema**:
  ```json
  {
    "id": 1492081,
    "assignment_id": 268868,
    "user_id": 197839,
    "workflow_state": "submitted",
    "submitted_at": "2026-09-18T14:30:00Z",
    "graded_at": "2026-09-19T08:15:00Z",
    "score": 95.0,
    "grade": "95",
    "attempt": 1,
    "submission_type": "online_upload",
    "late": false,
    "missing": false,
    "excused": false,
    "preview_url": "https://canvas.nus.edu.sg/courses/93752/assignments/268868/submissions/197839?preview=1",
    "body": null,
    "url": null,
    "attachments": [
      {
        "id": 9674841,
        "uuid": "4xK8W7V...",
        "folder_id": 312040,
        "display_name": "assignment_report.pdf",
        "filename": "assignment_report.pdf",
        "content-type": "application/pdf",
        "url": "https://canvas.nus.edu.sg/files/9674841/download?download_frd=1&verifier=...",
        "size": 245100,
        "created_at": "2026-09-18T14:29:50Z",
        "updated_at": "2026-09-18T14:29:55Z"
      }
    ],
    "submission_comments": [
      {
        "id": 819201,
        "author_id": 48201,
        "author_name": "Teaching Assistant",
        "comment": "Well structured solution.",
        "created_at": "2026-09-19T08:15:00Z"
      }
    ]
  }
  ```

#### `GET /api/v1/courses/{course_id}/students/submissions`
**High-Efficiency Batch Submissions Endpoint**: Retrieves all student submissions across every assignment in a course in a single network round-trip. This eliminates the N+1 API call overhead of querying `/assignments/{id}/submissions/self` for each individual assignment.
- **Status**: `200 OK`
- **Query Parameters**:
  - `student_ids[]`: Pass `"self"` to retrieve only the current student's submissions across all assignments, or specific user IDs for teaching assistants.
  - `include[]`: Optional additional records:
    - `submission_comments`: Tutor feedback and student replies.
    - `rubric_assessment`: Detailed criteria scores.
    - `assignment`: Inlines the parent assignment configuration into each submission record.
- **Example Call**:
  ```http
  GET /api/v1/courses/93752/students/submissions?student_ids[]=self&include[]=submission_comments&include[]=assignment HTTP/1.1
  Host: canvas.nus.edu.sg
  Authorization: Bearer <CANVAS_API_TOKEN>
  ```
- **Output Schema**: Array of submission objects (one per assignment).

#### `POST /api/v1/courses/{course_id}/assignments/{assignment_id}/submissions`
Submits student work for an assignment. The required request body depends on `submission_types`:

1. **Online Text Submission**:
   - `Content-Type: application/json`
   ```json
   {
     "submission": {
       "submission_type": "online_text_entry",
       "body": "<p>Here is my written reflection...</p>"
     }
   }
   ```
2. **Online URL Submission (e.g. GitHub Repository, Google Doc)**:
   - `Content-Type: application/json`
   ```json
   {
     "submission": {
       "submission_type": "online_url",
       "url": "https://github.com/nus-cs2102/assignment-1-submission"
     }
   }
   ```
3. **File Upload Submission (The 3-Step Handshake)**:
   Canvas does not accept multipart file uploads directly to the submissions endpoint. Instead, follow Canvas's standard 3-step file upload workflow:
   - **Step 1 (Request Upload Token)**:
     ```http
     POST /api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/self/files HTTP/1.1
     Content-Type: application/json
     Authorization: Bearer <TOKEN>

     {
       "name": "homework1.pdf",
       "size": 1048576,
       "content_type": "application/pdf"
     }
     ```
     Canvas returns `upload_url` (typically an Amazon S3 presigned POST URL) and an `upload_params` dictionary.
   - **Step 2 (Upload Binary to Storage)**:
     Perform a `POST` request to `upload_url` containing the key-value pairs from `upload_params` followed by the raw binary `file` field as multipart/form-data. S3 responds with a `302 Found` or a JSON payload containing the created Canvas file record with an integer `id`.
   - **Step 3 (Finalize Submission)**:
     Call the assignments submission endpoint referencing the uploaded file ID:
     ```http
     POST /api/v1/courses/{course_id}/assignments/{assignment_id}/submissions HTTP/1.1
     Content-Type: application/json
     Authorization: Bearer <TOKEN>

     {
       "submission": {
         "submission_type": "online_upload",
         "file_ids": [9674841]
       }
     }
     ```

---

### Quizzes Endpoints

#### `GET /api/v1/courses/{course_id}/quizzes`
Lists classic Canvas quizzes.
- **Status**:
  - `200 OK`: Courses using classic quizzes (CS2102: 2 quizzes, CS3103: 3 quizzes).
  - `404 Not Found`: Courses where classic quizzes are disabled (CS2109S).
- **Verified Keys (51 fields)**: `id`, `title`, `description`, `quiz_type`, `time_limit`, `allowed_attempts`, `question_count`, `points_possible`, `due_at`, `published`, `html_url`.

#### `GET /api/v1/courses/{course_id}/quizzes/{quiz_id}`
Returns details for a single quiz.
- **Status**: `200 OK`

#### `GET /api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions`
Returns user attempts and scores for a quiz.
- **Status**: `200 OK`
- **Output Schema**: `{"quiz_submissions": [{"id": int, "attempt": int, "score": float, "workflow_state": "complete"}]}`

#### `GET /api/v1/courses/{course_id}/quizzes/{quiz_id}/questions`
- **Status**: `403 Forbidden` (`{"status": "unauthorized", "errors": [{"message": "user not authorised to perform that action"}]}`).
- **Reason**: Students are barred from accessing question banks before completing the quiz.

---

### Modules & Module Items Endpoints

#### `GET /api/v1/courses/{course_id}/modules`
Lists course modules.
- **Status**: `200 OK`
- **Query Parameters**:
  - `include[]`: `items`, `content_details`
- **Output Schema**:
  - `id`: `int`
  - `name`: `str` (e.g. `"Topic 0: Overview & Introduction"`)
  - `items_count`: `int`
  - `items`: Array of module items.

#### `GET /api/v1/courses/{course_id}/modules/{module_id}/items`
Retrieves items contained within a module.
- **Status**: `200 OK`
- **Output Schema**: Array of item objects:
  - `id`: `int`
  - `title`: `str`
  - `type`: `str` (`"File"`, `"Page"`, `"Assignment"`, `"Quiz"`, `"ExternalUrl"`)
  - `content_id`: `int`
  - `html_url`: `str`
  - `url`: `str` (API URL for the underlying resource)

#### `PUT /api/v1/courses/{course_id}/modules/{module_id}/items/{item_id}/done`
Marks a manual completion item as done for the student.
- **Status**: `200 OK`

---

### Discussion Topics & Thread Views

#### `GET /api/v1/courses/{course_id}/discussion_topics`
Lists discussion topics in a course.
- **Status**: `200 OK`
- **Output Schema**: Array of topics (`id`, `title`, `message`, `posted_at`, `last_reply_at`, `discussion_type`, `user_name`).

#### `GET /api/v1/courses/{course_id}/discussion_topics/{topic_id}/view`
Returns the complete threaded view of a discussion, including all student and instructor replies.
- **Status**: `200 OK`
- **Output Schema**:
  - `unread_entries`: `list[int]`
  - `participants`: `list[dict]` (`id`, `display_name`, `avatar_image_url`)
  - `view`: Nested tree of reply objects (`id`, `user_id`, `message`, `created_at`, `replies`).

#### `POST /api/v1/courses/{course_id}/discussion_topics/{topic_id}/entries`
Posts a response to a discussion topic.
- **Payload**: `{"message": "<p>My response...</p>"}`

---

### Pages & Wiki Content

#### `GET /api/v1/courses/{course_id}/pages`
Lists wiki pages in a course.
- **Status**: `200 OK`
- **Output Schema**: Array of page summaries (`url`, `title`, `created_at`, `updated_at`, `front_page`).

#### `GET /api/v1/courses/{course_id}/pages/{url_or_id}`
Retrieves full HTML content of a wiki page.
- **Status**: `200 OK`
- **Output Schema**: `url`, `title`, `body` (HTML), `editing_roles`, `published`, `updated_at`.

---

### Files & Folders Endpoints

#### `GET /api/v1/courses/{course_id}/files`
Lists uploaded files across the course.
- **Status**: `200 OK`
- **Output Schema**: Array of files:
  - `id`: `int`
  - `display_name`: `str`
  - `filename`: `str`
  - `content-type`: `str` (e.g. `"application/pdf"`)
  - `url`: `str` (Direct authenticated download URL)
  - `size`: `int` (bytes)

#### `GET /api/v1/courses/{course_id}/folders`
Lists folder hierarchies in course workbins.
- **Status**: `200 OK`

#### `GET /api/v1/folders/{folder_id}/files`
Retrieves files within a specific folder.
- **Status**: `200 OK`

#### `GET /api/v1/files/{file_id}/public_url`
Generates a temporary public redirect URL to download a file without authorization headers.
- **Status**: `200 OK`
- **Output Schema**: `{"public_url": "https://..."}`

---

### Enrollments, Roster & Sections

#### `GET /api/v1/courses/{course_id}/users`
Lists enrolled students, instructors, and teaching assistants.
- **Status**: `200 OK`

#### `GET /api/v1/courses/{course_id}/enrollments`
Lists enrollment records including course roles and section IDs.
- **Status**: `200 OK`

#### `GET /api/v1/courses/{course_id}/sections`
Lists tutorial and lab sections.
- **Status**: `200 OK`

#### `GET /api/v1/courses/{course_id}/grading_periods`
Returns academic grading terms.
- **Status**: `200 OK`

---

### Calendar Events Endpoints

#### `GET /api/v1/calendar_events`
Lists calendar entries across courses.
- **Status**: `200 OK`
- **Query Parameters**:
  - `context_codes[]`: `course_{id}`
  - `type`: `"event"` or `"assignment"`
  - `start_date`: ISO datetime
  - `end_date`: ISO datetime

---

### Course Navigation Tabs & LTI External Tools (Panopto / Zoom)

#### `GET /api/v1/courses/{course_id}/tabs`
Lists all left-hand navigation tabs configured for the course, including built-in Canvas tools and third-party LTI integrations.
- **Status**: `200 OK`
- **Output Schema**: Array of tab objects:
  ```json
  [
    {
      "id": "home",
      "html_url": "/courses/93752",
      "full_url": "https://canvas.nus.edu.sg/courses/93752",
      "position": 1,
      "visibility": "public",
      "label": "Home",
      "type": "internal"
    },
    {
      "id": "context_external_tool_128",
      "html_url": "/courses/93752/external_tools/128",
      "full_url": "https://canvas.nus.edu.sg/courses/93752/external_tools/128",
      "position": 12,
      "visibility": "public",
      "label": "Videos/Panopto",
      "type": "external",
      "url": "https://canvas.nus.edu.sg/api/v1/courses/93752/external_tools/sessionless_launch?id=128&launch_type=course_navigation"
    }
  ]
  ```

#### `GET /api/v1/courses/{course_id}/external_tools/sessionless_launch`
Generates a one-time authenticated LTI launch URL for an external tool (such as Panopto or Zoom) without requiring an interactive Canvas web login.
- **Status**: `200 OK`
- **Query Parameters**:
  - `id`: External tool identifier (`128` for Videos/Panopto, `124` for Zoom in NUS Canvas).
  - `launch_type`: `"course_navigation"`
- **Output Schema**:
  ```json
  {
    "id": 128,
    "name": "Videos/Panopto",
    "url": "https://canvas.nus.edu.sg/courses/93752/external_tools/sessionless_launch?session_token=...&verifier=..."
  }
  ```

---

### Lecture Videos & Panopto Integration Architecture

In NUS Canvas, lecture video hosting and playback is powered by **Panopto** via LTI (Learning Tools Interoperability) integration. Because Panopto is an external service (`mediaweb.ap.panopto.com`), video records are not stored as native Canvas database rows. Instead, there are two primary integration patterns:

#### 1. Course Panopto Folder Launch (Full Video Library)
Students access the full archive of lecture recordings for a course through the course navigation tab:
1. Client requests the sessionless launch URL:
   ```http
   GET /api/v1/courses/{course_id}/external_tools/sessionless_launch?id=128&launch_type=course_navigation
   ```
2. Canvas returns a signed one-time URL. When followed by a browser or HTTP client, Canvas renders an auto-submitting HTML form directed to Panopto's LTI gateway:
   - **LTI Gateway**: `https://mediaweb.ap.panopto.com/Panopto/LTI/LTI.aspx`
   - **Form Fields**: Signed OAuth 1.0 HMAC-SHA1 parameters including `context_id`, `custom_canvas_course_id`, `roles` (`"Learner"`), `lis_person_name_full`, and `lis_person_contact_email_primary`.
3. Panopto authenticates the student session and loads the course folder viewer (`https://mediaweb.ap.panopto.com/Panopto/Pages/Sessions/List.aspx#folderID=...`).

#### 2. Embedded Lecture Recordings in Modules & Pages
Instructors frequently embed individual lecture recordings directly into Canvas module items and wiki pages (e.g. `Week 1 - Lecture (Recorded)` in CS3103):
- Inspecting the page HTML (`GET /api/v1/courses/{course_id}/pages/{page_url}`) reveals an embedded LTI iframe:
  ```html
  <iframe class="lti-embed"
          style="width: 720px; height: 405px;"
          title="CS3103 Lecture on 14/08/2026 (Fri)"
          src="https://canvas.nus.edu.sg/courses/{course_id}/external_tools/retrieve?display=borderless&url=https%3A%2F%2Fmediaweb.ap.panopto.com%2FPanopto%2FLTI%2FLTI.aspx%3Fcustom_context_delivery%3D3e243340-8991-4e01-9582-b4a801587605"
          allowfullscreen="allowfullscreen">
  </iframe>
  ```
- **Extracting Panopto Delivery IDs**:
  - The parameter `custom_context_delivery` in the `src` URL contains Panopto's unique video **Delivery ID** (e.g. `3e243340-8991-4e01-9582-b4a801587605`).
  - **Direct Panopto Viewer URL**:
    `https://mediaweb.ap.panopto.com/Panopto/Pages/Viewer.aspx?id={DELIVERY_UUID}`
  - **Direct Video Delivery Metadata Endpoint**:
    `POST https://mediaweb.ap.panopto.com/Panopto/Pages/Viewer/DeliveryInfo.aspx` with payload `{"deliveryId": "{DELIVERY_UUID}", "responseType": "json"}`.

#### 3. Standard NUS Canvas LTI External Tools Directory
| Tool ID | Tool Name | Description / Target |
| :---: | :--- | :--- |
| `124` | **Zoom** | Live and scheduled Zoom lectures, tutorial meetings, and cloud recordings. |
| `128` | **Videos/Panopto** | Primary NUS lecture capture, webcasts, and recorded classroom sessions. |
| `131` | **Student Feedback** | Mid-term and end-of-semester module feedback surveys. |
| `135` | **Course Readings** | NUS Library e-reserves and recommended reading lists. |
| `145` | **Chat** | Real-time course room chat. |
| `207` | **Course Analytics** | Course engagement and access analytics. |
| `1706`| **Microsoft Education** | Microsoft Teams and Office 365 course collaboration. |

---

## 6. Known Upstream Quirks & Error Responses

| Scenario | HTTP Status | Upstream Behavior & Resolution |
| :--- | :---: | :--- |
| **Quizzes on non-quiz courses** | `404 Not Found` | Courses like CS2109S disable classic quizzes. `CanvasClient.get_quizzes()` catches HTTP 404 and safely returns `[]`. |
| **Course progress on un-gated modules** | `404 Not Found` | Returns 404 if no module completion requirements exist. `CanvasClient.get_course_progress()` catches 404 and returns `{}`. |
| **Quiz questions access** | `403 Forbidden` | Canvas prohibits students from downloading quiz question banks before attempts. |
| **Paging limit** | `200 OK` | Defaults to 10 items. Always append `per_page=100` for collections. |

---

## 7. Project Implementation Mapping

| Purpose | Canvas Endpoint | Implementation Reference |
| :--- | :--- | :--- |
| **Active Courses** | `GET /api/v1/courses` | [`CanvasClient.get_courses`](file:///Users/javier/Projects/daily-brief/src/daily_brief/canvas/api.py#L42) |
| **Announcements** | `GET /api/v1/announcements` | [`CanvasClient.get_announcements`](file:///Users/javier/Projects/daily-brief/src/daily_brief/canvas/api.py#L48) |
| **Assignments** | `GET /api/v1/courses/{id}/assignments` | [`CanvasClient.get_assignments`](file:///Users/javier/Projects/daily-brief/src/daily_brief/canvas/api.py#L60) |
| **Quizzes** | `GET /api/v1/courses/{id}/quizzes` | [`CanvasClient.get_quizzes`](file:///Users/javier/Projects/daily-brief/src/daily_brief/canvas/api.py#L72) |
| **Course Progress** | `GET /api/v1/courses/{id}/course_progress` | [`CanvasClient.get_course_progress`](file:///Users/javier/Projects/daily-brief/src/daily_brief/canvas/api.py#L86) |
| **Extractor: Announcements** | - | [`extract_announcements_data`](file:///Users/javier/Projects/daily-brief/src/daily_brief/canvas/api.py#L147) |
| **Extractor: Assignments** | - | [`extract_assignments_data`](file:///Users/javier/Projects/daily-brief/src/daily_brief/canvas/api.py#L173) |
| **Extractor: Quizzes** | - | [`extract_quizzes_data`](file:///Users/javier/Projects/daily-brief/src/daily_brief/canvas/api.py#L236) |
| **Batch Submissions** | `GET /courses/{id}/students/submissions` | Documented for future high-efficiency ingestion. |

---

## 8. Standalone Reference Client Implementation (Python)

Below is a complete, self-contained Python reference client (`CanvasAPIClient`) built with standard `requests`. It implements bearer authorization, RFC 5988 `Link` header pagination traversal, rate-limit awareness, error handling, and high-level methods for all key Canvas LMS operations.

```python
import re
import time
from typing import Any, Generator, Optional
import requests


class CanvasAPIError(Exception):
    """Base exception for Canvas API errors."""

    def __init__(self, status_code: int, message: str, errors: Optional[list] = None):
        super().__init__(f"Canvas API HTTP {status_code}: {message}")
        self.status_code = status_code
        self.errors = errors or []


class CanvasAPIClient:
    """Production-ready standalone client for Canvas LMS REST API."""

    def __init__(self, base_url: str, api_token: str, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_token.strip()}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
    ) -> requests.Response:
        url = f"{self.base_url}{path}" if path.startswith("/") else path
        resp = self.session.request(
            method,
            url,
            params=params,
            json=json_data,
            timeout=self.timeout,
        )

        # Rate limit monitoring (leaky bucket)
        remaining = resp.headers.get("X-Rate-Limit-Remaining")
        if remaining and float(remaining) < 50.0:
            time.sleep(1.0)

        if resp.status_code >= 400:
            try:
                error_body = resp.json()
                msg = error_body.get("message") or error_body.get("status") or resp.text
                errs = error_body.get("errors", [])
            except Exception:
                msg = resp.text
                errs = []
            raise CanvasAPIError(resp.status_code, msg, errs)

        return resp

    def _paginate(
        self,
        path: str,
        params: Optional[dict[str, Any]] = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Automatically walks RFC 5988 Link headers to yield all items across all pages."""
        next_url: Optional[str] = f"{self.base_url}{path}"
        current_params = dict(params or {})
        current_params.setdefault("per_page", 100)

        while next_url:
            resp = self._request("GET", next_url, params=current_params)
            data = resp.json()
            if isinstance(data, list):
                for item in data:
                    yield item
            else:
                yield data
                break

            # Parse Link header for rel="next"
            link_header = resp.headers.get("Link", "")
            match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
            if match:
                next_url = match.group(1)
                current_params = {}  # Next URL already contains query parameters
            else:
                next_url = None

    # --- Profile & Identity ---
    def get_user_self(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/users/self").json()

    # --- Courses ---
    def get_courses(self, enrollment_state: str = "active") -> list[dict[str, Any]]:
        params = {
            "enrollment_state": enrollment_state,
            "include[]": ["term", "total_scores"],
        }
        return list(self._paginate("/api/v1/courses", params=params))

    def get_course(self, course_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/courses/{course_id}").json()

    # --- Announcements ---
    def get_announcements(
        self,
        context_codes: list[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"context_codes[]": context_codes}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return list(self._paginate("/api/v1/announcements", params=params))

    # --- Assignments & Submissions ---
    def get_assignments(self, course_id: int) -> list[dict[str, Any]]:
        params = {"include[]": ["submission", "assignment_overrides"]}
        return list(self._paginate(f"/api/v1/courses/{course_id}/assignments", params=params))

    def get_batch_submissions(self, course_id: int, student_ids: Optional[list[str]] = None) -> list[dict[str, Any]]:
        params = {
            "student_ids[]": student_ids or ["self"],
            "include[]": ["submission_comments", "assignment", "rubric_assessment"],
        }
        return list(self._paginate(f"/api/v1/courses/{course_id}/students/submissions", params=params))

    def get_assignment_submission_self(self, course_id: int, assignment_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/self").json()

    def submit_text_assignment(self, course_id: int, assignment_id: int, body_html: str) -> dict[str, Any]:
        payload = {
            "submission": {
                "submission_type": "online_text_entry",
                "body": body_html,
            }
        }
        return self._request("POST", f"/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions", json_data=payload).json()

    def submit_url_assignment(self, course_id: int, assignment_id: int, submission_url: str) -> dict[str, Any]:
        payload = {
            "submission": {
                "submission_type": "online_url",
                "url": submission_url,
            }
        }
        return self._request("POST", f"/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions", json_data=payload).json()

    # --- Quizzes ---
    def get_quizzes(self, course_id: int) -> list[dict[str, Any]]:
        try:
            return list(self._paginate(f"/api/v1/courses/{course_id}/quizzes"))
        except CanvasAPIError as exc:
            if exc.status_code == 404:
                return []
            raise

    # --- Modules ---
    def get_modules(self, course_id: int) -> list[dict[str, Any]]:
        params = {"include[]": ["items", "content_details"]}
        return list(self._paginate(f"/api/v1/courses/{course_id}/modules", params=params))

    # --- Discussions ---
    def get_discussion_topics(self, course_id: int) -> list[dict[str, Any]]:
        return list(self._paginate(f"/api/v1/courses/{course_id}/discussion_topics"))

    def get_discussion_view(self, course_id: int, topic_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/view").json()

    # --- Files & Folders ---
    def get_files(self, course_id: int) -> list[dict[str, Any]]:
        return list(self._paginate(f"/api/v1/courses/{course_id}/files"))

    # --- Navigation Tabs & Panopto Launch ---
    def get_tabs(self, course_id: int) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/courses/{course_id}/tabs").json()

    def get_panopto_launch_url(self, course_id: int) -> str:
        params = {"id": 128, "launch_type": "course_navigation"}
        data = self._request("GET", f"/api/v1/courses/{course_id}/external_tools/sessionless_launch", params=params).json()
        return data["url"]
```

---

## 9. Quick Reference cURL Commands

Replace `<TOKEN>` and `<BASE>` with your Canvas API token and domain (`https://canvas.nus.edu.sg`):

```bash
# 1. Verify Authentication & Identity
curl -H "Authorization: Bearer <TOKEN>" "<BASE>/api/v1/users/self"

# 2. List Active Courses
curl -H "Authorization: Bearer <TOKEN>" \
  "<BASE>/api/v1/courses?enrollment_state=active&per_page=100"

# 3. Fetch Course Announcements (Multi-course query)
curl -H "Authorization: Bearer <TOKEN>" \
  "<BASE>/api/v1/announcements?context_codes[]=course_93752&context_codes[]=course_93790"

# 4. Fetch Course Assignments with Overrides
curl -H "Authorization: Bearer <TOKEN>" \
  "<BASE>/api/v1/courses/93752/assignments?include[]=submission&include[]=assignment_overrides&per_page=100"

# 5. Fetch All Submissions in a Course (High-efficiency Batch)
curl -H "Authorization: Bearer <TOKEN>" \
  "<BASE>/api/v1/courses/93752/students/submissions?student_ids[]=self&include[]=submission_comments"

# 6. Fetch Full Discussion Thread Tree
curl -H "Authorization: Bearer <TOKEN>" \
  "<BASE>/api/v1/courses/93752/discussion_topics/488198/view"

# 7. Generate Authenticated Panopto Launch URL
curl -H "Authorization: Bearer <TOKEN>" \
  "<BASE>/api/v1/courses/93752/external_tools/sessionless_launch?id=128&launch_type=course_navigation"
```
