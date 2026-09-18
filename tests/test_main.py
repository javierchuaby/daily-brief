"""Tests for daily_brief.main module."""


class TestMainFunctions:
    """Test main automation functions."""

    def test_generate_brief_no_files(self, tmp_path):
        """Test generate_brief with no course files."""
        from daily_brief.main import generate_brief

        brief = generate_brief(tmp_path)

        assert "# Daily Brief" in brief
        assert "No urgent deadlines found." in brief
        assert "No new course updates." in brief
        assert "No upcoming deadlines." in brief

    def test_generate_brief_with_canvas_file(self, tmp_path):
        """Test generate_brief with Canvas course files."""
        from daily_brief.main import generate_brief

        # Create a canvas course file with an announcement and assignment
        canvas_file = tmp_path / "canvas-cs2102.md"
        canvas_file.write_text("""# CS2102

## Announcements
- **Welcome** (2026-09-13)
  Welcome to the course!

## Assignments
- **Assignment 1**
  Due: 2026-09-14 (in 1 days) | Points: 100 | Submissions: 0
""")

        brief = generate_brief(tmp_path)

        assert "CS2102" in brief
        assert "Assignment 1" in brief
        assert "Tomorrow" in brief

    def test_generate_brief_with_coursemology_file(self, tmp_path):
        """Test generate_brief with Coursemology file."""
        from daily_brief.main import generate_brief

        coursemology_file = tmp_path / "coursemology.md"
        coursemology_file.write_text("""# Coursemology - Course 123

## Announcements
- **New Assignment** (2026-09-13)

## Assessments & Quizzes
- **Problem Set 1**
  Due: 2026-09-15 (in 2 days)
""")

        brief = generate_brief(tmp_path)

        assert "Coursemology" in brief
        assert "Problem Set 1" in brief

    def test_generate_brief_urgent_deadlines(self, tmp_path):
        """Test urgent deadline extraction."""
        from daily_brief.main import generate_brief

        canvas_file = tmp_path / "canvas-cs2107.md"
        canvas_file.write_text("""# CS2107

## Assignments
- **Homework 1**
  Due: Today | Points: 50
- **Homework 2**
  Due: in 1 days | Points: 50
""")

        brief = generate_brief(tmp_path)

        assert "Today" in brief
        assert "Tomorrow" in brief
        assert "Homework 1" in brief
        assert "Homework 2" in brief

    def test_generate_brief_truncates_urgent_items(self, tmp_path):
        """Test that urgent items are truncated to 10."""
        from daily_brief.main import generate_brief

        # Create 15 canvas files
        for i in range(15):
            canvas_file = tmp_path / f"canvas-course{i:02d}.md"
            canvas_file.write_text(f"""# Course {i}
## Assignments
- **Assignment {i}**
  Due: Today | Points: 100
""")

        brief = generate_brief(tmp_path)

        # Count urgent items
        urgent_section = brief.split("## 🚨 Urgent Deadlines")[1].split("## 📚")[0]
        urgent_count = urgent_section.count("- **")

        assert urgent_count <= 10

    def test_generate_brief_truncates_upcoming_items(self, tmp_path):
        """Test that upcoming items are truncated to 20."""
        from daily_brief.main import generate_brief

        # Create 25 canvas files
        for i in range(25):
            canvas_file = tmp_path / f"canvas-course{i:02d}.md"
            canvas_file.write_text(f"""# Course {i}
## Assignments
- **Assignment {i}**
  Due: in 3 days | Points: 100
""")

        brief = generate_brief(tmp_path)

        # Count upcoming items
        upcoming_section = brief.split("## 📅 Upcoming Deadlines")[1]
        upcoming_count = upcoming_section.count("- **")

        assert upcoming_count <= 20


class TestFetchCanvasDataExtraction:
    """Test Canvas data extraction functions."""

    def test_format_announcement(self):
        """Test announcement formatting."""
        from daily_brief.canvas.api import format_announcement

        announcement = {
            "title": "Midterm Exam",
            "message": "The midterm exam will be held next week.",
            "posted_at": "2026-09-10T10:00:00Z",
        }

        formatted = format_announcement(announcement)
        assert "Midterm Exam" in formatted
        assert "2026-09-10" in formatted

    def test_extract_announcements_data(self):
        """Test announcements data extraction."""
        from daily_brief.canvas.api import extract_announcements_data

        from datetime import datetime, timedelta, timezone
        recent = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT10:00:00Z")
        announcements = [
            {
                "id": 1,
                "title": "Announcement 1",
                "message": "Content 1",
                "posted_at": recent,
                "is_pinned": True,
                "created_at": recent,
                "context_code": "course_123",
            }
        ]

        data = extract_announcements_data(announcements)

        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["title"] == "Announcement 1"
        assert data[0]["is_pinned"] is True

    def test_extract_assignments_data(self):
        """Test assignments data extraction."""
        from daily_brief.canvas.api import extract_assignments_data

        assignments = [
            {
                "id": 1,
                "name": "Assignment 1",
                "due_at": "2026-09-15T23:59:59Z",
                "points_possible": 100,
                "grading_type": "points",
                "published": True,
                "submissions_count": 5,
                "submission_types": ["online_upload"],
                "lock_at": "2026-09-16T00:00:00Z",
                "unlock_at": "2026-09-01T00:00:00Z",
            }
        ]

        data = extract_assignments_data(assignments)

        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Assignment 1"
        assert data[0]["points_possible"] == 100

    def test_extract_quizzes_data(self):
        """Test quizzes data extraction."""
        from daily_brief.canvas.api import extract_quizzes_data

        quizzes = [
            {
                "id": 1,
                "title": "Quiz 1",
                "due_at": "2026-09-16T23:59:59Z",
                "question_count": 10,
                "time_limit": 30,
                "allowed_attempts": 3,
                "quiz_type": "quiz",
                "published": True,
                "lock_at": "2026-09-17T00:00:00Z",
                "unlock_at": "2026-09-01T00:00:00Z",
            }
        ]

        data = extract_quizzes_data(quizzes)

        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["title"] == "Quiz 1"
        assert data[0]["question_count"] == 10
