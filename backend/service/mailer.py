"""SMTP delivery. An unconfigured SMTP server is an error, never a fake success."""
import os
import smtplib
import ssl
from email.message import EmailMessage

from fastapi import HTTPException


def send_email(to_address: str, subject: str, body: str):
    host = os.environ.get("GDAS_SMTP_HOST")
    sender = os.environ.get("GDAS_SMTP_FROM")
    if not host or not sender:
        raise HTTPException(503, "Email delivery is not configured. Set GDAS_SMTP_HOST and GDAS_SMTP_FROM.")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(host, int(os.environ.get("GDAS_SMTP_PORT", "587")), timeout=10) as client:
            if os.environ.get("GDAS_SMTP_STARTTLS", "1") == "1":
                client.starttls(context=ssl.create_default_context())
            username = os.environ.get("GDAS_SMTP_USERNAME")
            if username:
                client.login(username, os.environ.get("GDAS_SMTP_PASSWORD", ""))
            client.send_message(message)
    except (OSError, smtplib.SMTPException, ValueError) as exc:
        raise HTTPException(503, "Email delivery failed; check the SMTP settings") from exc
