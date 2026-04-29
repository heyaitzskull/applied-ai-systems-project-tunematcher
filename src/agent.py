import json
import logging

from groq import Groq

logger = logging.getLogger("tunematcher")

MODEL = "llama-3.3-70b-versatile"

PARSE_SYSTEM = """You are a music preference parser for TuneMatcher, an AI music recommender.

Your job is to extract structured music preferences from natural language input.

Return ONLY valid JSON with these exact keys (no markdown, no explanation, no code fences):
{
  "genre": string,         // one of: pop, rock, hip-hop, r&b, electronic, lofi, folk, indie, funk, afrobeats, pop-rock, indie-pop, indie-rock, folk-rock, pop-soul, pop-country
  "mood": string,          // one of: happy, sad, chill, energetic, melancholy, focused, angry, romantic, confident, nostalgic, passionate, epic
  "tempo": number,         // BPM integer 60-200
  "acousticness": number,  // 0.0 to 1.0
  "valence": number,       // 0.0 (dark) to 1.0 (positive)
  "energy": number,        // 0.0 to 1.0
  "intensity": number,     // 0.0 to 1.0 (0=soft, 1=aggressive)
  "parsed_intent": string  // one-sentence summary of what the user wants
}

Defaults if not mentioned: tempo=100, acousticness=0.4, valence=0.5, energy=0.5, intensity=0.5
Map user descriptions sensibly (e.g., "chill study music" -> lofi/focused/low energy).
Return ONLY the JSON object. No other text."""

RECOMMEND_SYSTEM = """You are TuneMatcher, an expert AI music recommender with deep knowledge of music theory, mood, and listener psychology.

You will receive:
1. What the user asked for
2. A list of pre-scored candidate songs (retrieved by the RAG system)
3. The parsed listener preferences

Your job (agentic reasoning):
1. ANALYZE the candidate list carefully, don't just pick the highest score
2. SELF-CHECK: Flag if any top-scored song seems like a poor mood/energy fit despite high score
3. PICK the best 3 songs for this listener
4. EXPLAIN each recommendation naturally, connecting it to what they asked for

Format your response EXACTLY like this (use these headers):

## Your Recommendations

**1. [Song Title] - [Artist]**
[2-3 sentence explanation connecting this song to the user's request. Be specific about WHY it fits.]

**2. [Song Title] - [Artist]**
[2-3 sentence explanation]

**3. [Song Title] - [Artist]**
[2-3 sentence explanation]

## Why These Work For You
[1-2 sentences about the overall theme/vibe of these picks and how they serve the listener's mood/context]

IMPORTANT GUARDRAIL: You may ONLY recommend songs that appear in the candidate list provided. Do not invent songs or recommend anything outside the list. If the top-scored songs are genuinely poor fits, choose lower-scored candidates that better match the intent."""


def call_groq(client: Groq, system_prompt: str, user_message: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=1000,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def parse_user_preferences(client: Groq, user_input: str) -> dict:
    """Step 1: parse natural language into structured prefs."""
    logger.debug(f"Parsing user input: {user_input!r}")
    try:
        raw = call_groq(client, PARSE_SYSTEM, user_input)
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        prefs = json.loads(raw)
        logger.debug(f"Parsed preferences: {prefs}")
        return prefs
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Failed to parse preferences: {e}. Using defaults.")
        return {
            "genre": "pop", "mood": "happy", "tempo": 100,
            "acousticness": 0.4, "valence": 0.5, "energy": 0.5,
            "intensity": 0.5, "parsed_intent": user_input,
        }


def get_ai_recommendations(
    client: Groq,
    user_input: str,
    prefs: dict,
    candidates: list[dict],
) -> tuple[str, list[str]]:
    """Step 2: LLM reasons over candidates and returns (response_text, recommended_titles)."""
    candidate_summary = "\n".join(
        f"- \"{s['title']}\" by {s['artist']} | genre={s['genre']}, mood={s['mood']}, "
        f"energy={s['energy']}, intensity={s['intensity']}, score={s['_score']}"
        for s in candidates
    )
    user_message = f"""User asked: "{user_input}"

Parsed preferences: {json.dumps({k: v for k, v in prefs.items() if k != 'parsed_intent'}, indent=2)}
Intent summary: {prefs.get('parsed_intent', user_input)}

Candidate songs (pre-scored by TuneMatcher algorithm):
{candidate_summary}

Please analyze these candidates and give your top 3 recommendations with explanations."""

    logger.debug("Sending candidate context to LLM for agentic reasoning.")
    response_text = call_groq(client, RECOMMEND_SYSTEM, user_message)

    recommended = []
    for line in response_text.split("\n"):
        if line.startswith("**") and "-" in line:
            try:
                title = line.split("**")[1].split("-")[0].strip().strip('"\'')
                if ". " in title:
                    title = title.split(". ", 1)[1].strip('"\'')
                recommended.append(title)
            except IndexError:
                pass

    logger.debug(f"LLM recommended titles: {recommended}")
    return response_text, recommended


def validate_recommendations(recommended_titles: list[str], candidates: list[dict]) -> bool:
    """Guardrail: ensure the LLM only recommended songs from the candidate pool."""
    candidate_titles_lower = {s["title"].lower() for s in candidates}
    all_valid = True
    for title in recommended_titles:
        if title.lower() not in candidate_titles_lower:
            logger.warning(f"GUARDRAIL TRIGGERED: '{title}' not in candidate pool. Possible hallucination.")
            all_valid = False
    if all_valid and recommended_titles:
        logger.debug("Guardrail check passed: all recommendations are from candidate pool.")
    return all_valid
