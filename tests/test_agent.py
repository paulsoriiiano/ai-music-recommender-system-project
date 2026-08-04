from unittest.mock import patch

from src.agent import (
    check_results,
    generate_explanation,
    parse_preferences,
    run_agentic_recommendation,
)

SONGS = [
    {
        "id": 1,
        "title": "Sunrise City",
        "artist": "Neon Echo",
        "genre": "pop",
        "mood": "happy",
        "energy": 0.82,
        "tempo_bpm": 118,
        "valence": 0.84,
        "danceability": 0.79,
        "acousticness": 0.18,
    },
    {
        "id": 2,
        "title": "Midnight Coding",
        "artist": "LoRoom",
        "genre": "lofi",
        "mood": "chill",
        "energy": 0.42,
        "tempo_bpm": 78,
        "valence": 0.56,
        "danceability": 0.62,
        "acousticness": 0.71,
    },
]


def test_check_results_flags_unknown_genre_and_low_score():
    prefs = {"genre": "opera", "mood": "chill", "energy": 0.5, "likes_acoustic": None}
    recommendations = [(SONGS[1], 0.5, "no strong matches")]
    ok, issues = check_results(prefs, recommendations, ["pop", "lofi"], ["happy", "chill"], k=5)
    assert not ok
    assert any("genre" in issue for issue in issues)
    assert any("score" in issue for issue in issues)
    assert any("5 requested results" in issue for issue in issues)


def test_check_results_passes_for_good_match():
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": None}
    recommendations = [(SONGS[0], 4.9, "genre match"), (SONGS[1], 1.0, "energy similarity")]
    ok, issues = check_results(prefs, recommendations, ["pop", "lofi"], ["happy", "chill"], k=2)
    assert ok
    assert issues == []


def test_parse_preferences_clamps_and_lowercases():
    with patch("src.agent._call_claude_json") as mock_call:
        mock_call.return_value = {
            "genre": "  POP ",
            "mood": "Happy",
            "energy": 5.0,
            "likes_acoustic": None,
        }
        prefs = parse_preferences("upbeat pop", ["pop", "lofi"], ["happy", "chill"])
    assert prefs["genre"] == "pop"
    assert prefs["mood"] == "happy"
    assert prefs["energy"] == 1.0
    assert prefs["likes_acoustic"] is None


def test_run_agentic_recommendation_retries_on_unknown_genre():
    with patch("src.agent._call_claude_json") as mock_json, patch(
        "src.agent._call_claude_text"
    ) as mock_text:
        mock_json.side_effect = [
            {"genre": "opera", "mood": "happy", "energy": 0.8, "likes_acoustic": None},
            {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": None},
        ]
        mock_text.return_value = "You'll love Sunrise City for its upbeat energy!"

        result = run_agentic_recommendation("upbeat happy pop", SONGS, k=2, max_retries=2)

    assert result.retries == 1
    assert result.final_prefs["genre"] == "pop"
    assert any("retry 1" in line for line in result.log)


def test_run_agentic_recommendation_stops_after_max_retries():
    with patch("src.agent._call_claude_json") as mock_json, patch(
        "src.agent._call_claude_text"
    ) as mock_text:
        mock_json.return_value = {
            "genre": "opera",
            "mood": "sad",
            "energy": 0.8,
            "likes_acoustic": None,
        }
        mock_text.return_value = "Here's a mix based on what's available."

        result = run_agentic_recommendation("obscure opera", SONGS, k=2, max_retries=2)

    assert result.retries == 2
    assert result.recommendations is not None


def test_generate_explanation_falls_back_when_ungrounded():
    recommendations = [(SONGS[0], 4.9, "genre match"), (SONGS[1], 1.0, "energy similarity")]
    with patch("src.agent._call_claude_text") as mock_text:
        mock_text.return_value = "You'll enjoy 'Totally Made Up Song' a lot!"
        explanation = generate_explanation(
            "upbeat pop", {"genre": "pop", "mood": "happy"}, recommendations
        )
    assert "Sunrise City" in explanation
    assert "Made Up Song" not in explanation
