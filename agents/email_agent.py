"""
Agent: email_agent
------------------
Connects via IMAP/SMTP to read and send emails.
Allows the Swarm to monitor an inbox, summarize threads, and draft replies autonomously.
"""

import os
import smtplib
import imaplib
import email
from email.message import EmailMessage

DESCRIPTION = (
    "The Communicator Agent (Email). Use this to read the user's inbox, search for specific emails, "
    "or send outgoing emails. It requires SMTP/IMAP credentials in the .env file."
)

PARAMETERS = {
    "action": {
        "type": "string",
        "required": True,
        "description": "Must be one of: 'read_inbox', 'send_email'.",
    },
    "to_address": {
        "type": "string",
        "required": False,
        "description": "The recipient email address (required for send_email).",
    },
    "subject": {
        "type": "string",
        "required": False,
        "description": "The subject line of the email (required for send_email).",
    },
    "body": {
        "type": "string",
        "required": False,
        "description": "The body content of the email.",
    },
    "query": {
        "type": "string",
        "required": False,
        "description": "IMAP search query, e.g. 'UNSEEN' or 'FROM \"example@test.com\"'. Defaults to 'UNSEEN' for read_inbox.",
    },
    "limit": {
        "type": "integer",
        "required": False,
        "description": "Maximum number of emails to fetch (default: 5).",
    }
}

def email_agent(
    action: str, 
    to_address: str = "", 
    subject: str = "", 
    body: str = "", 
    query: str = "UNSEEN",
    limit: int = 5
) -> dict:
    """Interacts with email using IMAP/SMTP."""
    action = action.lower().strip()
    
    email_user = os.environ.get("EMAIL_USER")
    email_pass = os.environ.get("EMAIL_PASS") # Usually an App Password
    
    if not email_user or not email_pass:
        return {"error": "Missing EMAIL_USER or EMAIL_PASS in .env. Cannot access email."}

    if action == "send_email":
        if not to_address or not subject:
            return {"error": "send_email requires 'to_address' and 'subject'."}
            
        try:
            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = subject
            msg['From'] = email_user
            msg['To'] = to_address
            
            # Using Gmail's SMTP as default for simplicity
            smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.environ.get("SMTP_PORT", "587"))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_user, email_pass)
                server.send_message(msg)
                
            return {"success": True, "message": f"Email successfully sent to {to_address}."}
            
        except Exception as e:
            return {"error": f"Failed to send email: {str(e)}"}
            
    elif action == "read_inbox":
        try:
            imap_server = os.environ.get("IMAP_SERVER", "imap.gmail.com")
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(email_user, email_pass)
            mail.select("inbox")
            
            status, messages = mail.search(None, query)
            if status != "OK":
                return {"error": "Failed to search inbox."}
                
            email_ids = messages[0].split()
            # Get the most recent emails up to the limit
            recent_ids = email_ids[-limit:] if len(email_ids) > limit else email_ids
            
            extracted_emails = []
            
            for e_id in recent_ids:
                status, msg_data = mail.fetch(e_id, '(RFC822)')
                if status == "OK":
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            # Extract body safely
                            email_body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        email_body = part.get_payload(decode=True).decode(errors="ignore")
                                        break
                            else:
                                email_body = msg.get_payload(decode=True).decode(errors="ignore")
                                
                            extracted_emails.append({
                                "id": e_id.decode(),
                                "from": msg.get("From"),
                                "subject": msg.get("Subject"),
                                "date": msg.get("Date"),
                                "body": email_body[:1000] # Truncate massive emails to protect context
                            })
                            
            mail.logout()
            
            if not extracted_emails:
                return {"success": True, "message": f"No emails found matching query '{query}'."}
                
            return {"success": True, "emails": extracted_emails}
            
        except Exception as e:
            return {"error": f"Failed to read inbox: {str(e)}"}
            
    else:
        return {"error": "Invalid action. Use 'read_inbox' or 'send_email'."}
