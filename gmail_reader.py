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

def fetch_recent_emails(service, max_results=5):
    results = service.users().messages().list(userId='me', maxResults=max_results).execute()
    messages = results.get('messages', [])
    email_list = []
    
    for msg in messages:
        txt = service.users().messages().get(userId='me', id=msg['id']).execute()
        payload = txt['payload']
        headers = payload.get("headers")
        
        sender = subject = ""
        for d in headers:
            if d['name'] == 'From':
                sender = d['value']
            if d['name'] == 'Subject':
                subject = d['value'] or "(no subject)"
        
        # Recursive helper to find plain text body
        def find_plain_text(parts):
            for part in parts:
                if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                    return part['body']['data']
                # Handle nested parts (e.g., forwarded messages)
                if part.get('parts'):
                    nested = find_plain_text(part['parts'])
                    if nested:
                        return nested
            return None
        
        body = "[No body content]"
        
        if 'parts' in payload:
            data = find_plain_text(payload['parts'])
            if data:
                try:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                except Exception as e:
                    body = f"[Decoding error: {str(e)}]"
            else:
                body = "[No plain text body found]"
        else:
            # Single-part message (rare, but possible)
            if payload['body'].get('data'):
                try:
                    body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
                except Exception as e:
                    body = f"[Decoding error: {str(e)}]"
        
        # CRITICAL: STRIP HTML TAGS AND CLEAN WHITESPACE 
        body = re.sub(r'<[^>]*>', '', body)  # Remove all HTML tags
        body = re.sub(r'\s+', ' ', body).strip()  # Replace multiple spaces/newlines with single space
        
        email_list.append({
            "sender": sender,
            "subject": subject,
            "content": body[:1000]  # Keep more context for better classification
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