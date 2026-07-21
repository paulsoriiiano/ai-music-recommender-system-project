# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

This version is a **content-based recommender**: it never looks at what other users liked
(that would be collaborative filtering). Instead it compares each song's own attributes
(genre, mood, energy, acousticness) directly against a single user's stated taste profile,
scores every song in the catalog, and returns the top matches with a plain-language
explanation of why each song was picked.

---

## How The System Works

Real platforms like Spotify or YouTube blend two big ideas: **collaborative filtering**
(predicting what you'll like based on what similar *users* listened to, liked, or skipped)
and **content-based filtering** (predicting what you'll like based on the *attributes* of
the songs themselves — genre, tempo, mood, acoustic qualities). Production systems mix
both, plus signals like skip rate, replay count, and playlist co-occurrence, because
content attributes alone can't capture "songs listened to by people like you."

This simulation only implements the content-based half. It represents a user's taste as
a small set of target values and scores every song by how closely its own attributes
match those targets. There's no notion of other users at all — every recommendation is
explainable purely from the song's own data and the user's own stated preferences.

**Features used by `Song` / song dict:** `genre`, `mood`, `energy`, `tempo_bpm`, `valence`,
`danceability`, `acousticness`.

**Features used by `UserProfile` / user_prefs:** `favorite_genre` (`genre`), `favorite_mood`
(`mood`), `target_energy` (`energy`), and an optional `likes_acoustic` flag.

**Algorithm Recipe** (see `score_song()` / `Recommender._score()` in `src/recommender.py`):

- **+2.0 points** if the song's genre matches the user's favorite genre.
- **+1.0 point** if the song's mood matches the user's favorite mood.
- **Up to +2.0 similarity points** for energy, calculated as
  `2.0 * (1 - abs(song.energy - target_energy))` — a song exactly at the user's target
  energy earns the full 2.0, and points shrink the further away it gets. This rewards
  *closeness*, not just "high energy," so a user who wants energy `0.35` is correctly
  matched to mellow songs, not maxed-out ones.
- **+1.0 point** if the user likes acoustic music and the song's acousticness is `>= 0.6`.
- **+0.5 points** if the user prefers non-acoustic music and the song's acousticness is
  `<= 0.3`.

Genre was weighted highest because it's the strongest, least ambiguous taste signal
(nobody who says "I want rock" wants ambient piano), followed by energy (a continuous
"vibe" signal), then mood (a genre/mood combination usually implies overlapping songs
already, so mood is a smaller supplementary signal).

A **Scoring Rule** (`score_song`) only judges *one* song at a time and returns a raw
number plus the reasons behind it. A **Ranking Rule** (`recommend_songs` /
`Recommender.recommend`) is a separate step: it runs the scoring rule over *every* song
in the catalog, then sorts the whole list to produce a Top-K result. You need both,
because scoring answers "how good is this song for this user?" while ranking answers
"which songs are best, relative to everything else available?" — a task no single-song
score can answer alone.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output

```
Loaded songs: 18

=== Default (Pop/Happy) ===
User preferences: {'genre': 'pop', 'mood': 'happy', 'energy': 0.8}

1. Sunrise City — Score: 4.96
   Because: genre match (+2.0), mood match (+1.0), energy similarity (+1.96)
2. Gym Hero — Score: 3.74
   Because: genre match (+2.0), energy similarity (+1.74)
3. Rooftop Lights — Score: 2.92
   Because: mood match (+1.0), energy similarity (+1.92)
4. Night Drive Loop — Score: 1.90
   Because: energy similarity (+1.90)
5. Street Cypher — Score: 1.80
   Because: energy similarity (+1.80)

=== High-Energy Pop ===
User preferences: {'genre': 'pop', 'mood': 'happy', 'energy': 0.95}

1. Sunrise City — Score: 4.74
   Because: genre match (+2.0), mood match (+1.0), energy similarity (+1.74)
2. Gym Hero — Score: 3.96
   Because: genre match (+2.0), energy similarity (+1.96)
3. Rooftop Lights — Score: 2.62
   Because: mood match (+1.0), energy similarity (+1.62)
4. Neon Pulse — Score: 2.00
   Because: energy similarity (+2.00)
5. Riot Engine — Score: 1.96
   Because: energy similarity (+1.96)

=== Chill Lofi ===
User preferences: {'genre': 'lofi', 'mood': 'chill', 'energy': 0.35, 'likes_acoustic': True}

1. Library Rain — Score: 6.00
   Because: genre match (+2.0), mood match (+1.0), energy similarity (+2.00), matches acoustic preference (+1.0)
2. Midnight Coding — Score: 5.86
   Because: genre match (+2.0), mood match (+1.0), energy similarity (+1.86), matches acoustic preference (+1.0)
3. Focus Flow — Score: 4.90
   Because: genre match (+2.0), energy similarity (+1.90), matches acoustic preference (+1.0)
4. Spacewalk Thoughts — Score: 3.86
   Because: mood match (+1.0), energy similarity (+1.86), matches acoustic preference (+1.0)
5. Coffee Shop Stories — Score: 2.96
   Because: energy similarity (+1.96), matches acoustic preference (+1.0)

=== Deep Intense Rock ===
User preferences: {'genre': 'rock', 'mood': 'intense', 'energy': 0.9}

1. Storm Runner — Score: 4.98
   Because: genre match (+2.0), mood match (+1.0), energy similarity (+1.98)
2. Gym Hero — Score: 2.94
   Because: mood match (+1.0), energy similarity (+1.94)
3. Neon Pulse — Score: 1.90
   Because: energy similarity (+1.90)
4. Riot Engine — Score: 1.86
   Because: energy similarity (+1.86)
5. Sunrise City — Score: 1.84
   Because: energy similarity (+1.84)

=== Adversarial (Sad but High-Energy) ===
User preferences: {'genre': 'classical', 'mood': 'sad', 'energy': 0.9}

1. Autumn Piano — Score: 2.50
   Because: genre match (+2.0), energy similarity (+0.50)
2. Storm Runner — Score: 1.98
   Because: energy similarity (+1.98)
3. Gym Hero — Score: 1.94
   Because: energy similarity (+1.94)
4. Neon Pulse — Score: 1.90
   Because: energy similarity (+1.90)
5. Riot Engine — Score: 1.86
   Because: energy similarity (+1.86)
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Experiments You Tried

**Weight Shift** — I halved `GENRE_WEIGHT` (2.0 → 1.0) and doubled `ENERGY_WEIGHT`
(2.0 → 4.0), then re-ran the "Default (Pop/Happy)" profile (`genre=pop, mood=happy,
energy=0.8`):

```
Sunrise City — 5.92 — genre match (+1.0), mood match (+1.0), energy similarity (+3.92)
Rooftop Lights — 4.84 — mood match (+1.0), energy similarity (+3.84)
Gym Hero — 4.48 — genre match (+1.0), energy similarity (+3.48)
Night Drive Loop — 3.80 — energy similarity (+3.80)
Street Cypher — 3.60 — energy similarity (+3.60)
```

With the original weights, the top 5 were all pop, mood-matched, or both. After the
shift, **Night Drive Loop** (synthwave) and **Street Cypher** (hip-hop) climb into the
top 5 purely because their energy is close to 0.8 — neither shares the user's genre or
mood at all. This confirms the system is very sensitive to relative weighting: genre
dominance is a *design choice*, not an inherent property of the data, and a small weight
change can pull in completely different genres just because their energy happens to
line up.

- Adding `tempo_bpm` or `valence` to the score was **not** attempted in the committed
  code, but would let the system distinguish, e.g., a slow sad pop song from a fast happy
  one — right now two songs with the same genre/mood/energy but very different tempo or
  valence score identically.
- Different profile "types" (see the CLI output above) behave as expected: energetic
  genre-specific profiles surface genre-appropriate high-energy songs, while the
  adversarial classical/sad/high-energy profile falls back almost entirely on energy
  similarity, since nothing in the catalog matches its mood.

---

## Limitations and Risks

- It only works on a tiny catalog (18 songs) — real platforms score millions of tracks,
  so the "cold start" effect here is exaggerated.
- It does not understand lyrics, artist identity/popularity, or listening history —
  purely metadata (genre/mood/energy/acousticness).
- It might over favor one genre or mood, since `genre` carries double the weight of
  `mood` by design.
- Because it's content-based only, it can't do "people who liked X also liked Y" —
  it will never recommend something outside a user's stated preferences, which risks a
  filter bubble.

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Building this recommender made concrete something that's easy to wave your hands at:
"recommendation" is really just "score everything, then sort." Once `score_song` exists,
`recommend_songs` is a two-line loop-and-sort — nearly all the actual product decisions
(what data to collect, how much to weight each signal) live in the scoring rule, not in
any clever ranking algorithm.

The bias risk became obvious once I ran the adversarial and weight-shift experiments:
whatever numeric weight you assign to a feature *is* the recommender's opinion about what
matters, and if your dataset over-represents a genre (here, `pop` and `lofi` each account
for a large share of the 18 songs), a strong genre weight will systematically push those
genres to the top for almost every profile, regardless of the user's second-order
preferences like mood or acousticness. A real-world system trained on skewed listening
data could bake in the same imbalance far less visibly, since there's no "genre weight"
you can read out of a black-box ranking model.
