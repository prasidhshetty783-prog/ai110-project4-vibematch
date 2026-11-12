import anthropic
import httpx2
import pytest

from src import parser
from src.parser import parse_request
from src.recommender import UserProfile


def test_valid_offline_parse_is_high_confidence():
    profile, confidence = parse_request("Chill lofi for studying ", offline=True)
    assert confidence == "high"
    assert profile == UserProfile(
        favorite_genre="lofi",
        favorite_mood="chill",
        target_energy=0.35,
        likes_acoustic=True,
        wants_instrumental=True,
        avoid_explicit=False,
    )


def test_unknown_genre_falls_back_to_keywords():
    profile, confidence = parse_request("happy polka for a road trip", offline=True)
    assert confidence == "low"
    # "polka" isn't in songs.csv, so the keyword parser leaves genre empty (scores 0).
    assert profile.favorite_genre == ""
    assert profile.favorite_mood == "happy"
    assert profile.target_energy is None
    assert profile.likes_acoustic is None


def test_api_error_falls_back_to_keywords(monkeypatch):
    class FailingMessages:
        def create(self, **kwargs):
            raise anthropic.APIConnectionError(
                request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
            )

    class FakeClient:
        def __init__(self, **kwargs):
            self.messages = FailingMessages()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(parser.anthropic, "Anthropic", FakeClient)

    profile, confidence = parse_request("high energy rock, clean lyrics")
    assert confidence == "low"
    assert profile.favorite_genre == "rock"
    assert profile.target_energy == 0.85
    assert profile.avoid_explicit is True


def test_offline_simulated_error_falls_back():
    profile, confidence = parse_request("high energy rock, clean lyrics", offline=True)
    assert confidence == "low"
    assert profile.favorite_genre == "rock"


def test_missing_api_key_falls_back(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    profile, confidence = parse_request("acoustic folk, instrumental")
    assert confidence == "low"
    assert profile.favorite_genre == "folk"
    assert profile.likes_acoustic is True
    assert profile.wants_instrumental is True


def test_energy_is_clamped_to_one():
    profile, confidence = parse_request("maximum intensity metal", offline=True)
    assert confidence == "high"
    assert profile.target_energy == 1.0


def test_keyword_parser_prefers_longest_genre():
    genres, moods = parser._catalog_vocab()
    profile = parser._keyword_parse("some indie pop please", genres, moods)
    assert profile.favorite_genre == "indie pop"
