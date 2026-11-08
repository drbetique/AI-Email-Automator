# gmail_reader.py

import os
import pickle
import base64
import re
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# FIXED: Removed trailing spaces in SCOPES
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

def get_gmail_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('gmail', 'v1', credentials=creds)

def _decode(data: str) -> str:
    """Decode Gmail's URL-safe base64 body data, tolerating missing padding."""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _find_plain_text(parts):
    """Return the base64 data of the first text/plain part, searching nested parts."""
    for part in parts:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return part["body"]["data"]
        if part.get("parts"):
            nested = _find_plain_text(part["parts"])
            if nested:
                return nested
    return None


def extract_body(payload: dict) -> str:
    """Pull a clean plain-text body out of a Gmail message payload."""
    body = "[No body content]"
    try:
        if "parts" in payload:
            data = _find_plain_text(payload["parts"])
            body = _decode(data) if data else "[No plain text body found]"
        elif payload.get("body", {}).get("data"):
            body = _decode(payload["body"]["data"])
    except Exception as e:
        body = f"[Decoding error: {e}]"

    body = re.sub(r"<[^>]*>", "", body)  # remove HTML tags
    return re.sub(r"\s+", " ", body).strip()  # collapse whitespace


def extract_headers(payload: dict) -> tuple:
    """Return (sender, subject) from a Gmail message payload."""
    sender = subject = ""
    for header in payload.get("headers") or []:
        name = header.get("name", "").lower()
        if name == "from":
            sender = header.get("value", "")
        elif name == "subject":
            subject = header.get("value") or ""
    return sender, subject or "(no subject)"


def fetch_recent_emails(service, max_results=5):
    results = service.users().messages().list(userId='me', maxResults=max_results).execute()
    messages = results.get('messages', [])
    email_list = []

    for msg in messages:
        txt = service.users().messages().get(userId='me', id=msg['id']).execute()
        payload = txt['payload']
        sender, subject = extract_headers(payload)
        email_list.append({
            "sender": sender,
            "subject": subject,
            "content": extract_body(payload)[:1000],
        })

    return email_list

def send_email(service, to, subject, message_text):
    """Send an email using the Gmail API."""
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    message = MIMEMultipart()
    message['to'] = to
    message['subject'] = subject
    msg = MIMEText(message_text)
    message.attach(msg)
    
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    try:
        sent_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        return sent_message
    except Exception as e:
        print(f"An error occurred: {e}")
        return None