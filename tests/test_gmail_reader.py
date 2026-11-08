import base64
import sys
import types

import pytest


@pytest.fixture(scope="module")
def gr():
    """gmail_reader with the Google client libraries stubbed out."""
    for name, attrs in {
        "google": {},
        "google.auth": {},
        "google.auth.transport": {},
        "google.auth.transport.requests": {"Request": object},
        "google_auth_oauthlib": {},
        "google_auth_oauthlib.flow": {"InstalledAppFlow": object},
        "googleapiclient": {},
        "googleapiclient.discovery": {"build": lambda *a, **k: None},
    }.items():
        mod = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(mod, key, value)
        sys.modules.setdefault(name, mod)
    import gmail_reader

    return gmail_reader


def b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


class TestExtractBody:
    def test_single_part(self, gr):
        assert gr.extract_body({"body": {"data": b64("Hello there")}}) == "Hello there"

    def test_multipart_prefers_plain_text(self, gr):
        payload = {"parts": [
            {"mimeType": "text/html", "body": {"data": b64("<p>html</p>")}},
            {"mimeType": "text/plain", "body": {"data": b64("plain")}},
        ]}
        assert gr.extract_body(payload) == "plain"

    def test_nested_parts(self, gr):
        payload = {"parts": [{"mimeType": "multipart/alternative", "parts": [
            {"mimeType": "text/plain", "body": {"data": b64("deep")}},
        ]}]}
        assert gr.extract_body(payload) == "deep"

    def test_strips_tags_and_collapses_whitespace(self, gr):
        assert gr.extract_body({"body": {"data": b64("<b>Hi</b>\n\n  there")}}) == "Hi there"

    def test_missing_padding_is_tolerated(self, gr):
        assert gr.extract_body({"body": {"data": b64("ab")}}) == "ab"

    def test_no_plain_text_part(self, gr):
        payload = {"parts": [{"mimeType": "text/html", "body": {"data": b64("x")}}]}
        assert gr.extract_body(payload) == "[No plain text body found]"

    def test_empty_payload(self, gr):
        assert gr.extract_body({}) == "[No body content]"


class TestExtractHeaders:
    def test_reads_from_and_subject_case_insensitively(self, gr):
        payload = {"headers": [{"name": "FROM", "value": "A <a@b.com>"}, {"name": "subject", "value": "Hi"}]}
        assert gr.extract_headers(payload) == ("A <a@b.com>", "Hi")

    def test_missing_subject(self, gr):
        assert gr.extract_headers({"headers": [{"name": "From", "value": "a@b.com"}]}) == ("a@b.com", "(no subject)")

    def test_no_headers(self, gr):
        assert gr.extract_headers({}) == ("", "(no subject)")


class TestFetchRecentEmails:
    def test_builds_email_dicts_and_truncates(self, gr):
        class Req:
            def __init__(self, value):
                self.value = value

            def execute(self):
                return self.value

        payload = {"headers": [{"name": "From", "value": "a@b.com"}, {"name": "Subject", "value": "S"}],
                   "body": {"data": b64("x" * 2000)}}

        class Messages:
            def list(self, **kw):
                return Req({"messages": [{"id": "1"}]})

            def get(self, **kw):
                return Req({"payload": payload})

        service = types.SimpleNamespace(users=lambda: types.SimpleNamespace(messages=lambda: Messages()))
        emails = gr.fetch_recent_emails(service)
        assert emails == [{"sender": "a@b.com", "subject": "S", "content": "x" * 1000}]
