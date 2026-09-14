"""Gmail SMTP email sender with robust error handling and multipart support."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from daily_brief import get_env_var
from daily_brief.interfaces import EmailSender
from daily_brief.utils import markdown_to_html

logger = logging.getLogger(__name__)


class GmailSender(EmailSender):
    """Email sender using Gmail SMTP with multipart fallback and timeouts."""

    def __init__(self, timeout_seconds: int = 15) -> None:
        self.timeout = timeout_seconds

    def _wrap_html(self, raw_html: str) -> str:
        """Wrap markdown-generated HTML in styled email boilerplate."""
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        line-height: 1.5;
        color: #1f2328;
        max-width: 680px;
        margin: 0 auto;
        padding: 20px;
    }}
    h1 {{ font-size: 20px; border-bottom: 1px solid #d0d7de; padding-bottom: 8px; color: #0969da; }}
    h2 {{ font-size: 16px; margin-top: 24px; margin-bottom: 8px; color: #24292f; border-bottom: 1px solid #eaeef2; }}
    h3 {{ font-size: 14px; margin-top: 16px; margin-bottom: 6px; color: #57606a; }}
    ul {{ padding-left: 20px; margin-top: 4px; }}
    li {{ margin-bottom: 6px; font-size: 13px; }}
    code {{ background-color: #f6f8fa; padding: 2px 4px; border-radius: 4px; font-size: 12px; }}
</style>
</head>
<body>
{raw_html}
</body>
</html>"""

    def send(self, to: str, subject: str, content: str) -> bool:
        """Send email via Gmail SMTP.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            content: Raw Markdown email body.

        Returns:
            True if delivered to SMTP server, False otherwise.
        """
        sender = get_env_var("GMAIL_SENDER")
        password = get_env_var("GMAIL_APP_PASSWORD")

        # Build multipart container
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to

        # Plain text fallback (must be attached first)
        part_plain = MIMEText(content, "plain", "utf-8")
        msg.attach(part_plain)

        # Styled HTML part (must be attached last so capable clients render it)
        raw_html = markdown_to_html(content)
        full_html = self._wrap_html(raw_html)
        part_html = MIMEText(full_html, "html", "utf-8")
        msg.attach(part_html)

        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=self.timeout) as smtp:
                smtp.starttls()
                smtp.login(sender, password)
                smtp.send_message(msg)

            logger.info("Email sent successfully to %s", to)
            return True

        except smtplib.SMTPAuthenticationError as exc:
            logger.error("SMTP authentication failed. Verify app password: %s", exc)
            return False
        except smtplib.SMTPConnectError as exc:
            logger.error("Failed to connect to smtp.gmail.com: %s", exc)
            return False
        except (smtplib.SMTPException, TimeoutError) as exc:
            logger.error("SMTP delivery error occurred: %s", exc)
            return False
        except Exception as exc:
            logger.error("Unexpected error during email dispatch: %s", exc)
            return False
