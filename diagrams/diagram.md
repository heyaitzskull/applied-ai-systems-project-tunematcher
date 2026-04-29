# TuneMatcher 2.0 — System Diagram

```
 INPUT
 ─────
 User types a natural language request
 e.g. "something chill to study to, low energy"
        │
        ▼
┌───────────────────────────────────────────┐
│         AGENT STEP 1 — Parser             │  agent.py
│         Groq LLM (llama-3.3-70b)         │
│                                           │
│  Converts plain text into structured      │
│  prefs: genre, mood, tempo, energy,       │
│  acousticness, valence, intensity         │
└───────────────────┬───────────────────────┘
                    │ structured JSON prefs
                    ▼
┌───────────────────────────────────────────┐
│         RAG RETRIEVER                     │  scoring.py
│         Pure Python scoring engine        │
│                                           │
│  Scores every song against prefs using    │  ◄──── songs.json
│  weighted formula (genre 28%, mood 24%,   │       (song dataset)
│  tempo 14%, acousticness 12%, …)          │
│                                           │
│  Returns top 15 scored candidates         │
└───────────────────┬───────────────────────┘
                    │ top 15 candidates + scores
                    ▼
┌───────────────────────────────────────────┐
│         AGENT STEP 2 — Recommender        │  agent.py
│         Groq LLM (llama-3.3-70b)         │
│                                           │
│  Reasons over candidates:                 │
│  - Analyzes scores AND qualitative fit    │
│  - Self-checks for poor mood/energy fits  │
│  - Picks best 3 with explanations         │
└───────────────────┬───────────────────────┘
                    │ response text + 3 song titles
                    ▼
┌───────────────────────────────────────────┐
│         GUARDRAIL                         │  agent.py
│         validate_recommendations()        │
│                                           │
│  Checks: are all picks from the           │
│  candidate pool? (prevents hallucination) │
│                                           │
│  PASS → response delivered as-is         │
│  FAIL → warning appended to response      │
└───────────────────┬───────────────────────┘
                    │
          ┌─────────┴──────────┐
          ▼                    ▼
┌──────────────────┐  ┌────────────────────────┐
│  OUTPUT          │  │  SESSION LOGGER         │  tunematcher.py
│                  │  │                         │
│  User sees top 3 │  │  logs/tunematcher.log   │
│  recommendations │  │  logs/sessions.jsonl    │
│  with explanatio │  │  (every request saved)  │
└──────────────────┘  └─────────────────────────┘


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 TESTING PATH  (python tunematcher.py --test)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 5 Test Personas (defined in testing.py)
 e.g. "Chill Lofi Student", "Gym Goer", "Heartbreak"
        │
        ▼
 Each persona runs the full pipeline above
        │
        ▼
┌───────────────────────────────────────────┐
│         EVALUATOR                         │  testing.py
│         score_song_for_test()             │
│                                           │
│  For each recommended song, checks:       │
│  - genre in expected family?              │
│  - mood in expected family?               │
│  - energy within expected range?          │
│  - intensity within expected range?       │
│                                           │
│  Scores: X/Y checks passed per persona    │
└───────────────────┬───────────────────────┘
                    │
                    ▼
         Overall reliability %
         PASS (>=80%) / MARGINAL / FAIL
                    │
                    ▼
         logs/test_results_<timestamp>.json


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 FILE STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 src/
   tunematcher.py   Entry point, logging setup, CLI, pipeline orchestration
   agent.py         LLM calls, prompt templates, preference parser, recommender, guardrail
   scoring.py       Song scoring algorithm, RAG retrieval
   testing.py       Test personas, evaluator, test runner
   songs.json       Song dataset
 logs/
   tunematcher.log  Debug + info log for every run
   sessions.jsonl   Structured record of every user request
   test_results_*.json  Reliability test output
```
