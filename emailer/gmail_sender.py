# emailer/gmail_sender.py

import os
import smtplib
import mimetypes
from email.message import EmailMessage

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT   = 587

def send_application(to_address: str, subject: str, body_text: str, attachment_path: str = None):
    """
    Sends an email via Gmail SMTP with optional attachment.
    - to_address: recipient email
    - subject: email subject
    - body_text: plain-text body
    - attachment_path: full path to a file to attach (e.g. your resume PDF)
    """
    # Read credentials at call time
    gmail_user     = os.getenv("GMAIL_USER")
    gmail_app_pass = os.getenv("GMAIL_APP_PASS")
    if not gmail_user or not gmail_app_pass:
        raise RuntimeError("Set GMAIL_USER and GMAIL_APP_PASS in your .env")

    # Create the message
    msg = EmailMessage()
    msg["From"]    = gmail_user
    msg["To"]      = to_address
    msg["Subject"] = subject
    msg.set_content(body_text)

    # Attach a file if provided
    if attachment_path:
        guessed, _ = mimetypes.guess_type(attachment_path)
        if guessed:
            maintype, subtype = guessed.split("/", 1)
        else:
            maintype, subtype = ("application", "octet-stream")

        with open(attachment_path, "rb") as f:
            data = f.read()
        msg.add_attachment(
            data,
            maintype=maintype,
            subtype=subtype,
            filename=os.path.basename(attachment_path)
        )

    # Send via Gmail SMTP
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(gmail_user, gmail_app_pass)
        smtp.send_message(msg)

