# app.py

import streamlit as st
from email_automator import classify_and_reply
from gmail_reader import get_gmail_service, fetch_recent_emails
import os

st.set_page_config(page_title="AI Email Automator", layout="wide")
st.title("AI Personal Email Automator")

# Sidebar: Configuration
st.sidebar.header("Configuration")

# OpenAI API Key (comment out if not using AI replies yet)
openai_api_key = st.sidebar.text_input("OpenAI API Key (optional)", type="password")
if openai_api_key:
    os.environ["OPENAI_API_KEY"] = openai_api_key

# User Preferences
st.sidebar.header("User Preferences")
urgent_senders_input = st.sidebar.text_input(
    "Urgent senders (comma-separated)",
    value="boss@company.com"
)
urgent_reply = st.sidebar.text_input(
    "Urgent email reply",
    value="I’ll address this soon."
)
work_reply = st.sidebar.text_input(
    "Work email reply (fallback)",
    value="Thank you for your email. I'll review and respond shortly."
)

# Parse preferences
user_prefs = {
    "urgent_senders": [s.strip() for s in urgent_senders_input.split(",") if s.strip()],
    "urgent_reply": urgent_reply,
    "work_reply": work_reply
}

# Main: Load Emails
st.subheader("Recent Emails")

if st.button("Load Emails from Gmail"):
    if not os.path.exists("credentials.json"):
        st.error("Missing `credentials.json`. Download an OAuth client file from the Google Cloud console and save it next to app.py (see the README).")
    else:
        try:
            service = get_gmail_service()
            emails = fetch_recent_emails(service, max_results=5)
            st.session_state.emails = emails
            st.session_state.gmail_service = service  # Store service for potential future use
        except Exception as e:
            st.error(f"Failed to load emails: {e}")

# Use mock data if no real emails
if 'emails' not in st.session_state:
    st.info("Click 'Load Emails from Gmail' or use sample below.")
    if st.button("Use Sample Email"):
        st.session_state.emails = [{
            "sender": "boss@company.com",
            "subject": "Q3 Report Needed ASAP",
            "content": "Hi, please send the Q3 financial summary by end of day. This is urgent."
        }]

# Process and display
if 'emails' in st.session_state:
    for i, email in enumerate(st.session_state.emails):
        with st.expander(f" From: {email['sender']} | Subject: {email['subject']}"):
            st.write("**Content preview:**")
            st.text(email['content'][:300] + ( "..." if len(email['content']) > 300 else ""))

            # Classify emails
            result = classify_and_reply(
                sender=email["sender"],
                subject=email["subject"],
                email_content=email["content"],
                user_prefs=user_prefs
            )
            #Show email category and reason 
            st.markdown(f"**Category**: `{result['category'].upper()}`")
            st.write(f"**Reason**: {result['reason']}")
            
            #Showing classification method
            if os.getenv("OPENAI_API_KEY") and "AI classification failed" not in result["reason"]:
                st.caption("Classified using Artificial Intellegence")
            else:
                st.caption("Classified using rule-based logic")


            
            if result["reply"]:
                st.markdown("**Suggested Reply:**")
                st.code(result["reply"], language="")

                if st.button("Send This Reply", key=f"send_{i}"):
                    if "gmail_service" not in st.session_state:
                        st.error("Gmail service not available. Reload emails first.")
                    else:
                        try:
                            from gmail_reader import send_email
                            # Extract just the email address from "Name <email@domain.com>"
                            import re
                            to_match = re.search(r'[\w\.-]+@[\w\.-]+', email["sender"])
                            to_addr = to_match.group() if to_match else email["sender"]
                            
                            sent = send_email(
                                st.session_state.gmail_service,
                                to=to_addr,
                                subject=f"Re: {email['subject']}",
                                message_text=result["reply"]
                            )
                            if sent:
                                st.success("Reply sent successfully!")
                            else:
                                st.error("Failed to send reply.")
                        except Exception as e:
                            st.error(f"Error sending email: {str(e)}")
