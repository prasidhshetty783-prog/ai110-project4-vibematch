"""Command line runner: guardrail, parse, score, retrieve notes, explain, then print and log one request."""
import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from tabulate import tabulate

from src.explainer import explain
from src.parser import parse_request
from src.recommender import MODES, UserProfile, _profile_to_prefs, load_songs, recommend_songs
from src.retriever import retrieve

ROOT = Path(__file__).resolve().parent.parent
SONGS_CSV = ROOT / "data" / "songs.csv"
DEFAULT_LOG = ROOT / "logs" / "run_log.txt"

MAX_INPUT_CHARS = 300
TOP_K = 5
EXAMPLE_PROMPT = "chill lofi for studying"
# Energy words count as music-related even when no catalog genre or mood is named.
ENERGY_WORDS = ("energy", "energetic", "tempo", "upbeat", "calm", "mellow", "intense",
                "hype", "workout", "party", "acoustic", "instrumental")


@dataclass
class RunResult:
    """Everything one request produced, as data; printing is done by render()."""
    text: str
    refusal: str | None = None
    profile: UserProfile | None = None
    confidence: str | None = None
    rows: list[dict] = field(default_factory=list)  # id, title, artist, score
    explanation: str = ""
    source: str | None = None

    @property
    def top_titles(self) -> list[str]:
        """Titles of the recommended songs, in rank order."""
        return [row["title"] for row in self.rows]


def _music_terms(songs: list[dict]) -> list[str]:
    """Return every catalog genre and mood plus the energy words, lowercased."""
    terms = {song["genre"].strip().lower() for song in songs}
    terms |= {song["mood"].strip().lower() for song in songs}
    terms |= set(ENERGY_WORDS)
    return sorted(terms)


def check_input(text: str, songs: list[dict]) -> str | None:
    """Return a refusal message for input the pipeline should not process, or None if it is fine."""
    cleaned = text.strip()
    if not cleaned:
        return f"Please type a music request, for example: \"{EXAMPLE_PROMPT}\"."
    if len(cleaned) > MAX_INPUT_CHARS:
        return (f"That request is {len(cleaned)} characters; the limit is {MAX_INPUT_CHARS}. "
                f"Please shorten it, for example: \"{EXAMPLE_PROMPT}\".")
    lowered = cleaned.lower()
    has_music_word = any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", lowered)
                         for term in _music_terms(songs))
    if not has_music_word:
        return ("I can only recommend music from a genre, mood, or energy level, so I can't "
                f"help with that. Try something like: \"{EXAMPLE_PROMPT}\".")
    return None


def run_pipeline(text: str, offline: bool = False, mode: str = "balanced",
                 songs: list[dict] | None = None) -> RunResult:
    """Run one request through guardrail, parser, scorer, retriever and explainer, and return the data."""
    songs = load_songs(str(SONGS_CSV)) if songs is None else songs
    refusal = check_input(text, songs)
    if refusal:
        return RunResult(text=text, refusal=refusal)

    profile, confidence = parse_request(text.strip(), offline=offline)
    scored = recommend_songs(_profile_to_prefs(profile), songs, TOP_K, mode=MODES[mode])
    rows = [{"id": song["id"], "title": song["title"], "artist": song["artist"], "score": score}
            for song, score, _ in scored]
    ranked = retrieve([row["id"] for row in rows])
    explanation, source = explain(profile, ranked, offline=offline)
    return RunResult(text=text, profile=profile, confidence=confidence, rows=rows,
                     explanation=explanation, source=source)


def render(result: RunResult) -> str:
    """Format one result for the terminal: a grid table, the explanation, then the parse/explanation line."""
    if result.refusal:
        return result.refusal
    rows = [[rank, row["title"], row["artist"], row["score"]]
            for rank, row in enumerate(result.rows, 1)]
    table = tabulate(rows, headers=["#", "Title", "Artist", "Score"], tablefmt="grid",
                     floatfmt=".2f", maxcolwidths=[None, 22, 18, None])
    return (f"{table}\n\nExplanation:\n{result.explanation}\n\n"
            f"parse: {result.confidence} | explanation: {result.source}")


def write_log(result: RunResult, text: str, log_path: Path) -> None:
    """Append one tab-separated line per request: timestamp, input, parse confidence, explanation source, top-5 titles."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat(timespec="seconds")
    clean_input = " ".join(text.split())
    if result.refusal:
        fields = [timestamp, clean_input, "-", "refused", ""]
    else:
        fields = [timestamp, clean_input, result.confidence or "-", result.source or "-",
                  " | ".join(result.top_titles)]
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\t".join(fields) + "\n")


def main(argv: list[str] | None = None, log_path: Path = DEFAULT_LOG) -> int:
    """Parse CLI arguments, run one request, print the result, and append it to the run log."""
    parser = argparse.ArgumentParser(description="Recommend songs from a plain-language request.")
    parser.add_argument("text", nargs="?", default="",
                        help=f'e.g. "{EXAMPLE_PROMPT}" (max {MAX_INPUT_CHARS} characters)')
    parser.add_argument("--offline", action="store_true",
                        help="use canned fixtures instead of calling the Anthropic API")
    parser.add_argument("--mode", choices=sorted(MODES), default="balanced",
                        help="scoring mode (default: balanced)")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    result = run_pipeline(args.text, offline=args.offline, mode=args.mode)
    print(render(result))
    write_log(result, args.text, log_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
