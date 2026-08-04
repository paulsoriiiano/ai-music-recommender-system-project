"""
Command line runner for the Music Recommender Simulation.

Run with: python -m src.main
Agentic mode: python -m src.main --agent "chill music for studying"
"""

import argparse
import logging
import sys

from src.agent import AgentConfigError, run_agentic_recommendation
from src.recommender import load_songs, recommend_songs

# A handful of distinct taste profiles, including one adversarial / conflicting
# profile, used to stress-test the scoring logic in Phase 4.
PROFILES = {
    "Default (Pop/Happy)": {"genre": "pop", "mood": "happy", "energy": 0.8},
    "High-Energy Pop": {"genre": "pop", "mood": "happy", "energy": 0.95},
    "Chill Lofi": {"genre": "lofi", "mood": "chill", "energy": 0.35, "likes_acoustic": True},
    "Deep Intense Rock": {"genre": "rock", "mood": "intense", "energy": 0.9},
    "Adversarial (Sad but High-Energy)": {"genre": "classical", "mood": "sad", "energy": 0.9},
}


def print_recommendations(profile_name: str, user_prefs: dict, recommendations: list) -> None:
    print(f"\n=== {profile_name} ===")
    print(f"User preferences: {user_prefs}\n")
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"{rank}. {song['title']} — Score: {score:.2f}")
        print(f"   Because: {explanation}")


def run_agent_mode(user_text: str, songs: list) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        result = run_agentic_recommendation(user_text, songs, k=5)
    except AgentConfigError as exc:
        print(f"Agent unavailable: {exc}")
        sys.exit(1)

    print(f"\n=== Agentic recommendation for: \"{user_text}\" ===")
    print(f"Parsed preferences: {result.final_prefs}")
    if result.retries:
        print(f"Retries: {result.retries}")
    for line in result.log:
        print(f"  · {line}")
    print(f"\n{result.explanation}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Music Recommender Simulation")
    parser.add_argument(
        "--agent",
        nargs="?",
        const="",
        default=None,
        help="Run the agentic workflow on a free-text taste description",
    )
    args = parser.parse_args()

    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")

    if args.agent is not None:
        user_text = args.agent or input("Describe the music you're in the mood for: ")
        run_agent_mode(user_text, songs)
        return

    for profile_name, user_prefs in PROFILES.items():
        recommendations = recommend_songs(user_prefs, songs, k=5)
        print_recommendations(profile_name, user_prefs, recommendations)


if __name__ == "__main__":
    main()
