# Project 4 plan — VibeMatch: Music Recommender → Applied AI System
Due: Mon Nov 16, 2:59 AM EST. Base project: Project 3 (Music Recommender Simulation).

## The one-line pitch
Type what you want to hear in plain English. An AI turns it into a taste profile, the
existing scorer retrieves matching songs, and a second AI step explains the picks
using only retrieved facts. A verifier blocks made-up songs.

## What changes vs Project 3
| Layer | Project 3 | Project 4 |
|---|---|---|
| Input | Hard-coded profile dicts | Natural-language request -> Claude parses to UserProfile |
| Retrieval | score_song ranking | Same ranking (reused) + song_notes.md retrieval = RAG |
| Explanation | "genre match (+2.0)" strings | Claude writes grounded explanation |
| Reliability | pytest unit tests | Guardrails + verifier + fallbacks + eval harness with metrics |

## Build order (you drive in VS Code, commit after each)
1. Copy Project 3 into a NEW repo `ai110-project4-vibematch` (keep src/recommender.py untouched).
2. `src/parser.py` — Claude call returns JSON; validate against known genres/moods; keyword fallback.
3. `data/song_notes.md` — 2-3 sentences per song (20 songs). `src/retriever.py` pulls notes for top-k.
4. `src/explainer.py` — prompt: "Use only the facts below. Do not mention any other song."
5. `src/guardrails.py` — input checks (empty, >300 chars, off-topic) + output verifier.
6. `src/app.py` — CLI: `python -m src.app "chill lofi for studying"`; logs to logs/run_log.txt.
7. `--offline` flag: mock LLM responses so graders can reproduce runs without an API key.
8. `eval/test_cases.json` (10 cases: 6 normal, 2 conflicting, 2 adversarial) + `eval/run_eval.py` -> eval/results.txt.
9. README evidence, model_card.md, diagram, deck, case study (Claude drafts from real logs).

## Metrics to report (these go in deck + case study)
- Parse accuracy: parsed genre/mood matches expected (target >= 8/10)
- Grounding rate: explanations with zero invented titles (target 10/10 after verifier)
- Guardrail catch rate: adversarial inputs blocked (target 2/2)
- Fallback rate: how often the system needed a fallback

## Commit rule
You commit and push. Claude never does.
