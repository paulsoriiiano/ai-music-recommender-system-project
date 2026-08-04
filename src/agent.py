"""
Agentic workflow layer on top of the content-based recommender.

Flow: parse free-text taste into structured preferences (LLM, structured
output) -> score with the existing recommender -> self-check the results
against the catalog -> revise and retry if the self-check fails -> write a
natural-language explanation grounded only in the actual scored results.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import anthropic

from src.recommender import recommend_songs

logger = logging.getLogger("music_recommender.agent")

DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5")
MIN_ACCEPTABLE_SCORE = 2.0

PREFERENCES_SCHEMA = {
    "type": "object",
    "properties": {
        "genre": {"type": "string"},
        "mood": {"type": "string"},
        "energy": {"type": "number"},
        "likes_acoustic": {"type": ["boolean", "null"]},
    },
    "required": ["genre", "mood", "energy", "likes_acoustic"],
    "additionalProperties": False,
}


class AgentConfigError(Exception):
    """Raised when the agent can't be configured (e.g. missing API key)."""


@dataclass
class AgentResult:
    user_text: str
    final_prefs: Dict
    retries: int
    recommendations: List[Tuple[Dict, float, str]]
    explanation: str
    log: List[str] = field(default_factory=list)


def _get_client() -> anthropic.Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise AgentConfigError(
            "ANTHROPIC_API_KEY is not set. Get an API key from the Anthropic "
            "Console and run `export ANTHROPIC_API_KEY=...` before using --agent."
        )
    return anthropic.Anthropic()


def _call_claude_json(system: str, user: str, schema: Dict) -> Dict:
    """Structured-output call. Returns the parsed JSON object. Isolated so tests can mock it."""
    client = _get_client()
    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    import json

    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)


def _call_claude_text(system: str, user: str) -> str:
    """Plain-text call. Isolated so tests can mock it."""
    client = _get_client()
    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return next(block.text for block in response.content if block.type == "text")


def _clamp_prefs(prefs: Dict) -> Dict:
    prefs = dict(prefs)
    prefs["genre"] = str(prefs.get("genre", "")).strip().lower()
    prefs["mood"] = str(prefs.get("mood", "")).strip().lower()
    prefs["energy"] = max(0.0, min(1.0, float(prefs.get("energy", 0.5))))
    likes_acoustic = prefs.get("likes_acoustic")
    prefs["likes_acoustic"] = None if likes_acoustic is None else bool(likes_acoustic)
    return prefs


def parse_preferences(user_text: str, known_genres: List[str], known_moods: List[str]) -> Dict:
    system = (
        "You extract a music taste profile from free text. Only use genre and "
        "mood values from the provided catalog lists - never invent one. "
        f"Known genres: {', '.join(known_genres)}. Known moods: {', '.join(known_moods)}. "
        "energy is a float between 0.0 (calm) and 1.0 (intense). "
        "likes_acoustic is true, false, or null if unstated."
    )
    raw = _call_claude_json(system, user_text, PREFERENCES_SCHEMA)
    prefs = _clamp_prefs(raw)
    logger.info("parsed preferences: %s", prefs)
    return prefs


def check_results(
    user_prefs: Dict,
    recommendations: List[Tuple[Dict, float, str]],
    known_genres: List[str],
    known_moods: List[str],
    k: int,
) -> Tuple[bool, List[str]]:
    issues = []
    if user_prefs["genre"] not in known_genres:
        issues.append(f"genre '{user_prefs['genre']}' is not in the catalog")
    if user_prefs["mood"] not in known_moods:
        issues.append(f"mood '{user_prefs['mood']}' is not in the catalog")
    if len(recommendations) < k:
        issues.append(f"only {len(recommendations)} of {k} requested results found")
    if recommendations and recommendations[0][1] < MIN_ACCEPTABLE_SCORE:
        issues.append(f"top score {recommendations[0][1]:.2f} is below the {MIN_ACCEPTABLE_SCORE} threshold")
    ok = not issues
    logger.info("self-check %s: %s", "passed" if ok else "failed", issues)
    return ok, issues


def revise_preferences(
    user_text: str,
    user_prefs: Dict,
    issues: List[str],
    known_genres: List[str],
    known_moods: List[str],
) -> Dict:
    system = (
        "You previously extracted a music taste profile from free text, but it "
        "had issues. Revise it to fix the issues while staying true to the "
        "user's original request. Only use genre and mood values from the "
        f"provided catalog lists. Known genres: {', '.join(known_genres)}. "
        f"Known moods: {', '.join(known_moods)}."
    )
    user = (
        f"Original request: {user_text}\n"
        f"Previous attempt: {user_prefs}\n"
        f"Issues found: {'; '.join(issues)}"
    )
    raw = _call_claude_json(system, user, PREFERENCES_SCHEMA)
    prefs = _clamp_prefs(raw)
    logger.info("revised preferences: %s", prefs)
    return prefs


def generate_explanation(
    user_text: str, user_prefs: Dict, recommendations: List[Tuple[Dict, float, str]]
) -> str:
    catalog_titles = {song["title"] for song, _, _ in recommendations}
    lines = "\n".join(
        f"- {song['title']} by {song['artist']} (score {score:.2f}): {reasons}"
        for song, score, reasons in recommendations
    )
    system = (
        "You write a short, friendly recommendation summary for a user. You "
        "may ONLY mention songs from the provided list, using their exact "
        "titles - never invent or add songs. Ground every claim in the given "
        "scores and reasons."
    )
    user = (
        f"The user asked for: {user_text}\n"
        f"Matched preferences: {user_prefs}\n"
        f"Top results:\n{lines}\n\n"
        "Write 2-4 sentences recommending these songs, referencing why they fit."
    )
    text = _call_claude_text(system, user)

    # Grounding guardrail: the response must reference at least one of the
    # songs it was actually given, or we assume it hallucinated and fall back.
    if not any(title in text for title in catalog_titles):
        logger.warning("explanation failed grounding check; falling back to deterministic text")
        return _deterministic_explanation(recommendations)
    return text


def _deterministic_explanation(recommendations: List[Tuple[Dict, float, str]]) -> str:
    lines = [
        f"{i}. {song['title']} — Score: {score:.2f} ({reasons})"
        for i, (song, score, reasons) in enumerate(recommendations, start=1)
    ]
    return "\n".join(lines)


def run_agentic_recommendation(
    user_text: str, songs: List[Dict], k: int = 5, max_retries: int = 2
) -> AgentResult:
    known_genres = sorted({s["genre"].lower() for s in songs})
    known_moods = sorted({s["mood"].lower() for s in songs})
    log: List[str] = []

    try:
        prefs = parse_preferences(user_text, known_genres, known_moods)
        log.append(f"parsed preferences: {prefs}")
    except (anthropic.APIError, anthropic.APIConnectionError) as exc:
        logger.error("LLM call failed during parsing: %s", exc)
        log.append(f"LLM parsing failed ({exc}); falling back to a default profile")
        prefs = _clamp_prefs({"genre": known_genres[0], "mood": known_moods[0], "energy": 0.5, "likes_acoustic": None})

    recommendations = recommend_songs(_to_user_prefs_dict(prefs), songs, k=k)
    ok, issues = check_results(prefs, recommendations, known_genres, known_moods, k)

    retries = 0
    while not ok and retries < max_retries:
        retries += 1
        log.append(f"retry {retries}: self-check failed ({'; '.join(issues)})")
        try:
            prefs = revise_preferences(user_text, prefs, issues, known_genres, known_moods)
        except (anthropic.APIError, anthropic.APIConnectionError) as exc:
            logger.error("LLM call failed during revision: %s", exc)
            log.append(f"LLM revision failed ({exc}); stopping retries")
            break
        recommendations = recommend_songs(_to_user_prefs_dict(prefs), songs, k=k)
        ok, issues = check_results(prefs, recommendations, known_genres, known_moods, k)

    try:
        explanation = generate_explanation(user_text, prefs, recommendations)
    except (anthropic.APIError, anthropic.APIConnectionError) as exc:
        logger.error("LLM call failed during explanation: %s", exc)
        log.append(f"LLM explanation failed ({exc}); using deterministic explanation")
        explanation = _deterministic_explanation(recommendations)

    return AgentResult(
        user_text=user_text,
        final_prefs=prefs,
        retries=retries,
        recommendations=recommendations,
        explanation=explanation,
        log=log,
    )


def _to_user_prefs_dict(prefs: Dict) -> Dict:
    return {
        "genre": prefs["genre"],
        "mood": prefs["mood"],
        "energy": prefs["energy"],
        "likes_acoustic": prefs["likes_acoustic"],
    }
