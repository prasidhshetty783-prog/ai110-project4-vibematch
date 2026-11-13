"""Run the eval cases through the CLI pipeline and write metrics to eval/results.txt.

Usage:
    python -m eval.run_eval            # offline (fixtures + keyword fallback), writes eval/results.txt
    python -m eval.run_eval --live     # calls the real Anthropic API; NOT run automatically
"""
import argparse
import json
import sys
import tempfile
from contextlib import contextmanager, nullcontext
from datetime import datetime
from pathlib import Path

from tabulate import tabulate

from src import explainer
from src.app import run_pipeline
from src.recommender import load_songs

EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parent
CASES_PATH = EVAL_DIR / "test_cases.json"
REPLIES_PATH = ROOT / "tests" / "fixtures" / "explainer_responses.json"
SONGS_CSV = ROOT / "data" / "songs.csv"
RESULTS_PATH = EVAL_DIR / "results.txt"
LIVE_RESULTS_PATH = EVAL_DIR / "results_live.txt"


@contextmanager
def _offline_reply_for(case_id: str, replies: dict[str, str]):
    """Point the explainer's offline fixture at this case's reply for one run.

    explain() reads a single {"reply": ...} file, so each case gets a one-entry copy.
    A case with no reply gets an empty file, which makes explain() use the template.
    """
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "reply.json"
        payload = {"reply": replies[case_id]} if case_id in replies else {}
        path.write_text(json.dumps(payload), encoding="utf-8")
        original = explainer.FIXTURE_JSON
        explainer.FIXTURE_JSON = path
        try:
            yield
        finally:
            explainer.FIXTURE_JSON = original


def evaluate(cases: list[dict], offline: bool, songs: list[dict],
             replies: dict[str, str]) -> list[dict]:
    """Run every case through the pipeline and return one summary row per case."""
    rows = []
    for case in cases:
        context = _offline_reply_for(case["id"], replies) if offline else nullcontext()
        with context:
            result = run_pipeline(case["input"], offline=offline, songs=songs)
        profile = result.profile
        rows.append({
            "id": case["id"],
            "type": case["type"],
            "input": case["input"],
            "expect_genre": case["expect_genre"],
            "expect_mood": case["expect_mood"],
            "got_genre": profile.favorite_genre if profile else None,
            "got_mood": profile.favorite_mood if profile else None,
            "confidence": result.confidence,
            "source": result.source,
            "refused": result.refusal is not None,
            "top_titles": result.top_titles,
        })
    return rows


def compute_metrics(rows: list[dict]) -> dict[str, tuple[int, int]]:
    """Return {metric: (numerator, denominator)} for every reported metric."""
    adversarial = [r for r in rows if r["type"] == "adversarial"]
    answered = [r for r in rows if not r["refused"]]
    # "llm" parse = the API path succeeded (offline: the canned parser fixture matched).
    # Keyword-fallback parses (confidence "low") are excluded from accuracy.
    llm_parse = [r for r in answered if r["confidence"] == "high"]

    parse_hits = sum(
        1 for r in llm_parse
        if r["got_genre"] == r["expect_genre"] and r["got_mood"] == r["expect_mood"]
    )
    grounded = sum(1 for r in answered if r["source"] == "llm")
    caught = sum(1 for r in adversarial if r["refused"])
    fallback = sum(1 for r in rows if r["confidence"] == "low" or r["source"] == "template")

    return {
        "llm_parse_cases": (len(llm_parse), len(answered)),
        "parse_accuracy": (parse_hits, len(llm_parse)),
        "grounding_rate": (grounded, len(answered)),
        "guardrail_catch_rate": (caught, len(adversarial)),
        "fallback_rate": (fallback, len(rows)),
    }


def _pct(num: int, den: int) -> str:
    """Format num/den as a percentage, or n/a when the denominator is zero."""
    return "n/a" if den == 0 else f"{100 * num / den:.1f}%"


def build_report(rows: list[dict], metrics: dict[str, tuple[int, int]], offline: bool) -> str:
    """Return the results text: the per-case table, then the metrics."""
    mode = "offline (per-case fixtures + keyword fallback)" if offline else "LIVE (Anthropic API)"
    table_rows = [
        [r["id"], r["type"], r["input"][:40] or "(empty)",
         f"{r['got_genre']}/{r['got_mood']}" if r["got_genre"] is not None else "-",
         r["confidence"] or "-", r["source"] or "refused",
         " | ".join(r["top_titles"][:2]) or "-"]
        for r in rows
    ]
    table = tabulate(table_rows,
                     headers=["id", "type", "input", "parsed genre/mood", "parse",
                              "explanation", "top 2 titles"],
                     tablefmt="grid")

    keyword_parses = sum(1 for r in rows if r["confidence"] == "low")
    template_uses = sum(1 for r in rows if r["source"] == "template")
    llm_n, llm_d = metrics["llm_parse_cases"]
    parse_n, parse_d = metrics["parse_accuracy"]
    ground_n, ground_d = metrics["grounding_rate"]
    guard_n, guard_d = metrics["guardrail_catch_rate"]
    fall_n, fall_d = metrics["fallback_rate"]
    metric_lines = [
        f"  llm_parse_cases: {llm_n} of {llm_d} answered cases used the LLM parse path",
        f"  parse_accuracy (over llm_parse_cases only): {_pct(parse_n, parse_d)}  ({parse_n}/{parse_d})",
        f"  grounding_rate (explanations passing the verifier, no template fallback): "
        f"{_pct(ground_n, ground_d)}  ({ground_n}/{ground_d})",
        f"  guardrail_catch_rate (adversarial inputs blocked by guardrail): "
        f"{_pct(guard_n, guard_d)}  ({guard_n}/{guard_d})",
        f"  fallback_rate (keyword parser or template explanation used, all cases): "
        f"{_pct(fall_n, fall_d)}  ({fall_n}/{fall_d})",
        f"    of which keyword parses: {keyword_parses}, template explanations: {template_uses}",
    ]
    notes = []
    if offline:
        notes = [
            "Note: offline explanations are per-case fixtures written to name only songs in that",
            "case's top 5, so offline grounding checks the verifier and template plumbing, not model",
            "behavior. Only --live measures real grounding.",
            "Note: offline 'high' parse means the canned parser fixture matched; only the cases",
            "listed in llm_parse_cases have one.",
        ]
    return "\n".join([
        f"Eval run: {datetime.now().isoformat(timespec='seconds')}",
        f"Mode: {mode}",
        "",
        table,
        "",
        "Metrics:",
        *metric_lines,
        "",
        *notes,
    ])


def main(argv: list[str] | None = None, cases_path: Path = CASES_PATH,
         out_path: Path | None = None) -> int:
    """Run the eval set, print the report, and write the metrics file."""
    parser = argparse.ArgumentParser(description="Run the eval cases through the pipeline.")
    parser.add_argument("--live", action="store_true",
                        help="call the real Anthropic API (not run automatically)")
    args = parser.parse_args(argv)
    offline = not args.live
    if out_path is None:
        out_path = RESULTS_PATH if offline else LIVE_RESULTS_PATH
    if not offline:
        print("LIVE mode: this calls the Anthropic API for each case.")

    with open(cases_path, encoding="utf-8") as f:
        cases = json.load(f)
    with open(REPLIES_PATH, encoding="utf-8") as f:
        replies = json.load(f)
    songs = load_songs(str(SONGS_CSV))
    rows = evaluate(cases, offline=offline, songs=songs, replies=replies)
    metrics = compute_metrics(rows)
    report = build_report(rows, metrics, offline=offline)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report + "\n", encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(report)
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
