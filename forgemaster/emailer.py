"""
FORGEMASTER — Email Sender

Sends daily reports via Gmail SMTP.
No MCP dependency. Direct SMTP with app password.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "pedro.paiva.mestre@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
REPORT_TO = os.getenv("REPORT_TO", "pedro.paiva.mestre@gmail.com")


def send_email(subject: str, body: str, to: str = "") -> bool:
    """Send an email via Gmail SMTP."""
    if not GMAIL_APP_PASSWORD:
        print("EMAIL: No app password set. Report saved to file only.", flush=True)
        return False

    to = to or REPORT_TO

    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print(f"EMAIL: Sent to {to}", flush=True)
        return True
    except Exception as e:
        print(f"EMAIL: Failed to send: {e}", flush=True)
        return False


if __name__ == "__main__":
    # Test
    sent = send_email(
        subject="Forgemaster Test Email",
        body="If you received this, the email sender works.\n\n- Forgemaster",
    )
    print(f"Sent: {sent}")
