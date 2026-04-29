import logging

logger = logging.getLogger("tunematcher")

GENRE_FAMILIES = {
    "pop":         {"pop", "indie-pop", "pop-rock", "pop-soul", "pop-country", "funk"},
    "rock":        {"rock", "indie-rock", "pop-rock", "folk-rock", "metal"},
    "hip-hop":     {"hip-hop", "r&b", "trap"},
    "r&b":         {"r&b", "hip-hop", "funk", "pop-soul"},
    "electronic":  {"electronic", "lofi"},
    "lofi":        {"lofi", "electronic"},
    "folk":        {"folk", "folk-rock", "indie-pop", "indie-rock"},
    "indie":       {"indie-pop", "indie-rock", "folk"},
    "funk":        {"funk", "r&b", "pop"},
    "afrobeats":   {"afrobeats", "r&b", "pop"},
}

MOOD_FAMILIES = {
    "happy":      {"happy", "energetic", "confident"},
    "sad":        {"sad", "melancholy", "nostalgic"},
    "chill":      {"chill", "focused", "relaxed"},
    "energetic":  {"energetic", "happy", "confident", "angry"},
    "melancholy": {"melancholy", "sad", "nostalgic"},
    "focused":    {"focused", "chill"},
    "angry":      {"angry", "energetic", "passionate"},
    "romantic":   {"romantic", "passionate"},
    "confident":  {"confident", "energetic", "happy"},
    "nostalgic":  {"nostalgic", "melancholy", "romantic"},
    "passionate": {"passionate", "romantic", "angry"},
    "epic":       {"epic", "passionate", "energetic"},
}


def genre_score(song_genre: str, preferred_genre: str) -> float:
    if song_genre == preferred_genre:
        return 1.0
    family = GENRE_FAMILIES.get(preferred_genre, set())
    if song_genre in family:
        return 0.6
    return 0.0


def mood_score(song_mood: str, preferred_mood: str) -> float:
    if song_mood == preferred_mood:
        return 1.0
    family = MOOD_FAMILIES.get(preferred_mood, set())
    if song_mood in family:
        return 0.5
    return 0.0


def normalized_distance_score(value: float, target: float, max_diff: float) -> float:
    if max_diff == 0:
        return 1.0
    return max(0.0, 1.0 - abs(value - target) / max_diff)


def score_song(song: dict, prefs: dict) -> float:
    """Weights: genre=0.28, mood=0.24, tempo=0.14, acousticness=0.12, valence=0.12, energy=0.06, intensity=0.04"""
    g = genre_score(song["genre"], prefs.get("genre", ""))
    m = mood_score(song["mood"], prefs.get("mood", ""))
    t = normalized_distance_score(song["tempo"],        prefs.get("tempo", 100),      100)
    a = normalized_distance_score(song["acousticness"], prefs.get("acousticness", 0.5), 1)
    v = normalized_distance_score(song["valence"],      prefs.get("valence", 0.5),      1)
    e = normalized_distance_score(song["energy"],       prefs.get("energy", 0.5),       1)
    i = normalized_distance_score(song["intensity"],    prefs.get("intensity", 0.5),    1)
    return (0.28 * g + 0.24 * m + 0.14 * t +
            0.12 * a + 0.12 * v + 0.06 * e + 0.04 * i)


def retrieve_candidates(songs: list[dict], prefs: dict, top_k: int = 15) -> list[dict]:
    """RAG retrieval: score all songs and return top_k candidates to pass to the LLM."""
    scored = [{**song, "_score": round(score_song(song, prefs), 4)} for song in songs]
    candidates = sorted(scored, key=lambda x: x["_score"], reverse=True)[:top_k]
    logger.debug(
        f"RAG retrieved {len(candidates)} candidates. "
        f"Top score: {candidates[0]['_score']}, Bottom score: {candidates[-1]['_score']}"
    )
    return candidates
