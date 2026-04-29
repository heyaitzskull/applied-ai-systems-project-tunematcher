import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from groq import Groq

from agent import parse_user_preferences, get_ai_recommendations, validate_recommendations
from scoring import retrieve_candidates

logger = logging.getLogger("tunematcher")

LOG_DIR = Path("logs")

TEST_PERSONAS = [
    {
        "name": "Chill Lofi Student",
        "input": "I want background music for studying, nothing distracting, low energy and chill",
        "expected_genre_family": {"lofi", "electronic"},
        "expected_mood_family": {"chill", "focused"},
        "energy_max": 0.4,
        "intensity_max": 0.3,
    },
    {
        "name": "High Energy Gym Goer",
        "input": "I need something really intense to push through a tough workout, high energy rock or hip-hop",
        "expected_genre_family": {"rock", "hip-hop", "pop-rock", "indie-rock"},
        "expected_mood_family": {"energetic", "angry", "confident"},
        "energy_min": 0.65,
        "intensity_min": 0.6,
    },
    {
        "name": "Heartbreak Playlist Listener",
        "input": "just went through a breakup, want something sad and emotional",
        "expected_genre_family": {"pop", "pop-soul", "indie-pop", "folk", "r&b", "indie-rock"},
        "expected_mood_family": {"sad", "melancholy"},
        "energy_max": 0.6,
    },
    {
        "name": "Happy Party Vibes",
        "input": "I want upbeat happy music to dance to at a party, fun pop or funk",
        "expected_genre_family": {"pop", "funk", "electronic", "r&b"},
        "expected_mood_family": {"happy", "energetic"},
        "energy_min": 0.65,
        "valence_min": 0.6,
    },
    {
        "name": "Late Night Drive",
        "input": "music for a late night drive, moody and atmospheric, not too heavy",
        "expected_genre_family": {"electronic", "indie-pop", "indie-rock", "r&b", "hip-hop"},
        "expected_mood_family": {"chill", "melancholy", "nostalgic"},
        "intensity_max": 0.7,
    },
]


def score_song_for_test(song_title: str, songs: list[dict], persona: dict) -> dict:
    """Find a song by title and evaluate it against persona expectations."""
    song = next((s for s in songs if s["title"].lower() == song_title.lower()), None)
    if not song:
        return {"title": song_title, "found": False, "checks": {}}

    checks = {}
    if "expected_genre_family" in persona:
        checks["genre_ok"] = song["genre"] in persona["expected_genre_family"]
    if "expected_mood_family" in persona:
        checks["mood_ok"] = song["mood"] in persona["expected_mood_family"]
    if "energy_min" in persona:
        checks["energy_high_ok"] = song["energy"] >= persona["energy_min"]
    if "energy_max" in persona:
        checks["energy_low_ok"] = song["energy"] <= persona["energy_max"]
    if "intensity_min" in persona:
        checks["intensity_high_ok"] = song["intensity"] >= persona["intensity_min"]
    if "intensity_max" in persona:
        checks["intensity_low_ok"] = song["intensity"] <= persona["intensity_max"]
    if "valence_min" in persona:
        checks["valence_ok"] = song["valence"] >= persona["valence_min"]

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {"title": song_title, "found": True, "checks": checks, "passed": passed, "total": total}


def run_tests(client: Groq, songs: list[dict]):
    """Reliability test suite: run all personas and report pass/fail rates."""
    print("\n" + "=" * 60)
    print("  TUNEMATCHER 2.0: RELIABILITY TEST SUITE")
    print("=" * 60)

    results_log = []
    total_checks = 0
    passed_checks = 0

    for i, persona in enumerate(TEST_PERSONAS, 1):
        print(f"\n[Test {i}/{len(TEST_PERSONAS)}] {persona['name']}")
        print(f"  Input: \"{persona['input']}\"")

        try:
            prefs = parse_user_preferences(client, persona["input"])
            candidates = retrieve_candidates(songs, prefs, top_k=15)
            response_text, recommended_titles = get_ai_recommendations(
                client, persona["input"], prefs, candidates
            )
            valid = validate_recommendations(recommended_titles, candidates)

            print(f"  Guardrail: {'PASS' if valid else 'FAIL (hallucination detected)'}")
            print(f"  Recommended: {', '.join(recommended_titles) if recommended_titles else 'none parsed'}")

            persona_checks_passed = 0
            persona_checks_total = 0
            song_results = []

            for title in recommended_titles:
                result = score_song_for_test(title, songs, persona)
                song_results.append(result)
                if result["found"]:
                    p = result["passed"]
                    t = result["total"]
                    persona_checks_passed += p
                    persona_checks_total += t
                    check_str = ", ".join(
                        f"{'OK' if v else 'FAIL'} {k}" for k, v in result["checks"].items()
                    )
                    print(f"    - {title}: {p}/{t} checks: {check_str}")
                else:
                    print(f"    - {title}: NOT FOUND in dataset (guardrail issue)")

            total_checks += persona_checks_total
            passed_checks += persona_checks_passed

            pct = (persona_checks_passed / persona_checks_total * 100) if persona_checks_total else 0
            print(f"  Persona score: {persona_checks_passed}/{persona_checks_total} ({pct:.0f}%)")

            results_log.append({
                "persona": persona["name"],
                "guardrail_passed": valid,
                "checks_passed": persona_checks_passed,
                "checks_total": persona_checks_total,
                "songs": song_results,
            })

        except Exception as e:
            logger.error(f"Test failed for persona '{persona['name']}': {e}")
            print(f"  ERROR: {e}")

    print("\n" + "=" * 60)
    overall_pct = (passed_checks / total_checks * 100) if total_checks else 0
    print(f"  OVERALL RELIABILITY: {passed_checks}/{total_checks} checks passed ({overall_pct:.1f}%)")

    if overall_pct >= 80:
        verdict = "PASS - System is performing reliably"
    elif overall_pct >= 60:
        verdict = "MARGINAL - Some improvements needed"
    else:
        verdict = "FAIL - System needs significant improvement"
    print(f"  Verdict: {verdict}")
    print("=" * 60 + "\n")

    test_log_path = LOG_DIR / f"test_results_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    with open(test_log_path, "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_pct": overall_pct,
            "passed": passed_checks,
            "total": total_checks,
            "personas": results_log,
        }, f, indent=2)
    print(f"  Test results saved to: {test_log_path}")
