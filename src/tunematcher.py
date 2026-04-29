"""
TuneMatcher 2.0 - AI-Powered Music Recommender (Groq Edition)
Complete applied AI system with RAG, agentic workflow, logging, and reliability testing.

Requirements:
    pip install groq python-dotenv

Setup:
    1. Get a free API key at https://console.groq.com
    2. Add it to .env: GROQ_API_KEY=your-key-here

Usage:
    python tunematcher.py              # Interactive mode
    python tunematcher.py --test       # Run reliability test suite
"""

import json
import os
import sys
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

# Logging setup (before local imports so handlers are ready when modules load)
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("tunematcher")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(LOG_DIR / "tunematcher.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(message)s"))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

from agent import parse_user_preferences, get_ai_recommendations, validate_recommendations
from scoring import retrieve_candidates
from testing import run_tests

SONGS_PATH = Path(__file__).parent.parent / "data" / "songs.json"
SESSION_LOG_PATH = LOG_DIR / "sessions.jsonl"

BANNER = """
+----------------------------------------------+
|         TuneMatcher 2.0                      |
|   AI-Powered Music Recommender               |
|   Powered by Groq (Free!)                    |
|   Type what you're looking for, or 'quit'    |
+----------------------------------------------+
"""

EXAMPLES = [
    "something chill to study to, low energy",
    "I want angry rock music to vent",
    "happy danceable pop for a party",
    "sad songs for a breakup",
    "focus music without lyrics",
    "late night moody hip-hop",
]


def load_songs() -> list[dict]:
    if not SONGS_PATH.exists():
        logger.error(f"Song dataset not found at {SONGS_PATH}")
        sys.exit(1)
    with open(SONGS_PATH) as f:
        songs = json.load(f)
    logger.debug(f"Loaded {len(songs)} songs from dataset.")
    return songs


def log_session(user_input: str, prefs: dict, candidates: list[dict], response: str, valid: bool):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_input": user_input,
        "parsed_prefs": prefs,
        "top_candidate_titles": [c["title"] for c in candidates[:5]],
        "guardrail_passed": valid,
        "response_length": len(response),
    }
    with open(SESSION_LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
    logger.debug(f"Session logged to {SESSION_LOG_PATH}")


def run_recommendation(client: Groq, songs: list[dict], user_input: str) -> str:
    logger.info("-" * 50)
    logger.info(f"New request: {user_input!r}")

    prefs = parse_user_preferences(client, user_input)
    print(
        f"[Parser]    genre={prefs.get('genre')}, mood={prefs.get('mood')}, "
        f"energy={prefs.get('energy')}, tempo={prefs.get('tempo')} BPM"
    )

    candidates = retrieve_candidates(songs, prefs, top_k=15)
    top_titles = ", ".join(c["title"] for c in candidates[:5])
    print(f"[RAG]       Top candidates: {top_titles} ...")

    response_text, recommended_titles = get_ai_recommendations(client, user_input, prefs, candidates)

    valid = validate_recommendations(recommended_titles, candidates)
    print(f"[Guardrail] {'PASS — all picks found in candidate pool' if valid else 'FAIL — possible hallucination detected'}")
    print()

    if not valid:
        response_text += (
            "\n\nNote: Some recommendations may not have been found in the dataset. "
            "Please verify the suggestions above."
        )

    log_session(user_input, prefs, candidates, response_text, valid)
    return response_text


def interactive_mode(client: Groq, songs: list[dict]):
    print(BANNER)
    print("Example requests:")
    for ex in EXAMPLES:
        print(f"  - {ex}")
    print()

    while True:
        try:
            user_input = input("What kind of music do you want? > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        print("\nFinding your music...\n")
        try:
            result = run_recommendation(client, songs, user_input)
            print(result)
            print()
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            print(f"Something went wrong: {e}")


def main():
    parser = argparse.ArgumentParser(description="TuneMatcher 2.0 - AI Music Recommender (Groq)")
    parser.add_argument("--test", action="store_true", help="Run reliability test suite")
    args = parser.parse_args()

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY environment variable is not set.")
        print("  1. Get a free key at: https://console.groq.com")
        print("  2. Set it with: export GROQ_API_KEY=your-key-here")
        sys.exit(1)

    client = Groq(api_key=api_key)
    songs = load_songs()

    if args.test:
        run_tests(client, songs)
    else:
        interactive_mode(client, songs)


if __name__ == "__main__":
    main()
