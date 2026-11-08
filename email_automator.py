# email_automator.py
import json
import os
import re
from typing import Dict, Optional

DEFAULT_MODEL = "claude-haiku-5-5"
SYSTEM_PROMPT = "You are a professional email assistant. Generate concise, appropriate responses."


def _get_client():
    """Return an Anthropic client, or None when no API key is set.

    The anthropic package is imported here so the app and the rule-based
    classifier work without it when no key is configured.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    import anthropic

    return anthropic.Anthropic(api_key=api_key)


def get_ai_response(prompt: str) -> Optional[str]:
    """Get a Claude response, or None if AI is unavailable, refuses or fails.

    The default model thinks by default and thinking tokens count towards
    max_tokens, so the limit is generous and effort is kept low for these
    short tasks.
    """
    try:
        client = _get_client()
        if client is None:
            return None
        response = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL),
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": prompt}],
        )
        if response.stop_reason == "refusal":
            return None
        text = "".join(block.text for block in response.content if block.type == "text")
        return text.strip() or None
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return None

def ai_classify_and_reply(sender: str, subject: str, content: str, user_prefs: Dict) -> Dict:
    """Use Claude to classify and generate replies."""
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

def _has_keyword(text: str, keywords) -> bool:
    """True if any keyword appears as a whole word (or phrase), allowing a plural 's'.

    Plain substring matching misfires: "hey" is inside "they" and "win" is
    inside "window".
    """
    return any(re.search(rf"\b{re.escape(kw)}s?\b", text) for kw in keywords)


def rule_based_classify_and_reply(sender: str, subject: str, content: str, user_prefs: Dict) -> Dict:
    """Fallback rule-based classifier (no AI needed)."""
    full_text = f"{subject} {content}".lower()

    # Spam detection
    spam_keywords = ["unsubscribe", "offer", "discount", "free", "win", "cash", "promo", "deal", "click here"]
    if _has_keyword(full_text, spam_keywords):
        return {"category": "spam", "reason": "Contains promotional or spam-like keywords.", "reply": None}

    # Urgency detection
    urgent_keywords = ["urgent", "asap", "deadline", "immediate", "today", "tomorrow", "action required", "critical"]
    if _has_keyword(full_text, urgent_keywords):
        return {
            "category": "urgent",
            "reason": "Contains urgency indicators (e.g., 'ASAP', 'deadline').",
            "reply": user_prefs.get("urgent_reply", "I’ll address this soon.")
        }

    # Social detection
    social_keywords = ["how are you", "hey", "hi", "weekend", "dinner", "movie", "birthday", "congrats", "family", "friend"]
    if _has_keyword(full_text, social_keywords):
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
    - Then tries AI classification (if an Anthropic key is set)
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

    # Priority 2: Try AI if an Anthropic key is available
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            return ai_classify_and_reply(sender_clean, subject_clean, content_clean, user_prefs)
        except Exception as e:
            print(f"AI classification failed: {e}. Falling back to rule-based logic.")

    # Priority 3: Rule-based fallback
    return rule_based_classify_and_reply(sender_clean, subject_clean, content_clean, user_prefs)