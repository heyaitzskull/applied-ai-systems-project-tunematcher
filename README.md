# TuneMatcher 2.0

## Original Project

TuneMatcher 1.0 was a simple recommender that suggests songs that match what you like in music. It looks at your favorite genre, mood, and energy level to find good matches. The dataset has 30 songs. Each song has details like genre, mood, energy, tempo, and more. It covers pop, lofi, rock, and some others. But it might not have all music types out there.
---

## What This Version Does

TuneMatcher 2.0 lets you describe what you want in plain English. An example would be "something sad for a rainy night" or "high energy gym music" in which it figures out the rest. It uses an AI model to parse your request, a scoring algorithm to find the best candidate songs, and then the AI again to pick the top 3 and explain why they fit.

This makes it easy because being able to just say what you're feeling is a much more natural way to find something to listen to.

---

## Architecture Overview

The system runs in two AI steps with a retrieval layer in between:

1. **Parser**: a Groq LLM call turns your plain text into structured preferences (genre, mood, tempo, energy, etc.)
2. **RAG Retriever**: a scoring algorithm ranks every song in the dataset against those preferences and returns the top 15
3. **Recommender**: a second LLM call looks at those 15 candidates and picks the best 3, with explanations
4. **Guardrail**: checks that the AI only recommended real songs from the candidate list (catches hallucinations)
5. **Logger**: every request and session is saved to the `logs/` folder

For testing, 5 preset user personas run through the full pipeline and the results are checked against expected genre, mood, and energy ranges. See `diagrams/diagram.md` for the full flow.

---

## Setup

**Requirements:** Python 3.10+, a free Groq API key

**1. Get a free API key**
Go to https://console.groq.com, sign up, and create a key. No credit card needed.

**2. Clone or download the project**
Make sure you have the full folder with `src/` and all `.py` files.

**3. Create a virtual environment and install dependencies**
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac/Linux
pip install groq
```

**4. Set your API key**
in the .env file, add:
    GROQ_API_KEY=your-key-here

```

**5. Run it**
```bash
# Interactive mode
python src/tunematcher.py

# Run the reliability test suite
python src/tunematcher.py --test
```

---

## Sample Interactions

**Example 1: Study music**
```
What kind of music do you want? > something chill to study to, low energy

## Your Recommendations

**1. Tokyo Cafe — Idealism**
A soft lofi track with very low energy (0.2) and almost no intensity. The slow tempo
and acoustic texture make it easy to tune out without getting distracted.

**2. With You — Lofi Hip Hop Radio**
Similar vibe to Tokyo Cafe but slightly warmer. The gentle beat and chill mood make
it good background noise for focusing.

**3. Snowfall — Øneheart & reidenshi**
A more atmospheric pick. Low energy and intensity with a dreamy feel — works well
if you want something that fades into the background.

## Why These Work For You
All three are lofi tracks with minimal intensity, picked specifically because they
won't pull your attention away from what you're doing.
```

**Example 2: Workout music**
```
What kind of music do you want? > intense music for the gym, rock or hip-hop

## Your Recommendations

**1. POWER — Kanye West**
High energy hip-hop with an intense, confident feel. The driving beat is built
for high-effort moments and it scores near the top for both energy and intensity.

**2. Enter Sandman — Metallica**
A hard rock track with heavy guitar and aggressive intensity. If you want something
that actually feels like a workout, this fits.

**3. Stronger — Kanye West**
Sits between the other two — electronic-influenced hip-hop with high energy but
slightly less raw aggression. Good for steady-pace lifting.

## Why These Work For You
These are all high-energy, high-intensity picks across rock and hip-hop, which
is exactly what you asked for. They're loud and driving without being chaotic.
```

**Example 3: Late night mood**
```
What kind of music do you want? > late night drive, moody and atmospheric

## Your Recommendations

**1. Retrograde — James Blake**
Electronic with a melancholy, atmospheric feel. Low intensity but emotionally heavy —
fits the mood of driving alone at night without being overwhelming.

**2. Motion Picture Soundtrack — Radiohead**
Slow, nostalgic, and quiet. The sparse arrangement gives it a cinematic quality
that works well for late-night reflection.

**3. Night Owl — Khruangbin**
More groove-based than the others but still mellow. Adds a bit of warmth to
the playlist without breaking the late-night atmosphere.

## Why These Work For You
All three lean into the moody, atmospheric side of things — none of them are
too heavy or too upbeat. They fit the feeling of being out late and just driving.
```

---

## Design Decisions

**Why two LLM calls instead of one?**
Splitting parsing and recommending into separate steps made each job simpler and more reliable. Asking one prompt to both understand natural language AND reason over 15 songs in a single call produced messier results.

**Why a scoring algorithm for retrieval instead of vector search?**
The dataset is small and the attributes (genre, mood, energy) are already structured. A weighted formula is faster, easier to debug, and more predictable than embeddings for this use case. You can also read exactly why a song ranked where it did.

**Why Groq?**
It's free, fast, and `llama-3.3-70b-versatile` is capable enough for this task. The original version used Google Gemini but ran into quota limits on the free tier.

**Trade-offs**
- The scoring weights (genre 28%, mood 24%, etc.) were set manually. They work well but haven't been formally tuned, a different weighting might produce better results.
- The guardrail catches hallucinations by title matching. If the LLM paraphrases a title slightly differently, it'll still flag it even if the intent was correct.

---

## Testing Summary

There are two layers of testing: unit tests on the scoring functions and an end-to-end reliability suite using AI personas.

**Scoring unit tests: 12/12 passed**

The core scoring logic (genre matching, mood matching, distance scoring, retrieval) was tested with known inputs and expected outputs. All 12 checks passed. These tests don't need the API and can be run anytime.

Tested:
- Exact genre/mood match → score 1.0
- Related genre/mood match → score 0.6 / 0.5
- No match → score 0.0
- Distance scoring at 0%, 50%, and 100% difference
- Full song score with perfect preferences → 1.0
- Retrieval returns exactly 15 candidates, sorted highest to lowest

**Reliability test suite: 5 personas, run with `--test` flag**

Each persona (study, gym, heartbreak, party, late-night drive) runs the full pipeline and the 3 recommended songs are checked against expected genre family, mood family, energy range, and intensity range. Results are saved to `logs/test_results_<timestamp>.json`.

The lofi/chill persona scored highest where the attributes for that genre are distinct enough that the scoring and the LLM agreed. The gym persona was the weakest where songs sometimes scored well numerically but didn't feel like obvious workout picks, because the weights don't fully capture raw aggression the way a person would.

**Guardrail**

Every response is validated to confirm the LLM only recommended songs from the 15 retrieved candidates. During testing, the guardrail caught two real issues: the LLM wrapping song titles in quotes (causing false mismatches) and inconsistent use of em-dash vs hyphen as the title/artist separator. Both were fixed in the parser and prompt.

**Logging**

Every request is logged to `logs/sessions.jsonl` with the parsed preferences, top candidate titles, whether the guardrail passed, and response length. Errors are written to `logs/tunematcher.log` with timestamps. This makes it easy to go back and see exactly what the system did on any given request.