"""Turn a free-text music request into a UserProfile, via Claude with a keyword fallback."""
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple

import anthropic

from src.recommender import UserProfile, load_songs

ROOT = Path(__file__).resolve().parent.parent
SONGS_CSV = ROOT / "data" / "songs.csv"
FIXTURES_JSON = ROOT / "tests" / "fixtures" / "llm_responses.json"
DEFAULT_MODEL = "claude-haiku-5-5"

# Keyword fallback vocab. Energy targets: high 0.85, medium 0.5, low 0.3.
_ENERGY_WORDS = [
    (0.85, ["high energy", "energetic", "workout", "gym", "hype", "pump", "party", "upbeat", "fast"]),
    (0.3, ["low energy", "calm", "chill", "relax", "sleep", "mellow", "quiet", "slow", "study"]),
    (0.5, ["medium energy", "moderate", "mid tempo", "mid-tempo"]),
]
_NOT_ACOUSTIC_WORDS = ["not acoustic", "no acoustic", "electronic", "synth"]
_ACOUSTIC_WORDS = ["acoustic", "unplugged"]
_INSTRUMENTAL_WORDS = ["instrumental", "no vocals", "no lyrics", "without lyrics"]
_CLEAN_WORDS = ["clean", "no explicit", "not explicit", "family friendly", "kid friendly", "for kids"]

_PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "favorite_genre": {"type": "string"},
        "favorite_mood": {"type": "string"},
        "target_energy": {"anyOf": [{"type": "number"}, {"type": "null"}]},
        "likes_acoustic": {"anyOf": [{"type": "boolean"}, {"type": "null"}]},
        "wants_instrumental": {"type": "boolean"},
        "avoid_explicit": {"type": "boolean"},
    },
    "required": [
        "favorite_genre", "favorite_mood", "target_energy",
        "likes_acoustic", "wants_instrumental", "avoid_explicit",
    ],
    "additionalProperties": False,
}


class ParseFailure(Exception):
    """Raised when the LLM path can't produce a valid profile."""


@lru_cache(maxsize=1)
def _catalog_vocab() -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """Return (genres, moods) found in data/songs.csv, lowercased and sorted."""
    songs = load_songs(str(SONGS_CSV))
    genres = sorted({_norm(s["genre"]) for s in songs})
    moods = sorted({_norm(s["mood"]) for s in songs})
    return tuple(genres), tuple(moods)


def _norm(value: Optional[str]) -> str:
    """Lowercase and strip a string; None becomes ""."""
    return "" if value is None else str(value).strip().lower()


def _system_prompt(genres: Tuple[str, ...], moods: Tuple[str, ...]) -> str:
    """Build the instruction that tells Claude how to fill the profile JSON."""
    return (
        "You convert a listener's music request into a taste profile for a song recommender.\n"
        f"favorite_genre must be one of: {', '.join(genres)}; use \"\" if the request names no genre.\n"
        f"favorite_mood must be one of: {', '.join(moods)}; use \"\" if the request implies no mood.\n"
        "If the request names a genre or mood outside these lists, pick the closest listed one only "
        "when it is clearly the same thing; otherwise use \"\".\n"
        "target_energy is 0.0 (very calm) to 1.0 (very intense), or null if energy isn't implied.\n"
        "likes_acoustic is true/false only if the request says so, else null.\n"
        "wants_instrumental and avoid_explicit are true only if the request asks for it."
    )


def _call_llm(text: str, genres: Tuple[str, ...], moods: Tuple[str, ...]) -> str:
    """Ask Claude for the profile JSON and return the raw text reply."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ParseFailure("ANTHROPIC_API_KEY is not set")
    model = os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL

    client = anthropic.Anthropic(api_key=api_key, timeout=30.0)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=_system_prompt(genres, moods),
            messages=[{"role": "user", "content": text}],
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": _PROFILE_SCHEMA},
            },
        )
    except anthropic.APIError as exc:
        raise ParseFailure(f"API error: {exc}") from exc

    if response.stop_reason != "end_turn":
        raise ParseFailure(f"unexpected stop_reason: {response.stop_reason}")
    reply = next((b.text for b in response.content if b.type == "text"), None)
    if reply is None:
        raise ParseFailure("no text block in response")
    return reply


def _offline_reply(text: str) -> str:
    """Return the canned reply for this request from the fixtures file."""
    with open(FIXTURES_JSON, encoding="utf-8") as f:
        fixtures = json.load(f)
    entry = fixtures.get(_norm(text))
    if entry is None:
        raise ParseFailure("no offline fixture for this request")
    if isinstance(entry, dict) and "error" in entry:
        raise ParseFailure(f"simulated API error: {entry['error']}")
    return entry if isinstance(entry, str) else json.dumps(entry)


def _validate(data: object, genres: Tuple[str, ...], moods: Tuple[str, ...]) -> UserProfile:
    """Check the LLM's JSON against the catalog and return a UserProfile."""
    if not isinstance(data, dict):
        raise ParseFailure("reply is not a JSON object")

    genre = _norm(data.get("favorite_genre"))
    if genre and genre not in genres:
        raise ParseFailure(f"unknown genre: {genre!r}")
    mood = _norm(data.get("favorite_mood"))
    if mood and mood not in moods:
        raise ParseFailure(f"unknown mood: {mood!r}")

    energy = data.get("target_energy")
    if energy is not None:
        if isinstance(energy, bool) or not isinstance(energy, (int, float)):
            raise ParseFailure(f"target_energy is not a number: {energy!r}")
        energy = min(1.0, max(0.0, float(energy)))

    acoustic = data.get("likes_acoustic")
    if acoustic is not None and not isinstance(acoustic, bool):
        raise ParseFailure(f"likes_acoustic is not a bool: {acoustic!r}")
    for key in ("wants_instrumental", "avoid_explicit"):
        if not isinstance(data.get(key, False), bool):
            raise ParseFailure(f"{key} is not a bool: {data.get(key)!r}")

    return UserProfile(
        favorite_genre=genre,
        favorite_mood=mood,
        target_energy=energy,
        likes_acoustic=acoustic,
        wants_instrumental=data.get("wants_instrumental", False),
        avoid_explicit=data.get("avoid_explicit", False),
    )


def _has_any(text: str, phrases: List[str]) -> bool:
    """True if any phrase appears in text as whole words."""
    return any(re.search(rf"\b{re.escape(p)}\b", text) for p in phrases)


def _find_term(text: str, terms: Tuple[str, ...]) -> str:
    """Return the longest catalog term found in text (so 'indie pop' beats 'pop'), or ""."""
    spaced = text.replace("-", " ")
    for term in sorted(terms, key=len, reverse=True):
        if re.search(rf"\b{re.escape(term.replace('-', ' '))}\b", spaced):
            return term
    return ""


def _keyword_parse(text: str, genres: Tuple[str, ...], moods: Tuple[str, ...]) -> UserProfile:
    """Build a profile from simple keyword matches; anything not found is left empty/None."""
    lowered = _norm(text)
    energy = next((value for value, words in _ENERGY_WORDS if _has_any(lowered, words)), None)

    acoustic: Optional[bool] = None
    if _has_any(lowered, _NOT_ACOUSTIC_WORDS):
        acoustic = False
    elif _has_any(lowered, _ACOUSTIC_WORDS):
        acoustic = True

    return UserProfile(
        favorite_genre=_find_term(lowered, genres),
        favorite_mood=_find_term(lowered, moods),
        target_energy=energy,
        likes_acoustic=acoustic,
        wants_instrumental=_has_any(lowered, _INSTRUMENTAL_WORDS),
        avoid_explicit=_has_any(lowered, _CLEAN_WORDS),
    )


def parse_request(text: str, offline: bool = False) -> Tuple[UserProfile, str]:
    """Parse a music request into (UserProfile, confidence), where confidence is "high" or "low"."""
    genres, moods = _catalog_vocab()
    try:
        reply = _offline_reply(text) if offline else _call_llm(text, genres, moods)
        data = json.loads(reply)
        return _validate(data, genres, moods), "high"
    except (ParseFailure, json.JSONDecodeError):
        return _keyword_parse(text, genres, moods), "low"
