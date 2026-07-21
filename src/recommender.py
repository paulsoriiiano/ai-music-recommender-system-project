import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# --- Algorithm Recipe ---
# +2.0 points for a genre match
# +1.0 point for a mood match
# up to +2.0 points for energy similarity (closer to the user's target energy scores higher)
# +1.0 point if the user likes acoustic songs and the song is acoustic (acousticness >= 0.6)
# +0.5 points if the user does not like acoustic songs and the song is not acoustic (acousticness <= 0.3)
GENRE_WEIGHT = 2.0
MOOD_WEIGHT = 1.0
ENERGY_WEIGHT = 2.0
ACOUSTIC_BONUS = 1.0
NON_ACOUSTIC_BONUS = 0.5
ACOUSTIC_THRESHOLD = 0.6
NON_ACOUSTIC_THRESHOLD = 0.3


@dataclass
class Song:
    """Represents a song and its attributes."""
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    """Represents a user's taste preferences."""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


def _score(
    genre: str,
    mood: str,
    energy: float,
    acousticness: float,
    favorite_genre: str,
    favorite_mood: str,
    target_energy: float,
    likes_acoustic: Optional[bool] = None,
) -> Tuple[float, List[str]]:
    """Core scoring logic shared by the dict-based and OOP recommender APIs."""
    score = 0.0
    reasons: List[str] = []

    if genre.lower() == favorite_genre.lower():
        score += GENRE_WEIGHT
        reasons.append(f"genre match (+{GENRE_WEIGHT:.1f})")

    if mood.lower() == favorite_mood.lower():
        score += MOOD_WEIGHT
        reasons.append(f"mood match (+{MOOD_WEIGHT:.1f})")

    energy_gap = abs(energy - target_energy)
    energy_points = ENERGY_WEIGHT * (1 - energy_gap)
    if energy_points > 0:
        score += energy_points
        reasons.append(f"energy similarity (+{energy_points:.2f})")

    if likes_acoustic is True and acousticness >= ACOUSTIC_THRESHOLD:
        score += ACOUSTIC_BONUS
        reasons.append(f"matches acoustic preference (+{ACOUSTIC_BONUS:.1f})")
    elif likes_acoustic is False and acousticness <= NON_ACOUSTIC_THRESHOLD:
        score += NON_ACOUSTIC_BONUS
        reasons.append(f"matches non-acoustic preference (+{NON_ACOUSTIC_BONUS:.1f})")

    return round(score, 2), reasons


class Recommender:
    """OOP implementation of the recommendation logic."""

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top-k songs ranked by score for this user."""
        scored = [
            (song, _score(
                song.genre, song.mood, song.energy, song.acousticness,
                user.favorite_genre, user.favorite_mood, user.target_energy,
                user.likes_acoustic,
            )[0])
            for song in self.songs
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [song for song, _ in scored[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a human-readable explanation of a song's score for this user."""
        score, reasons = _score(
            song.genre, song.mood, song.energy, song.acousticness,
            user.favorite_genre, user.favorite_mood, user.target_energy,
            user.likes_acoustic,
        )
        if not reasons:
            return f"Score {score:.2f}: no strong matches with your preferences."
        return f"Score {score:.2f}: " + ", ".join(reasons)


def load_songs(csv_path: str) -> List[Dict]:
    """Load songs from a CSV file into a list of dicts with numeric fields converted."""
    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["id"] = int(row["id"])
            row["energy"] = float(row["energy"])
            row["tempo_bpm"] = float(row["tempo_bpm"])
            row["valence"] = float(row["valence"])
            row["danceability"] = float(row["danceability"])
            row["acousticness"] = float(row["acousticness"])
            songs.append(row)
    return songs


def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score a single song dict against a user_prefs dict, returning (score, reasons)."""
    return _score(
        song["genre"], song["mood"], song["energy"], song["acousticness"],
        user_prefs["genre"], user_prefs["mood"], user_prefs["energy"],
        user_prefs.get("likes_acoustic"),
    )


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Score every song, then return the top-k as (song, score, explanation) sorted descending."""
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = ", ".join(reasons) if reasons else "no strong matches"
        scored.append((song, score, explanation))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:k]
