"""Retrieve per-song notes for a ranked list of song ids."""
import logging
import re
from pathlib import Path

from src.recommender import load_songs

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_NOTES_PATH = DATA_DIR / "song_notes.md"
DEFAULT_SONGS_PATH = DATA_DIR / "songs.csv"

_SECTION = re.compile(r"^##\s+(\d+)\s*\|")


def load_notes(path: str | Path = DEFAULT_NOTES_PATH) -> dict[int, str]:
    """Parse a notes markdown file into {song_id: note_text}, one note per "## <id> |" section."""
    sections: dict[int, list[str]] = {}
    current: int | None = None
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            match = _SECTION.match(line)
            if match:
                current = int(match.group(1))
                sections[current] = []
            elif line.startswith("#"):
                current = None  # any other heading ends the open section
            elif current is not None and line:
                sections[current].append(line)
    return {song_id: " ".join(lines) for song_id, lines in sections.items()}


def _note_from_fields(song: dict) -> str:
    """Build a factual 3-sentence note from a song's CSV fields (used when no written note exists)."""
    tags = ", ".join(song["mood_tags"]) or "no tags"
    decade = f"{song['release_decade']}s" if song["release_decade"] else "an unknown decade"
    explicit = "flagged explicit" if song["explicit"] else "not flagged explicit"
    return (
        f"{song['title']} is a {song['genre']} track by {song['artist']} with a {song['mood']} mood, "
        f"energy {song['energy']:.2f}, and a tempo of {song['tempo_bpm']:g} BPM. "
        f"Its acousticness is {song['acousticness']:.2f} and its instrumentalness is "
        f"{song['instrumentalness']:.2f}. "
        f"Tagged {tags}, it was released in {decade} and is {explicit}."
    )


def retrieve(song_ids: list[int], notes: dict[int, str] | None = None,
             songs: list[dict] | None = None) -> list[dict]:
    """Return {id, title, note} dicts in the same order as song_ids; missing notes are built from CSV fields."""
    if notes is None:
        notes = load_notes(DEFAULT_NOTES_PATH)
    if songs is None:
        songs = load_songs(str(DEFAULT_SONGS_PATH))
    catalog = {song["id"]: song for song in songs}

    results: list[dict] = []
    for song_id in song_ids:
        song = catalog.get(song_id)
        if song is None:
            logger.warning("Song id %s is not in the catalog; returning a placeholder note", song_id)
            title = "Unknown song"
        else:
            title = song["title"]

        note = notes.get(song_id)
        if note is None:
            logger.warning("No written note for song id %s; building one from CSV fields", song_id)
            note = (_note_from_fields(song) if song is not None
                    else f"No catalog data found for song id {song_id}.")
        results.append({"id": song_id, "title": title, "note": note})
    return results
