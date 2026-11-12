# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agentic Workflow (SF8)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

I used Claude Code in VS Code as the agent for the stretch features, one feature at a time: switchable ranking modes, an optional diversity re-rank, five new song attributes with optional preferences, and a CLI demo of them. A separate Claude chat acted as my co-pilot. It drafted the prompts and checked the agent's reports against my real files. I told the agent never to run `git commit`, and I made every commit myself after checking.

**Prompts used:**

Excerpts from the prompts, word for word:

> GOLDEN RULE: a user who sets none of the new prefs gets output identical to now: same scores, same reasons, same order, in every mode, with diversity on or off.

> STEP 0 - STOP AND SHOW ME FIRST. Before you edit any file, show me a 20-row table of proposed values for each song ... Wait for my OK.

> Do NOT run git commit or push. Never invent results: every number you report must come from a real run.

> if any expected number above differs, STOP and tell me; do not adjust it

**What did the agent generate or change?**

| Commit | What it added | Files changed | Tests after |
|---|---|---|---|
| `ef68abe` | `ScoringMode` and four ranking modes | `src/recommender.py`, tests (+119 −22) | 20 |
| `738efd8` | Diversity re-rank | `src/recommender.py`, tests (+149 −3) | 29 |
| `f7d8f0a` | Five song attributes and optional preferences | `data/songs.csv`, `src/recommender.py`, tests (+287 −29) | 53 |
| `a670b0a` | Focus Study profile and diversity run in the CLI | `src/main.py`, tests (+25 −4) | 53 |

It also ran pytest and `python -m src.main` and reported the results.

**What did you verify or fix manually?**

Double-check moment: When I asked Claude to "stage CLAUDE.md and commit it," it refused based only on its reading of the "never commit" rule in CLAUDE.md. It never ran a git command, so the settings.json deny list was never actually tested. Claude also said the rule was "enforced in settings.json" before it had opened that file. I had to ask before it checked and confirmed the deny entries really exist (and that git add isn't blocked). The lesson: an AI saying a safeguard exists isn't proof it works, so check the config yourself.

More double-check moments from the stretch features:

- **A guess about git.** The agent described the git state without running `git log`. I ran it and checked the real history.
- **A wrong tie explanation.** Gym Hero and Rooftop Lights are an exact tie at 3.77 in one test profile, so the title tie-break decides the order. The agent explained it as an acoustic advantage.
- **Wrong counts in a summary.** The agent's table summary said five songs had popularity under 30 while listing four, and said the tag `night` covered 6 genres when it covers 7. I recounted both from its table and told it to compute counts with code, which its next report did.
- **A misleading claim about tags.** The agent said Coffee Shop Stories got into the Focus Study top 5 "on its `rainy` tag alone". It was already #5 without any tags. The Focus Study profile does not change the top 5 order at all, and only comparing it with plain Chill Lofi showed that.
- **My own checks went wrong too.** A false line-ending alarm came from checking in a Linux shell that does not use my Windows git settings. A claim that the diversity penalty would fix Gym Hero appearing in most profiles was wrong, because the penalty only works inside one list.
- **A test that needed a smaller scope.** Adding a profile that sets new preferences broke 8 tests, because the golden-rule test looped over every profile. The fix limited it to profiles that set none of the new preferences and asserted there are exactly five, so a new profile cannot quietly shrink the check.

---

## Design Pattern (SF10)

> Document how AI helped you choose or implement a design pattern.

**Which design pattern did you use?**

Strategy.

**How did AI help you brainstorm or implement it?**

I wanted switchable rankings (genre first, mood first, energy focused) without an if/elif chain inside the scoring code. Strategy fits because the modes differ only in numbers: each one is a small immutable object of weights, and the scoring function receives it as a parameter. Claude Code wrote the dataclass and passed the `mode` parameter through the functions. I chose the `genre_first` weights (3.0 / 1.0 / 1.0 / 0.5) myself, and the `mood_first` weights were decided earlier in the project (1.5 / 1.5 / 2.0 / 0.5). This is a lightweight version of the pattern: a frozen dataclass of weights, not a class hierarchy with methods, because there is no behavior to swap, only numbers.

I checked the work by running the 20 tests, comparing `main.py` output with the previous commit (byte-identical with the default mode), and testing 480 combinations of mode, profile and song to confirm each score equals the sum of its reasons.

**How does the pattern appear in your final code?**

In `src/recommender.py`: the frozen dataclass `ScoringMode` (its `related_genre` property is half the genre weight), the `MODES` dictionary, and the `mode=MODES["balanced"]` parameter on `score_song`, `recommend_songs` and `Recommender.recommend`. The scoring code never branches on a mode name. The default mode is the original recipe, so code that ignores modes behaves exactly as before.
