# Model Card: VibeFinder

## 1. Model Details

VibeFinder is a music recommender that takes a plain-English request and returns five songs from a 20-song catalog, with an explanation. It combines a Claude model with a deterministic scorer from Project 3.

**Runtime model (both AI steps):** `claude-haiku-5-5`, the default in `src/parser.py` and `src/explainer.py`. It can be overridden with the `ANTHROPIC_MODEL` environment variable.

| Setting | Parser (`src/parser.py`) | Explainer (`src/explainer.py`) |
|---|---|---|
| Purpose | Turn the request into a taste profile (JSON) | Explain the top five songs in plain language |
| Effort | `low` (`output_config`) | Not set |
| Thinking | Not set in the call | Disabled (`thinking={"type": "disabled"}`) |
| `max_tokens` | 4096 | 1200 |

The scorer, retriever, verifier, and guardrail are ordinary code, not models.

**Fallbacks:** if the parser fails, a keyword parser is used with confidence "low". If the explainer fails or its output names a song outside the top five, a template built from the scoring reasons is used.

## 2. Intended Use

- **Intended:** a course project that shows how an AI step can be wrapped with guardrails, a verifier, fallbacks, and an evaluation harness. Also a demonstration for a small, fictional catalog.
- **Users:** a person typing a short music request in a terminal (`python -m src.app`).
- **Not intended:** a production music service, recommendations for a real catalog, or any decision that matters beyond the demo. All 20 songs and artists are fictional.

**Guardrails on input:** requests that are empty, longer than 300 characters, or contain no genre, mood, energy, or related music word are refused.

## 3. AI Collaboration

Coding and review: Claude Haiku 5.5, Medium effort, in VS Code and chat. Opus was not used.
The developer drove each change and reviewed the code before commit. Process: test, ask the AI to find missed issues,
fix one issue at a time, ask for the exact change and why, then ask about alternatives.

## 4. Evaluation

The eval has 10 cases: 6 normal, 2 conflicting, and 2 adversarial. Expected genre and mood were written by hand before the runs. Each result file below is one run.

**Live run, final** (`eval/results_live_final.txt`):

| Metric | Result |
|---|---|
| parse accuracy (LLM parse cases) | 8/8 (100%) |
| grounding rate | 8/8 (100%) |
| guardrail catch rate | 2/2 (100%) |
| fallback rate | 0/10 (0%) |

**First live run** (`eval/results_live_run1.txt`):

| Metric | Result |
|---|---|
| parse accuracy (LLM parse cases) | 8/8 (100%) |
| grounding rate | 4/8 (50%) |
| guardrail catch rate | 2/2 (100%) |
| fallback rate | 4/10 (40%), all four from template explanations |

The terminal output from this run showed four fallbacks with the message "stop_reason was max_tokens". That message is not saved in any file in the repository.

**Offline run, labeled offline** (`eval/results.txt`): this run checks the plumbing of the code, not model behavior. Each offline explanation is a canned reply written for its eval case and checked against that case's top five, so the verifier passes by construction.

| Metric | Result |
|---|---|
| parse accuracy (LLM parse cases) | 1/1 (100%), one case has a canned parser fixture |
| grounding rate | 8/8 (100%), plumbing only |
| guardrail catch rate | 2/2 (100%) |
| fallback rate | 7/10 (70%), all seven keyword parses |

Changes made between the first and final live runs, and why they were made: `max_tokens` set to 1200, a two-sentence instruction added to the system prompt, and thinking disabled in the explainer's call. The run after raising the limit to 1200 still showed four fallbacks (terminal output, not saved to a file).

## 5. Limitations

- **The verifier checks song titles only.** It confirms that an explanation names only songs from the top five. It does not check numbers or other claims. The demo 3 explanation says Night Drive Loop "echoes the emotional tone you seem to prefer", which is an inference, not a fact from its note.
- **The eval is small.** Ten cases, one run per result file, and expected genre and mood were written by hand before the runs.
- **Explanations may exceed the two-sentence request.** The demo 3 explanations and the single `normal-3` live check both use three sentences per song.
- **Offline grounding checks plumbing only.** The offline explanations were written to name only songs in each case's top five, so the offline 100% says nothing about model behavior. Only a live run measures that.
- **Offline parse accuracy rests on one case.** One parser fixture matches an eval case.
- **The keyword fallback is coarse.** It covers only the genres, moods, and energy words it knows. It is used when the parser fails. An explainer failure falls back to a template, which is less readable.
- **Notes come only from catalog fields.** They are built from genre, mood, energy, tempo, acousticness, tags, decade, instrumentalness, and explicit flag, so they cannot describe anything the catalog does not contain.
- **No human in the loop.** A user cannot accept a result or ask for a change; each request is a single pass.
- **The catalog is 20 fictional songs.** Results describe this catalog, not music in general.
- Numbers in demos 1 to 3 were spot-checked by hand against songs.csv. The verifier does not check numbers.

## 6. Reflection

This project showed me how I work with AI when I build products. I don't trust the first answer. I test the product myself, find the bugs, and ask the AI to check for anything I missed. Then I have it fix the issues one at a time, and for each change I ask what it changed, where, why, and how it solves the problem. I also ask what other options it considered, so I understand the code before I move on. That process caught a real failure: four explanations were cut off in the first live run. Raising the output limit did not stop the fallbacks in the observed runs. Turning off the thinking block was followed by none. The token counts for the failing calls were not logged, so the mechanism is likely but not confirmed. It also showed me the limits of my own checks. The verifier confirms that explanations name only songs from the list, but it doesn't check the numbers, so I spot-checked those by hand against the data. That's what I mean by building AI with trust: test it, verify it, and be clear about what the checks don't cover. My UX and product design background shaped how I judged the output, so the result is clear to the person using it, not just technically correct.
