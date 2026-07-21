"""
Command line runner for the Music Recommender Simulation.

Run with: python -m src.main
"""

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


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")

    for profile_name, user_prefs in PROFILES.items():
        recommendations = recommend_songs(user_prefs, songs, k=5)
        print_recommendations(profile_name, user_prefs, recommendations)


if __name__ == "__main__":
    main()
