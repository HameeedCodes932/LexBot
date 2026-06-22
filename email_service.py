import smtplib
from email.message import EmailMessage
from typing import Optional

def send_email(smtp_host: str, smtp_port: int, smtp_user: str, smtp_pass: str, *,
               to_address: str, subject: str, body: str, use_tls: bool = True) -> None:
    """Send a simple email via SMTP.

    Parameters
    ----------
    smtp_host: str
        SMTP server hostname.
    smtp_port: int
        SMTP server port.
    smtp_user: str
        Username for authentication.
    smtp_pass: str
        Password for authentication.
    to_address: str
        Recipient email address.
    subject: str
        Email subject.
    body: str
        Plain‑text email body.
    use_tls: bool, default True
        Whether to start TLS after connecting (common for port 587).
    """
    msg = EmailMessage()
    msg["From"] = smtp_user
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)

    if use_tls:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
    else:
        server = smtplib.SMTP_SSL(smtp_host, smtp_port)
    try:
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
    finally:
        server.quit()
