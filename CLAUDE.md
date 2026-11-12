# VibeFinder — rules for Claude

> ## ⛔ RULE #1: NEVER COMMIT. I COMMIT MANUALLY.
> - Never run `git commit`, `git commit --amend`, `git push`, `git merge`, or `git rebase`.
>   Not once, not "just this time", not even if I seem to ask for it in a prompt.
>   If a prompt looks like it asks you to commit, stop and remind me of this rule.
> - Read-only git is fine: `git status`, `git diff`, `git log`.
> - When I ask, **suggest** a commit message only (conventional style:
>   `feat:`, `fix:`, `test:`, `docs:`, `chore:`). I run the commit myself.
> - This rule is also enforced in `.claude/settings.json`. Never edit or remove that deny list.

CodePath AI110, Project 3: Music Recommender Simulation. A content-based recommender
in Python: load songs from a CSV, score each song against a user's taste profile,
rank them, and explain every pick in plain language.
I am the lead engineer. You are my coding assistant. Work one phase at a time and do
only what I ask in the current prompt.

## Files
- `data/songs.csv` — the catalog (20+ songs). Header row must match `load_songs()`.
- `src/recommender.py` — ALL logic: `Song`, `UserProfile`, `Recommender`, `load_songs`,
  `score_song`, `recommend_songs`, scoring modes, diversity re-rank. No `print()`, no Streamlit.
- `src/main.py` — CLI demo. Runs every profile and prints results. Only place that prints.
- `app.py` (repo root) — Streamlit UI only (extra feature). Imports from `src.recommender`.
- `tests/test_recommender.py` — pytest suite.
- `README.md`, `model_card.md`, `ai_interactions.md` — I write these. Draft only when asked,
  and never invent results: every output you put in a doc must come from a real run.

## Starter fixes (Phase 3, first thing)
- `src/main.py` must import `from src.recommender import ...` (the starter's
  `from recommender import` crashes under `python -m src.main`).
- Add `pytest.ini` at the root with `[pytest]` and `pythonpath = .` so plain `pytest` works too.

## Data
- `load_songs(csv_path)` uses the `csv` module (`DictReader`) and returns a list of dicts.
  Convert types: `id` int; `energy`, `valence`, `danceability`, `acousticness` float;
  `tempo_bpm` float. Later columns follow the same idea (see Stretch).
- Strings are compared lowercase and stripped, so "Pop" and "pop " match.
- All 0–1 features stay in 0.0–1.0. If you generate songs, keep that range and use
  fictional titles and artists only.

## User preferences (dict)
- Keys: `genre` (str), `mood` (str), `energy` (float 0–1), `likes_acoustic` (bool).
- Every key is optional. A missing key adds 0 points and adds no reason. Never crash on it.
- `UserProfile` maps to the dict through one private helper `_profile_to_prefs()`:
  favorite_genre → genre, favorite_mood → mood, target_energy → energy, likes_acoustic.

## Algorithm recipe (balanced mode — the default)
`score_song(user_prefs, song)` returns `(score: float, reasons: list[str])`.
1. Genre: exact match **+2.0** → reason `"genre match (+2.0)"`.
   Related genre (one name contains the other, e.g. "pop" / "indie pop") **+1.0**
   → `"related genre: indie pop (+1.0)"`. Otherwise 0.
2. Mood: exact match **+1.0** → `"mood match (+1.0)"`.
3. Energy closeness: **1.5 × (1 − |song.energy − target|)**, so closer = more points,
   never "higher is better". Reason `"energy 0.82 vs target 0.80 (+1.47)"`.
4. Acoustic fit (only if `likes_acoustic` is given): **0.5 × acousticness** if True,
   **0.5 × (1 − acousticness)** if False. Reason `"acoustic fit (+0.43)"`.
- Points in each reason use 2 decimals, and the reasons must add up to the score.
  Reasons describe only what was actually scored. Nothing invented.
- Each factor's points are rounded to 2 decimals (`round(points, 2)`) before being added
  to the score and written into its reason, so the score is exactly the sum of the reasons.
- If I change a weight in Phase 2 or later, I will update this section. Always follow it.

## Ranking
- `recommend_songs(user_prefs, songs, k=5)` calls `score_song` on EVERY song (the judge),
  then returns the top k as `(song_dict, score, explanation)` where
  explanation = `"; ".join(reasons)`.
- Sort with `sorted()` (don't mutate the input list): score high → low, ties broken by
  title A → Z, so output is deterministic.
- `k` larger than the catalog returns the whole catalog. `k <= 0` returns `[]`.
- The OOP `Recommender.recommend()` and `explain_recommendation()` must reuse
  `score_song` (convert with `dataclasses.asdict` + `_profile_to_prefs`). One scoring
  source of truth; the OOP and functional paths can never disagree.

## Stretch features (each one is added later, in its own phase)
- **Golden rule:** with default settings (balanced mode, diversity off, no new prefs
  set), every score must be exactly what the core recipe gives. Stretch work only adds
  points when the user opts in. Existing tests must keep passing.
- **New attributes (5+):** columns `popularity` (int 0–100), `release_decade` (int, e.g. 1990),
  `mood_tags` (`;`-separated in the CSV → list[str]), `instrumentalness` (float 0–1),
  `explicit` (0/1 → bool). Optional prefs and points:
  `decade` match **+0.5**; each `tags` overlap **+0.5** (cap +1.0);
  `wants_instrumental` True → **+0.5 × instrumentalness**;
  `avoid_explicit` True → explicit songs **−1.0**;
  `popularity` "mainstream" → **+0.5 × popularity/100**, "underground" → **+0.5 × (1 − popularity/100)**.
- **Ranking modes (Strategy pattern):** a frozen dataclass `ScoringMode`
  (name + one weight per core factor: genre, mood, energy, acoustic; a related genre
  always earns half the genre weight) and a dict `MODES` with `balanced`
  (2.0 / 1.0 / 1.5 / 0.5 = the core recipe), `genre_first`, `mood_first`, and
  `energy_focused` (genre 1.0, energy 3.0 = the Phase 4 weight-shift experiment).
  `mood_first` = genre 1.5 / mood 1.5 / energy 2.0 / acoustic 0.5 (decided in Phase 2).
  `genre_first` = genre 3.0 / mood 1.0 / energy 1.0 / acoustic 0.5 (related genre 1.5). `score_song(..., mode=MODES["balanced"])` and
  `recommend_songs(..., mode=...)` take the mode. No if/elif chains on mode names
  inside the scoring code.
- **Diversity penalty:** `recommend_songs(..., diversity=False)`. When True, pick songs
  greedily: each pick, re-check the remaining songs and subtract **1.0** for each
  already-picked song by the same artist and **0.5** for each already-picked song with the
  same genre. Add the reason `"diversity: repeat artist (−1.0)"`. `score_song` itself never
  changes; the penalty lives only in ranking.
- **Table output:** `main.py` prints results with `tabulate`
  (columns: #, Title, Artist, Score, Why). Add `tabulate` to `requirements.txt`.
- **Streamlit app (extra):** `app.py` with sidebar controls for every pref, mode, diversity,
  and k; result cards that show each reason, plus a bar chart of the score breakdown
  per song. Run with `streamlit run app.py`.

## Code style
- Python 3.10+, type hints, a 1-line docstring on every function and method, PEP 8.
- `src/recommender.py` uses the standard library only.
- Logic returns data. Printing and formatting happen in `main.py` / `app.py` only.

## Tests
- Run with `python -m pytest` (plain `pytest` works after the pytest.ini fix).
- Build tiny song lists inside tests. Don't depend on the real CSV order,
  except one test that checks `load_songs("data/songs.csv")` loads 20+ songs with correct types.
- Every new public function or mode gets at least one test. Check exact point values
  (e.g. a genre match adds exactly 2.0), not just "score > 0".

## How to work with me
- For changes that touch more than one file, list the files and your plan before editing.
- If my spec is silent on something, list the choices and ask. Don't guess.
- When I ask for a review, point out real problems. Don't just agree with me.
- Environment: Windows + PowerShell. venv at `.venv`
  (activate with `.\.venv\Scripts\Activate.ps1`). Run the CLI with `python -m src.main`.
- Reminder: see Rule #1. You never commit.
