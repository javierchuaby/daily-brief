# Daily Brief Automation

An automated daily brief system that aggregates data from **Canvas** (LMS) and **Coursemology**, synthesizes it using **Google Gemini AI**, and emails you a structured morning brief.

### Tech Stack
- **Python 3.10+** (with `pydantic` & `google-genai`)
- **APIs:** Canvas LMS, Coursemology, Google Gemini (3.1-flash-lite)
- **Email:** Gmail SMTP

<br>

## 🚀 Quick Start

### 1. Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration
Copy `.env.example` to `.env` and fill in your credentials:

| Credential | Description |
|------------|-------------|
| `CANVAS_API_TOKEN` | Generate at LMS Profile → Approved Integrations |
| `COURSEMOLOGY_*` | Your Coursemology login credentials and course ID |
| `GEMINI_API_KEY` | Generate at Google AI Studio |
| `GMAIL_*` | Your Gmail address and an App Password (not your main password) |
| `CANVAS_COURSES` | Format: `CODE:ID,CODE2:ID2` (e.g., `CS2102:93752`) |

### 3. Run
```bash
# Test without sending an email
python3 -m daily_brief --dry-run

# Full run
python3 -m daily_brief
```
Data is saved to `data/YYYY-MM-DD/` (auto-cleaned after 3 days).

<br>

## ⏰ Automation (Cron)
To run this automatically every morning at 7:30 AM, add this to your crontab (`crontab -e`):
```bash
30 7 * * * cd /path/to/daily-brief && source venv/bin/activate && python3 -m daily_brief >> logs/cron.log 2>&1
```
*macOS Users:* Ensure `cron`, `Terminal`, or `iTerm2` has "Full Disk Access" in System Settings.

<br>

## 🔧 Customization
To change how the AI formats your email, edit the `DailyBriefSchema` and prompt inside `src/daily_brief/services/gemini_service.py`.

<br>

## 🙏 Acknowledgments

- Canvas API documentation: https://canvas.instructure.com/doc/api/
- Coursemology Python client: https://github.com/rizkiarm/coursemology-py

<br>

## ❓ Questions?

Open an issue or contact me at javierchua.dev@gmail.com.
