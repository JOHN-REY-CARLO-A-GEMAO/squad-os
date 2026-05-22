"""
EmailTool — send and receive emails via SMTP/IMAP.

Requires:
- EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_USER, EMAIL_PASSWORD for sending
- EMAIL_IMAP_HOST, EMAIL_IMAP_PORT for receiving
"""
import asyncio
import json
import os
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from squad_os.tools.base import BaseTool


class EmailSendTool(BaseTool):
    name = "send_email"
    description = (
        "Send an email via SMTP. Requires EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, "
        "EMAIL_USER, and EMAIL_PASSWORD environment variables. "
        "Supports plain text and HTML content."
    )
    parameters = {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient email address"
            },
            "subject": {
                "type": "string",
                "description": "Email subject line"
            },
            "body": {
                "type": "string",
                "description": "Email body text"
            },
            "html": {
                "type": "string",
                "description": "HTML version of email body (optional)"
            },
            "cc": {
                "type": "string",
                "description": "CC recipients (comma-separated, optional)"
            }
        },
        "required": ["to", "subject", "body"]
    }

    def __init__(self):
        self.smtp_host = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
        self.user = os.getenv("EMAIL_USER")
        self.password = os.getenv("EMAIL_PASSWORD")

    async def execute(
        self,
        to: str,
        subject: str,
        body: str,
        html: Optional[str] = None,
        cc: Optional[str] = None
    ) -> str:
        if not self.user or not self.password:
            return "Error: EMAIL_USER and EMAIL_PASSWORD not set in environment."

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.user
            msg["To"] = to
            msg["Subject"] = subject
            
            if cc:
                msg["Cc"] = cc
            
            msg.attach(MIMEText(body, "plain"))
            if html:
                msg.attach(MIMEText(html, "html"))

            recipients = [to]
            if cc:
                recipients.extend(cc.split(","))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.user, recipients, msg.as_string())
            
            return f"Email sent to {to} (subject: {subject})."
        except Exception as e:
            return f"Error sending email: {e}"


class EmailReceiveTool(BaseTool):
    name = "receive_email"
    description = (
        "Poll for new emails via IMAP. Requires EMAIL_IMAP_HOST, EMAIL_IMAP_PORT, "
        "EMAIL_USER, and EMAIL_PASSWORD environment variables. "
        "Returns recent unread emails with sender, subject, and body preview."
    )
    parameters = {
        "type": "object",
        "properties": {
            "folder": {
                "type": "string",
                "description": "IMAP folder to check (default: INBOX)"
            },
            "limit": {
                "type": "integer",
                "description": "Max number of emails to retrieve (default 10)"
            },
            "mark_read": {
                "type": "boolean",
                "description": "Mark emails as read after fetching (default: false)"
            }
        },
        "required": []
    }

    def __init__(self):
        self.imap_host = os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com")
        self.imap_port = int(os.getenv("EMAIL_IMAP_PORT", "993"))
        self.user = os.getenv("EMAIL_USER")
        self.password = os.getenv("EMAIL_PASSWORD")

    async def execute(
        self,
        folder: str = "INBOX",
        limit: int = 10,
        mark_read: bool = False
    ) -> str:
        if not self.user or not self.password:
            return "Error: EMAIL_USER and EMAIL_PASSWORD not set in environment."

        try:
            with imaplib.IMAP4_SSL(self.imap_host, self.imap_port) as mail:
                mail.login(self.user, self.password)
                mail.select(folder)
                
                status, messages = mail.search(None, "UNSEEN")
                if status != "OK" or not messages[0]:
                    return "No unread emails."
                
                email_ids = messages[0].split()
                email_ids = email_ids[-limit:]  # Get most recent
                
                emails = []
                for eid in email_ids:
                    status, msg_data = mail.fetch(eid, "(RFC822)")
                    if status == "OK":
                        msg = email.message_from_bytes(msg_data[0][1])
                        
                        # Extract body
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                        
                        emails.append({
                            "from": msg.get("From", "Unknown"),
                            "subject": msg.get("Subject", "(No Subject)"),
                            "date": msg.get("Date", ""),
                            "body_preview": body[:200] + ("..." if len(body) > 200 else "")
                        })
                        
                        if mark_read:
                            mail.store(eid, "+FLAGS", "\\Seen")
                
                return json.dumps(emails, indent=2)
        except Exception as e:
            return f"Error receiving emails: {e}"
