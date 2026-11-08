import email_automator as ea

PREFS = {"urgent_senders": ["boss@company.com"], "urgent_reply": "On it.", "work_reply": "Noted."}


def classify(subject="", content="", sender="someone@example.com", prefs=PREFS):
    return ea.rule_based_classify_and_reply(sender.lower(), subject.lower(), content.lower(), prefs)


class TestRuleBased:
    def test_spam_keywords(self):
        assert classify("Big discount", "Click here to win cash")["category"] == "spam"

    def test_spam_has_no_reply(self):
        assert classify("Free promo")["reply"] is None

    def test_urgent_uses_custom_reply(self):
        result = classify("Report", "Needed ASAP please")
        assert result["category"] == "urgent"
        assert result["reply"] == "On it."

    def test_social_has_no_reply(self):
        result = classify("Dinner", "Are we on for the weekend?")
        assert result["category"] == "social"
        assert result["reply"] is None

    def test_default_is_work_with_custom_reply(self):
        result = classify("Meeting notes", "Attached are the notes.")
        assert result["category"] == "work"
        assert result["reply"] == "Noted."

    def test_keywords_match_whole_words_only(self):
        # "window" contains "win", "they" contains "hey", "freedom" contains "free"
        assert classify("Window cleaning schedule", "They agreed on freedom of choice")["category"] == "work"

    def test_plural_keywords_still_match(self):
        assert classify("Great deals this week")["category"] == "spam"


class TestClassifyAndReply:
    def test_urgent_sender_wins_over_spam_words(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        result = ea.classify_and_reply("Boss <boss@company.com>", "Free pizza", "win a free lunch", PREFS)
        assert result["category"] == "urgent"
        assert "boss@company.com" in result["reason"]

    def test_uses_rules_when_no_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        result = ea.classify_and_reply("a@b.com", "Lunch", "hi, how are you", PREFS)
        assert result["category"] == "social"

    def test_falls_back_to_rules_when_ai_fails(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(ea, "get_ai_response", lambda prompt: None)
        result = ea.classify_and_reply("a@b.com", "Deadline", "due today", PREFS)
        assert result["category"] == "urgent"


class TestAiPath:
    def _ai(self, monkeypatch, replies):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        queue = list(replies)
        monkeypatch.setattr(ea, "get_ai_response", lambda prompt: queue.pop(0))

    def test_parses_json_in_a_code_fence(self, monkeypatch):
        self._ai(monkeypatch, ['```json\n{"category": "spam", "reason": "ad"}\n```'])
        result = ea.classify_and_reply("a@b.com", "x", "y", PREFS)
        assert result == {"category": "spam", "reason": "ad", "reply": None}

    def test_work_reply_comes_from_the_model(self, monkeypatch):
        self._ai(monkeypatch, ['{"category": "work", "reason": "r"}', "Will do."])
        assert ea.classify_and_reply("a@b.com", "x", "y", PREFS)["reply"] == "Will do."

    def test_work_reply_falls_back_to_preference(self, monkeypatch):
        self._ai(monkeypatch, ['{"category": "work", "reason": "r"}', None])
        assert ea.classify_and_reply("a@b.com", "x", "y", PREFS)["reply"] == "Noted."

    def test_bad_json_falls_back_to_rules(self, monkeypatch):
        self._ai(monkeypatch, ["not json"])
        result = ea.classify_and_reply("a@b.com", "Deadline", "asap", PREFS)
        assert result["category"] == "urgent"


class TestGetAiResponse:
    def test_none_without_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert ea.get_ai_response("hi") is None

    def test_uses_configured_model(self, monkeypatch):
        monkeypatch.setenv("OPENAI_MODEL", "my-model")
        seen = {}

        class Msg:
            content = " hello "

        class Choice:
            message = Msg()

        class Completions:
            def create(self, **kwargs):
                seen.update(kwargs)
                return type("R", (), {"choices": [Choice()]})()

        client = type("C", (), {"chat": type("Ch", (), {"completions": Completions()})()})()
        monkeypatch.setattr(ea, "_get_client", lambda: client)
        assert ea.get_ai_response("hi") == "hello"
        assert seen["model"] == "my-model"
