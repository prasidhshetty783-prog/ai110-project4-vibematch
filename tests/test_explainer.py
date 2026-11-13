import json
from types import SimpleNamespace

import anthropic
import httpx2

from src import explainer
from src.recommender import UserProfile

PROFILE = UserProfile(favorite_genre="pop", favorite_mood="happy",
                      target_energy=0.8, likes_acoustic=False)
RANKED = [
    {"id": 1, "title": "Sunrise City", "note": "Sunrise City is a pop track tagged happy."},
    {"id": 10, "title": "Rooftop Lights", "note": "Rooftop Lights is an indie pop track."},
]


class _FailingMessages:
    """Stands in for client.messages and always raises an API error."""

    def create(self, **kwargs):
        raise anthropic.APIConnectionError(
            request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))


class _FailingClient:
    """Fake Anthropic client whose calls fail."""

    def __init__(self, **kwargs):
        self.messages = _FailingMessages()


def test_api_error_falls_back_to_template(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(explainer.anthropic, "Anthropic", _FailingClient)

    text, source = explainer.explain(PROFILE, RANKED)

    assert source == "template"
    # The template lists each recommended song with its real scoring reasons.
    assert "Sunrise City: genre match (+2.0)" in text
    assert "Rooftop Lights:" in text
    assert "Storm Runner" not in text


def test_missing_api_key_falls_back_to_template(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    text, source = explainer.explain(PROFILE, RANKED)

    assert source == "template"
    assert "Sunrise City: genre match (+2.0)" in text


def test_offline_returns_canned_reply_as_llm():
    with open(explainer.FIXTURE_JSON, encoding="utf-8") as f:
        expected = json.load(f)["reply"].strip()

    text, source = explainer.explain(PROFILE, RANKED, offline=True)

    assert source == "llm"
    assert text == expected


def test_offline_reply_naming_non_top_k_song_falls_back(monkeypatch, tmp_path):
    bad_fixture = tmp_path / "explainer_responses.json"
    bad_fixture.write_text(json.dumps({
        "reply": "Storm Runner is an intense rock track, and Sunrise City is pop."
    }), encoding="utf-8")
    monkeypatch.setattr(explainer, "FIXTURE_JSON", bad_fixture)

    text, source = explainer.explain(PROFILE, RANKED, offline=True)

    assert source == "template"
    assert "Storm Runner" not in text
    assert "Sunrise City: genre match (+2.0)" in text


def test_successful_api_reply_is_used_and_prompt_has_only_notes_and_profile(monkeypatch):
    seen = {}

    class _OkMessages:
        def create(self, **kwargs):
            seen.update(kwargs)
            return SimpleNamespace(
                stop_reason="end_turn",
                content=[SimpleNamespace(type="text", text="Sunrise City fits a happy pop mood.")],
            )

    class _OkClient:
        def __init__(self, **kwargs):
            self.messages = _OkMessages()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(explainer.anthropic, "Anthropic", _OkClient)

    text, source = explainer.explain(PROFILE, RANKED)

    assert (text, source) == ("Sunrise City fits a happy pop mood.", "llm")
    assert "Do not mention any song not in the list" in seen["system"]
    user_message = seen["messages"][0]["content"]
    assert "Sunrise City" in user_message and "Rooftop Lights" in user_message
    assert "Storm Runner" not in user_message  # catalog songs outside the list never reach the prompt
    assert '"favorite_genre": "pop"' in user_message


def test_refusal_falls_back_to_template(monkeypatch):
    class _RefusalMessages:
        def create(self, **kwargs):
            return SimpleNamespace(stop_reason="refusal", content=[])

    class _RefusalClient:
        def __init__(self, **kwargs):
            self.messages = _RefusalMessages()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(explainer.anthropic, "Anthropic", _RefusalClient)

    text, source = explainer.explain(PROFILE, RANKED)

    assert source == "template"
    assert "Sunrise City: genre match (+2.0)" in text
