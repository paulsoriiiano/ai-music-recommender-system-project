# 🎵 VibeFinder — Music Recommender Simulation

## Original Project (CodePath Modules 1–3)

This repository started as the **Music Recommender Simulation** project from Modules
1–3 of the CodePath AI course. The original goals were to represent songs and a user
"taste profile" as plain data, design a hand-written scoring rule that turns that data
into ranked recommendations, and evaluate/reflect on what a simple content-based
recommender gets right and wrong compared to real-world systems like Spotify. That
version had no AI model in it at all — it was pure Python arithmetic (weighted feature
matching) over an 18-song CSV catalog.

This submission extends that project with an **agentic AI workflow** (Part 2/3 of the
assignment): a Claude-powered layer that lets a user describe their taste in plain
English instead of filling out a structured profile, while reusing the original scorer
unchanged underneath.

---

## Title & Summary

**VibeFinder** is a small, fully explainable music recommender. Given a "taste
profile" — favorite genre, favorite mood, target energy, and an acoustic preference —
it scores every song in a catalog and returns the top matches with a plain-language
reason for each pick. On top of that deterministic core, it adds an **agentic
workflow**: describe what you want to hear in a sentence, and an LLM parses your
request into a taste profile, the scorer ranks the catalog, a self-check step verifies
the results actually make sense for the catalog, retries if they don't, and a final
LLM call writes a short recommendation — grounded strictly in the real scored results,
never inventing a song.

Why it matters: "recommendation" is often treated as a black box, but this project
makes every step legible — you can see exactly why a song was picked (rule-based
scoring reasons) *and* exactly how a natural-language request became a structured query
(the agent's own log of what it parsed, checked, and retried). That transparency is the
whole point: it's a small, honest model of how a production recommender's content-based
half works, plus a demonstration of how to bolt an LLM onto deterministic business logic
without letting the LLM's mistakes reach the user unchecked.

---

## Architecture Overview

Full diagram: [`diagrams/system_diagram.md`](diagrams/system_diagram.md) (Mermaid source).

There are two entry points that share one scoring core:

1. **Default demo** (`python -m src.main`) — five hardcoded taste profiles run straight
   through the scorer and print their top-5 results. No AI involved; this is the
   original Modules 1–3 deliverable, unchanged.
2. **Agentic mode** (`python -m src.main --agent "<free text>"`) — a **plan → act →
   check → (retry) → explain** loop:
   - **Plan**: an LLM call (`parse_preferences`) turns free text into the same
     `genre`/`mood`/`energy`/`likes_acoustic` shape the scorer expects, constrained to
     genres/moods that actually exist in the catalog.
   - **Act**: the existing `recommend_songs` scorer runs, completely unchanged.
   - **Check**: `check_results` is a plain-Python heuristic gate (no LLM call) that
     flags an unknown genre/mood, too few results, or a top score below a threshold.
   - **Retry**: on a failed check, `revise_preferences` asks the LLM to fix the
     specific issues found, up to 2 times.
   - **Explain**: a final LLM call writes 2–4 sentences of natural-language
     recommendation, but only from the real `(song, score, reasons)` tuples the scorer
     returned. A **grounding guardrail** checks the response actually names one of the
     real songs; if it doesn't (a hallucination), the code discards the LLM prose and
     falls back to the same deterministic explanation format used in the demo mode.

Both entry points funnel through `src/recommender.py`, so the agentic layer never
re-implements or second-guesses the scoring math — it only decides *what* to score
against and *whether* the result is good enough to show the user.

---

## Setup Instructions

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. *(Only needed for the agentic `--agent` mode)* Get an API key from the
   [Anthropic Console](https://console.anthropic.com/) and export it:

   ```bash
   export ANTHROPIC_API_KEY=your-key-here
   ```

4. Run the app:

   ```bash
   python -m src.main
   ```

### Running Tests

```bash
pytest
```

All 8 tests pass with **no** `ANTHROPIC_API_KEY` set — `tests/test_agent.py` mocks
every Claude API call directly, so the suite makes zero network requests and costs
nothing to run. You can add more tests in `tests/test_recommender.py` or
`tests/test_agent.py`.

---

## Sample Interactions

### 1. Default demo — "Chill Lofi" profile (real output, rule-based scorer)

**Input** (`user_prefs` dict, no AI involved):
```python
{"genre": "lofi", "mood": "chill", "energy": 0.35, "likes_acoustic": True}
```

**Output:**
```
=== Chill Lofi ===
User preferences: {'genre': 'lofi', 'mood': 'chill', 'energy': 0.35, 'likes_acoustic': True}

1. Library Rain — Score: 6.00
   Because: genre match (+2.0), mood match (+1.0), energy similarity (+2.00), matches acoustic preference (+1.0)
2. Midnight Coding — Score: 5.86
   Because: genre match (+2.0), mood match (+1.0), energy similarity (+1.86), matches acoustic preference (+1.0)
3. Focus Flow — Score: 4.90
   Because: genre match (+2.0), energy similarity (+1.90), matches acoustic preference (+1.0)
4. Spacewalk Thoughts — Score: 3.86
   Because: mood match (+1.0), energy similarity (+1.86), matches acoustic preference (+1.0)
5. Coffee Shop Stories — Score: 2.96
   Because: energy similarity (+1.96), matches acoustic preference (+1.0)
```

### 2. Default demo — "Adversarial (Sad but High-Energy)" profile (real output)

This profile deliberately asks for a combination (`classical` + `sad` + `energy=0.9`)
that barely exists in the catalog, to see how the scorer degrades.

**Input:**
```python
{"genre": "classical", "mood": "sad", "energy": 0.9}
```

**Output:**
```
=== Adversarial (Sad but High-Energy) ===
User preferences: {'genre': 'classical', 'mood': 'sad', 'energy': 0.9}

1. Autumn Piano — Score: 2.50
   Because: genre match (+2.0), energy similarity (+0.50)
2. Storm Runner — Score: 1.98
   Because: energy similarity (+1.98)
3. Gym Hero — Score: 1.94
   Because: energy similarity (+1.94)
4. Neon Pulse — Score: 1.90
   Because: energy similarity (+1.90)
5. Riot Engine — Score: 1.86
   Because: energy similarity (+1.86)
```
It doesn't fail loudly — it just falls back almost entirely on energy similarity once
genre/mood stop matching, which is *technically* correct but shows the system has no
way to say "I'm not confident about this."

### 3. Agentic mode — illustrative example (requires `ANTHROPIC_API_KEY`)

The following was **not captured from a live API call** in this environment (no key
was configured here) — it illustrates the expected shape of a run, based on the actual
code path in `src/agent.py`, not a fabricated transcript of real model output.

```
$ python -m src.main --agent "chill music for studying, not too acoustic"

Loaded songs: 18
INFO: parsed preferences: {'genre': 'lofi', 'mood': 'chill', 'energy': 0.3, 'likes_acoustic': False}
INFO: self-check passed: []

=== Agentic recommendation for: "chill music for studying, not too acoustic" ===
Parsed preferences: {'genre': 'lofi', 'mood': 'chill', 'energy': 0.3, 'likes_acoustic': False}

(2-4 sentence LLM summary referencing the real top-K songs and their scored reasons,
 e.g. "Midnight Coding and Focus Flow are strong picks here — both are lofi and chill,
 sitting right at your low-energy target, and neither leans acoustic.")
```

If the parsed genre/mood didn't exist in the catalog, or the top score came back too
low, the console would instead show a `retry N: self-check failed (...)` line before
the final recommendation — see `tests/test_agent.py::test_run_agentic_recommendation_retries_on_unknown_genre`
for a concrete example of that path under test.

---

## Design Decisions

- **Keep the scorer untouched.** The agentic layer never re-implements or overrides
  `recommend_songs`/`score_song` — it only decides what to feed in and whether to trust
  what comes out. This means the rule-based scoring behavior (and its documented
  weighting: genre 2.0, mood 1.0, energy up to 2.0, acoustic 0.5–1.0) is identical
  whether you use the fixed demo profiles or free text.
- **Self-check in plain Python, not another LLM call.** `check_results` uses catalog
  membership and a score threshold — no extra API cost, and no risk of an LLM
  "checker" rubber-stamping its own sibling's mistake. The only place an LLM's output
  is trusted without a second opinion is the final explanation text, which is why that
  step has its own guardrail instead.
- **Grounding over eloquence.** The explanation step is deliberately restricted to
  talking about songs it was actually handed — the prompt states this explicitly, and
  the code double-checks it by requiring at least one real song title to appear in the
  response. A hallucinated recommendation is worse than a plain one, so the fallback is
  the same deterministic template used elsewhere in the app, not an apology or a retry
  (retrying explanation generation risks the same failure again for no guaranteed gain).
- **Bounded retries (max 2), not an open loop.** An LLM that can't parse a genre that
  doesn't exist in an 18-song catalog isn't going to succeed on unlimited attempts —
  capping retries keeps cost and latency predictable and forces a best-effort result
  instead of hanging.
- **Fail loud in setup, fail soft at runtime.** A missing `ANTHROPIC_API_KEY` raises a
  clear, actionable error before any API call is attempted (`AgentConfigError`). Once
  running, a transient API failure (rate limit, network blip) is caught, logged, and
  degrades to a best-effort fallback rather than crashing the whole CLI — the user
  still gets *a* result, even if the agentic polish didn't fully land.
- **Trade-off accepted:** the self-check heuristics are simple and occasionally too
  permissive or too strict (see Testing Summary) — a more sophisticated evaluator was
  out of scope for a classroom project, and the plain-Python approach keeps the whole
  loop auditable and free to run in tests.

---

## Testing Summary

- **What worked:** All 8 tests pass, including the original recommender tests and 6
  new ones for the agent. Every agent test mocks `_call_claude_json`/`_call_claude_text`
  directly (see `tests/test_agent.py`), so the whole suite runs with **no API key and
  no network access** — this was a deliberate design choice so the grading environment
  never needs live credentials just to verify the logic works.
- **What the tests cover:** `check_results` correctly flags an unknown genre, a low
  score, and too few results; `parse_preferences` clamps an out-of-range energy value
  and lowercases genre/mood; the full retry loop hits exactly one retry when the first
  parse is bad and the revision fixes it, and stops after `max_retries` without hanging
  when it doesn't; the grounding guardrail correctly discards a mocked response that
  invents a song title not in the given list.
- **What didn't work initially / what I learned:** the first version of the grounding
  guardrail tried to detect "hallucinated" titles by checking the *absence* of a bad
  pattern, which is unreliable — you can't enumerate every way a model might invent a
  song name. Switching to a positive check ("does the response mention at least one
  *real* title?") is simpler and actually testable with a mocked adversarial response.
  This was the clearest lesson from the whole exercise: guardrails on generative output
  are much easier to write and verify as **allow-list checks against known-good data**
  than as **deny-list checks against unknown-bad output**.
- **Manual verification:** confirmed the default demo mode still produces identical
  output after adding the agent code path, and confirmed `--agent` exits cleanly with a
  friendly message (not a traceback) when `ANTHROPIC_API_KEY` is unset. Live end-to-end
  verification of the agent's actual LLM calls (with a real API key) is documented as a
  follow-up in `diagrams/system_diagram.md` and was not performed in this environment.

---

## Experiments From the Original Project

**Weight Shift** — halving `GENRE_WEIGHT` (2.0 → 1.0) and doubling `ENERGY_WEIGHT`
(2.0 → 4.0), then re-running the "Default (Pop/Happy)" profile
(`genre=pop, mood=happy, energy=0.8`):

```
Sunrise City — 5.92 — genre match (+1.0), mood match (+1.0), energy similarity (+3.92)
Rooftop Lights — 4.84 — mood match (+1.0), energy similarity (+3.84)
Gym Hero — 4.48 — genre match (+1.0), energy similarity (+3.48)
Night Drive Loop — 3.80 — energy similarity (+3.80)
Street Cypher — 3.60 — energy similarity (+3.60)
```

With the original weights, the top 5 were all pop, mood-matched, or both. After the
shift, **Night Drive Loop** (synthwave) and **Street Cypher** (hip-hop) climb into the
top 5 purely because their energy is close to 0.8 — neither shares the user's genre or
mood at all. This confirms genre dominance is a *design choice*, not an inherent
property of the data, and a small weight change can pull in completely different
genres just because their energy happens to line up.

- Adding `tempo_bpm` or `valence` to the score was **not** attempted in the committed
  code, but would let the system distinguish, e.g., a slow sad pop song from a fast
  happy one — right now two songs with the same genre/mood/energy but very different
  tempo or valence score identically.

---

## Limitations and Risks

- Only works on a tiny catalog (18 songs) — real platforms score millions of tracks,
  so the "cold start" effect here is exaggerated.
- The rule-based scorer does not understand lyrics, artist identity/popularity, or
  listening history — purely metadata (genre/mood/energy/acousticness).
- It might over-favor one genre or mood, since `genre` carries double the weight of
  `mood` by design.
- Because it's content-based only, it can't do "people who liked X also liked Y" — it
  will never recommend something outside a user's stated preferences, risking a filter
  bubble.
- The agentic layer's self-check is a handful of heuristics, not a learned evaluator,
  and its grounding guardrail only checks that a real song title appears — it doesn't
  verify every claim in the generated prose is accurate.

Deeper reflection on bias, responsible-AI trade-offs, and what I'd change is in
[**model_card.md**](model_card.md), not here.

---

## Reflection

Building the original recommender made concrete something that's easy to wave your
hands at: "recommendation" is really just "score everything, then sort." Adding the
agentic layer on top made a second thing concrete — an LLM in the loop doesn't have to
mean giving up control. The most useful pattern from this project was keeping the LLM
confined to two narrow jobs (translate free text into a known schema; describe known
results in prose) and never letting it touch the actual scoring or ranking logic, with
a cheap, deterministic check in between. That's a small-scale version of how a lot of
real "AI features" bolted onto existing products are actually built.

For the graded responsible-AI reflection — how I collaborated with AI tools, one
helpful and one flawed AI suggestion, and this system's limitations in more depth — see
[**model_card.md**](model_card.md).
