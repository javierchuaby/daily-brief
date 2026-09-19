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

## ⏰ Automation (macOS launchd)
To run this automatically every morning at 7:30 AM, macOS `launchd` is configured.
Unlike `cron`, if your Mac is asleep at 7:30 AM, `launchd` is smart enough to run the brief immediately when you wake the computer up!

The configuration is located at: `~/Library/LaunchAgents/com.yourname.dailybrief.plist`

**To manage the background job:**
```bash
# To stop/disable the daily automation
launchctl unload ~/Library/LaunchAgents/com.yourname.dailybrief.plist

# To start/enable the daily automation
launchctl load ~/Library/LaunchAgents/com.yourname.dailybrief.plist
```
*Note:* Ensure `Terminal` or `iTerm2` has "Full Disk Access" in macOS System Settings so it can read your credentials.

<br>

## 🔧 Customization
To change how the AI formats your email, edit the `DailyBriefSchema` and prompt inside `src/daily_brief/services/gemini_service.py`.

<br>

## 📚 API Documentation & Probing

Complete technical documentation verified against live upstream services:
- **[Canvas LMS API Documentation](docs/api/canvas.md)**: Endpoints, Bearer authentication, pagination, verified response structures, and quirks.
- **[Coursemology API Documentation](docs/api/coursemology.md)**: Endpoints, session CSRF authentication, student vs staff RBAC permissions, and `coursemology-py` SDK compatibility.
- **[API Verification Index](docs/api/README.md)**: Full endpoint index and probe methodology.

To run the live endpoint verification suite:
```bash
python scripts/probe_endpoints.py
```

<br>

## 🙏 Acknowledgments

- Canvas API documentation: https://canvas.instructure.com/doc/api/
- Coursemology Python client: https://github.com/rizkiarm/coursemology-py

<br>

## ❓ Questions?

Open an issue or contact me at javierchua.dev@gmail.com.
