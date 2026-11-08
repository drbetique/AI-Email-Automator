# email_automator.py
import json
import os
from typing import Dict, Optional

DEFAULT_MODEL = "gpt-4o-mini"


def _get_client():
    """Return an OpenAI client, or None when no API key is set.

    The openai package is imported here so the app and the rule-based
    classifier work without it when no key is configured.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    from openai import OpenAI

    return OpenAI(api_key=api_key)


def get_ai_response(prompt: str) -> Optional[str]:
    """Get an AI-generated response, or None if AI is unavailable or fails."""
    try:
        client = _get_client()
        if client is None:
            return None
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
            messages=[
                {"role": "system", "content": "You are a professional email assistant. Generate concise, appropriate responses."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=150,
            temperature=0.7,
        )
        return (response.choices[0].message.content or "").strip() or None
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return None

def ai_classify_and_reply(sender: str, subject: str, content: str, user_prefs: Dict) -> Dict:
    """Use OpenAI to classify and generate replies."""
    analysis_prompt = f"""
    Analyze this email and categorize it as either 'urgent', 'work', 'social', or 'spam'.
    
    From: {sender}
    Subject: {subject}
    Content: {content}
    
    Respond ONLY with a valid JSON object in this exact format:
    {{"category": "work", "reason": "Brief explanation"}}
    Do not include any other text.
    """
    
    ai_analysis = get_ai_response(analysis_prompt)
    if not ai_analysis:
        raise ValueError("AI returned no response")
    
    # Clean potential markdown code block
    ai_analysis = ai_analysis.strip()
    if ai_analysis.startswith("```"):
        ai_analysis = ai_analysis.split("\n", 1)[-1].rsplit("\n", 1)[0]
    
    # Parse safely
    result = json.loads(ai_analysis)
    category = result["category"].lower()
    reason = result["reason"]
    
    # Handle categories
    if category == "spam":
        return {"category": "spam", "reason": reason, "reply": None}
    
    if category == "urgent":
        return {
            "category": "urgent",
            "reason": reason,
            "reply": user_prefs.get("urgent_reply", "I’ll address this soon.")
        }
    
    if category == "social":
        response_prompt = f"Write a friendly, brief (1-2 sentence) reply to this personal message:\n{content}"
        ai_reply = get_ai_response(response_prompt)
        return {
            "category": "social",
            "reason": reason,
            "reply": ai_reply or "Thanks for your message!"
        }
    
    # Default to work
    response_prompt = f"""
    You are a busy professional. Draft a 2-sentence reply that:
    1. Acknowledges the email
    2. States you'll follow up soon (without overpromising)
    
    Email: {content}
    """
    ai_reply = get_ai_response(response_prompt)
    return {
        "category": "work",
        "reason": reason,
        "reply": ai_reply or user_prefs.get("work_reply", "Thank you for your email. I’ll review and respond shortly.")
    }

def rule_based_classify_and_reply(sender: str, subject: str, content: str, user_prefs: Dict) -> Dict:
    """Fallback rule-based classifier (no AI needed)."""
    full_text = f"{subject} {content}".lower()

    # Spam detection
    spam_keywords = ["unsubscribe", "offer", "discount", "free", "win", "cash", "promo", "deal", "click here"]
    if any(kw in full_text for kw in spam_keywords):
        return {"category": "spam", "reason": "Contains promotional or spam-like keywords.", "reply": None}

    # Urgency detection
    urgent_keywords = ["urgent", "asap", "deadline", "immediate", "today", "tomorrow", "action required", "critical"]
    if any(kw in full_text for kw in urgent_keywords):
        return {
            "category": "urgent",
            "reason": "Contains urgency indicators (e.g., 'ASAP', 'deadline').",
            "reply": user_prefs.get("urgent_reply", "I’ll address this soon.")
        }

    # Social detection
    social_keywords = ["how are you", "hey", "hi ", "weekend", "dinner", "movie", "birthday", "congrats", "family", "friend"]
    if any(kw in full_text for kw in social_keywords):
        return {"category": "social", "reason": "Appears to be a personal or social message.", "reply": None}

    # Default to work (as per your specification)
    return {
        "category": "work",
        "reason": "Email does not clearly match urgent, social, or spam criteria; defaulting to work per specification.",
        "reply": user_prefs.get("work_reply", "Thank you for your email. I’ll review and respond shortly.")
    }

def classify_and_reply(sender: str, subject: str, email_content: str, user_prefs: Dict) -> Dict:
    """
    Main function to classify an email and draft a reply.
    - First checks user-defined urgent senders
    - Then tries AI classification (if OpenAI key is set)
    - Falls back to rule-based logic if AI fails or is unavailable
    """
    sender_clean = sender.lower().strip()
    subject_clean = subject.lower().strip()
    content_clean = email_content.lower().strip()

    # Priority 1: User-defined urgent senders
    urgent_senders = user_prefs.get("urgent_senders", [])
    for urgent_sender in urgent_senders:
        if urgent_sender.lower() in sender_clean:
            return {
                "category": "urgent",
                "reason": f"Sender matches user-defined urgent contact: {sender}",
                "reply": user_prefs.get("urgent_reply", "I’ll address this soon.")
            }

    # Priority 2: Try AI if OpenAI key is available
    if os.getenv("OPENAI_API_KEY"):
        try:
            return ai_classify_and_reply(sender_clean, subject_clean, content_clean, user_prefs)
        except Exception as e:
            print(f"AI classification failed: {e}. Falling back to rule-based logic.")

    # Priority 3: Rule-based fallback
    return rule_based_classify_and_reply(sender_clean, subject_clean, content_clean, user_prefs)