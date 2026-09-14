# Daily Brief Automation

Automated daily brief system that aggregates data from:
- **Canvas** (LMS) - Announcements, assignments, quizzes
- **Coursemology** - Assessments, announcements

The system uses OpenCode AI to generate a concise morning brief and emails it daily.

---

## 📋 Prerequisites

- Python 3.10+
- pip package manager
- **OpenCode CLI**
- Canvas account
- Coursemology account
- Gmail account (with App Password for SMTP)

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd daily-brief

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip3 install -r requirements.txt
```

### 2. Configure Credentials

```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env with your credentials
vim .env
```

**Required credentials:**

| Credential | Where to Get It |
|------------|-----------------|
| Canvas API Token | Your LMS profile → "Approved Integrations" → "New Access Token" |
| Coursemology Username/Password | Your account credentials |
| GMAIL_SENDER | Your Gmail address |
| GMAIL_APP_PASSWORD | https://myaccount.google.com/apppasswords (generate app password) |

**Important:** Never commit `.env` to git!

### 3. Test Automation

```bash
# Dry run (test without sending email)
python3 -m daily_brief --dry-run

# Full run (sends email)
python3 -m daily_brief
```

### 4. Set Up Cron (Daily Automation)

```bash
# Edit crontab
crontab -e
```

Add this line (runs at 7:30 AM every day):

```
30 7 * * * cd /path/to/daily-brief && source venv/bin/activate && python3 -m daily_brief >> logs/$(date +\%Y-\%m-\%d).log 2>&1
```

**macOS Note:** You must grant `cron`, `Terminal`, or `iTerm2` "Full Disk Access" in System Settings → Privacy & Security. Without this, the script will silently fail to read `.env` or execute the OpenCode CLI.

---

## 📁 Output Structure

```
./data/
├── 2026-09-13/              # Date-stamped folder
│   ├── canvas-*.md          # Course markdown files
│   ├── coursemology.md      # Coursemology data
│   ├── fine_grained.json    # Structured data for AI synthesis
│   ├── debug_prompt.txt     # AI prompt sent to OpenCode
│   └── debug_raw_output.md  # Raw AI output before formatting
└── latest/ → 2026-09-13     # Symlink to most recent
```

---

## 📧 Email Format

The AI generates the brief with a rigid schema:

```markdown
# Daily Brief - YYYY-MM-DD

## URGENT (Today/Tomorrow)
- [Source] Title (Due: YYYY-MM-DD): Key action or requirement

## IMPORTANT (This Week)
- [Source] Title (Due: YYYY-MM-DD): Key action or requirement

## INFO (For Awareness)
### Recent Updates & Announcements
- [Source] Title (Posted: YYYY-MM-DD): 1-sentence action item or takeaway

### Later Deadlines
- [Source] Title (Due: YYYY-MM-DD)
```

**Notes:**
- If a section has no qualifying items, it outputs: `- None`
- No conversational language, greetings, or sign-offs
- All dates use YYYY-MM-DD format

---

## 🔧 Configuration Options

### Change Email Recipient

In `.env`:

```bash
RECIPIENT_EMAIL=your-email@example.com
```

### Change Send Time

In crontab:

```bash
# Every morning at 7:30 AM
30 7 * * * python3 -m daily_brief

# Every morning at 8:00 AM
0 8 * * * python3 -m daily_brief
```

---

## 🐛 Troubleshooting

### "Invalid Canvas API token"

1. Go to your LMS profile
2. Click "New Access Token"
3. Update `.env` with new token

### "Failed to connect to Coursemology"

1. Check username/password in `.env`
2. Test login manually at your Coursemology instance
3. Check `coursemology-py` is installed: `pip3 show coursemology-py`

### "Failed to send email"

1. Check Gmail app password in `.env`
2. Generate app password at https://myaccount.google.com/apppasswords
3. Verify `GMAIL_SENDER` is correct

### "OpenCode not found"

1. Install opencode CLI
2. Pull the model: `opencode pull soclaas/qwen3.8:27b`
3. Verify installation: `opencode run --help`

---

## 🔐 Security Notes

⚠️ **IMPORTANT:**

1. **Never commit `.env`** to git (it's gitignored)
2. **Use environment variables** for sensitive data
3. **Use Gmail app password**, not regular password
4. **Rotate credentials** periodically

---

## 📝 Customization

### Change AI Brief Structure

Edit `src/daily_brief/synthesizer.py`:

The AI's behavior is controlled by the `system_prompt` in the `synthesize_brief_with_opencode()` function. To customize the output:

1. **Modify the system prompt template** (lines 48-88): Change section headers, classification rules, or output format
2. **Adjust temporal anchors** (lines 37-41): Modify how "Today", "Tomorrow", and "This Week" are calculated
3. **Update classification rules** (lines 57-68): Add new rules for what constitutes URGENT, IMPORTANT, or INFO items

**Example changes:**
- Add a new section: Insert `## NEW SECTION` in the prompt's OUTPUT FORMAT
- Change date logic: Modify the `datetime.timedelta` calculations for past_cutoff
- Adjust item counts: Update truncation logic in the main processing functions

### Add More Canvas Courses

In `.env`:

```bash
CANVAS_COURSES=COURSE1:12345,COURSE2:12346,COURSE3:12347
```


---

## 🙏 Acknowledgments

- Canvas API documentation: https://canvas.instructure.com/doc/api/
- Coursemology Python client: https://github.com/rizkiarm/coursemology-py

---

## ❓ Questions?

Open an issue or contact me at javierchua.dev@gmail.com.
