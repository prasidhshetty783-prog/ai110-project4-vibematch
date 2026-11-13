"""Explain ranked recommendations in plain language via Claude, with a verified template fallback."""
import json
import logging
import os
from dataclasses import asdict
from pathlib import Path

import anthropic

from src.recommender import Recommender, Song, UserProfile, load_songs
from src.verifier import verify

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
SONGS_CSV = ROOT / "data" / "songs.csv"
FIXTURE_JSON = ROOT / "tests" / "fixtures" / "explainer_responses.json"
DEFAULT_MODEL = "claude-haiku-5-5"
MAX_TOKENS = 1024

SYSTEM_PROMPT = (
    "You explain music recommendations to a listener.\n"
    "Explain each recommendation using only the facts in the notes. "
    "Do not mention any song not in the list.\n"
    "Write one short paragraph per song and say how it fits the listener's profile."
)


class ExplainFailure(Exception):
    """Raised when the LLM path can't produce a usable explanation."""


def _catalog() -> list[Song]:
    """Load data/songs.csv as Song objects so the template can score each one."""
    return [Song(**row) for row in load_songs(str(SONGS_CSV))]


def _prompt(profile: UserProfile, ranked: list[dict]) -> str:
    """Build the user message from only the user profile and the retrieved notes."""
    notes = "\n".join(f"- {item['title']}: {item['note']}" for item in ranked)
    return f"Listener profile: {json.dumps(asdict(profile))}\n\nNotes:\n{notes}"


def _call_llm(profile: UserProfile, ranked: list[dict]) -> str:
    """Ask Claude for the explanation and return its text reply."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ExplainFailure("ANTHROPIC_API_KEY is not set")
    model = os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL

    client = anthropic.Anthropic(api_key=api_key, timeout=30.0)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _prompt(profile, ranked)}],
        )
    except anthropic.APIError as exc:
        raise ExplainFailure(f"API error: {exc}") from exc

    # Anything but a clean end_turn (refusal, truncation) is not a usable explanation.
    if response.stop_reason != "end_turn":
        raise ExplainFailure(f"stop_reason was {response.stop_reason}")
    reply = "".join(block.text for block in response.content if block.type == "text").strip()
    if not reply:
        raise ExplainFailure("empty reply")
    return reply


def _offline_reply() -> str:
    """Return the canned explanation from the fixtures file."""
    with open(FIXTURE_JSON, encoding="utf-8") as f:
        reply = str(json.load(f).get("reply", "")).strip()
    if not reply:
        raise ExplainFailure("offline fixture has no reply")
    return reply


def _template(profile: UserProfile, ranked: list[dict], recommender: Recommender,
              by_id: dict[int, Song]) -> str:
    """Explain each ranked song with the scoring reasons from recommender.explain_recommendation()."""
    lines = []
    for item in ranked:
        song = by_id.get(item["id"])
        if song is None:
            lines.append(f"{item['title']}: no scoring details available.")
        else:
            lines.append(f"{song.title}: {recommender.explain_recommendation(profile, song)}")
    return "\n".join(lines)


def explain(profile: UserProfile, ranked: list[dict],
            offline: bool = False) -> tuple[str, str]:
    """Return (explanation, "llm" or "template") for the ranked songs, with a template fallback."""
    if not ranked:
        return "No songs to explain.", "template"

    songs = _catalog()
    recommender = Recommender(songs)
    by_id = {song.id: song for song in songs}

    try:
        text = _offline_reply() if offline else _call_llm(profile, ranked)
    except ExplainFailure as exc:
        logger.warning("Falling back to template explanation: %s", exc)
        return _template(profile, ranked, recommender, by_id), "template"

    passed, problems = verify(
        text,
        [item["title"] for item in ranked],
        [song.title for song in songs],
    )
    if not passed:
        logger.warning("Explanation failed verification: %s", "; ".join(problems))
        return _template(profile, ranked, recommender, by_id), "template"
    return text, "llm"
