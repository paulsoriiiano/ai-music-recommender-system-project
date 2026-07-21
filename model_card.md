# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**VibeFinder 1.0**

---

## 2. Intended Use

VibeFinder is a classroom simulation of a content-based music recommender. Given a
small "taste profile" (favorite genre, favorite mood, target energy, and whether the
user likes acoustic songs), it scores every song in a small catalog and returns the
top-K matches with a plain-language explanation for each.

- It assumes the user can describe their taste in a handful of simple categories — it
  does not learn taste from listening behavior.
- It's built for classroom exploration and demonstration of how content-based scoring
  and ranking work, **not** for real users or production use. The catalog is only 18
  songs and the scoring weights were chosen by hand, not learned from data.

---

## 3. How the Model Works

Every song has a genre, a mood, a 0.0–1.0 energy level, and a 0.0–1.0 acousticness
level. Every user has a favorite genre, a favorite mood, a target energy level, and a
yes/no on whether they like acoustic songs.

To score a song, the model adds up points:

- 2 points if the song's genre matches the user's favorite genre.
- 1 point if the song's mood matches the user's favorite mood.
- Up to 2 points based on how close the song's energy is to the user's target energy —
  a perfect match earns the full 2 points, and the points shrink the further apart they
  are.
- 1 point if the user likes acoustic songs and this song is acoustic, or half a point
  if the user dislikes acoustic songs and this song isn't acoustic.

Once every song has a score, the model sorts the whole catalog from highest to lowest
score and returns the top 5. Each recommendation comes with the list of reasons that
built up its score, so a user can see exactly why a song was picked.

The starter code had no logic at all (just `TODO`s and a placeholder that returned the
first songs in file order). Everything above — the point weights, the energy-closeness
formula, and the reason list — was designed and implemented from scratch.

---

## 4. Data

- 18 songs total (10 in the original starter file, 8 added to broaden genre/mood
  coverage: EDM, classical, hip-hop, R&B, folk, metal, reggae, and country).
- Genres represented: pop, lofi, rock, ambient, jazz, synthwave, indie pop, edm,
  classical, hip-hop, r&b, folk, metal, reggae, country.
- Moods represented: happy, chill, intense, relaxed, moody, focused, energetic,
  peaceful, confident, melancholy, aggressive, uplifting.
- Every song has genre, mood, energy, tempo_bpm, valence, danceability, and
  acousticness — no lyrics, artist popularity, or release date are included.
- Even with 18 songs, several genres (pop, lofi) still have more entries than others
  (metal, country, reggae each have just one), so the catalog is not evenly balanced.

---

## 5. Strengths

- Clear-cut profiles (a specific genre + mood + energy, e.g. "High-Energy Pop" or
  "Deep Intense Rock") produce results that match musical intuition — the top song is
  always the one that's genuinely closest on every axis.
- The energy-closeness formula correctly distinguishes "high energy" preferences from
  "low energy" ones — a user who wants energy 0.35 gets mellow lofi/ambient songs, not
  the most intense songs in the catalog.
- Because every score comes with a reason list, it's easy to audit *why* a song was
  recommended, which is a strength real black-box recommenders usually lack.

---

## 6. Limitations and Bias

The system over-prioritizes genre because it's worth double the points of a mood match,
and the catalog isn't evenly split across genres — pop and lofi songs are more likely to
climb into any Top-5 list simply because there are more of them to score well on energy
even when genre doesn't match. In the weight-shift experiment (see `README.md`),
halving the genre weight and doubling the energy weight was enough to pull in a
synthwave song and a hip-hop song that shared no genre or mood with the user profile,
showing the ranking is highly sensitive to weight choices rather than any deep
understanding of "taste." The scoring also ignores tempo and valence entirely, so two
songs with identical genre/mood/energy but very different feel (e.g., a slow sad pop
song vs. a fast happy one) score identically. Finally, because this is purely
content-based, it can never suggest something outside a user's stated preferences —
there's no mechanism like "other users with your energy/mood taste also liked this
different genre," so a user's profile becomes a hard filter bubble rather than a
starting point for discovery.

---

## 7. Evaluation

I tested five profiles: a default "Pop/Happy" profile, "High-Energy Pop," "Chill Lofi"
(with `likes_acoustic=True`), "Deep Intense Rock," and an adversarial profile with
conflicting preferences (`genre=classical, mood=sad, energy=0.9`) designed to see how
the system behaves when nothing in the catalog matches well.

What surprised me: the adversarial profile didn't break — it just fell back almost
entirely on energy similarity once genre/mood matches ran out, correctly surfacing the
one classical song for its genre match, then several unrelated high-energy songs for
their energy alone. That's *technically* correct given the scoring rule, but it shows
the system has no way to say "I'm not confident about this" — it will always return 5
recommendations even when none of them are a good match.

Comparing "Chill Lofi" vs. "Deep Intense Rock": the lofi profile pulls in quiet,
acoustic, mellow songs (Library Rain, Midnight Coding, Focus Flow), while the rock
profile pulls in loud, high-tempo, low-acousticness songs (Storm Runner, Gym Hero,
Riot Engine) — makes sense, since energy and acousticness pull in opposite directions
for these two profiles. Comparing "Default (Pop/Happy)" vs. "High-Energy Pop": raising
the target energy from 0.8 to 0.95 reordered the top two (Gym Hero, which is closer to
0.95, edges ahead of songs closer to 0.8) without changing which songs qualify at all —
a small numeric nudge on target_energy has a real but bounded effect, since genre/mood
matches still dominate.

---

## 8. Future Work

- Add `tempo_bpm` and `valence` as scored features so two songs with the same
  genre/mood/energy can still be told apart by feel.
- Add a diversity constraint to the ranking step (e.g., no more than 2 songs from the
  same artist or genre in the Top-5) to reduce filter-bubble risk.
- Blend in a lightweight collaborative signal (e.g., "users with a similar profile also
  picked...") so the system isn't a hard filter on the user's stated preferences alone.

---

## 9. Personal Reflection

The biggest learning moment was realizing that "recommending" is really just "score
everything, then sort" — almost all of the actual design work is in choosing what to
score and how much to weight it, not in the sorting step itself. AI tools were most
useful for quickly drafting the CSV expansion and for sanity-checking the energy
similarity formula, but I had to double-check that the generated songs used valid
attribute ranges and that the "closer is better" formula for energy actually behaved
correctly at the boundaries (energy gap of 0 → full points, gap of 1 → zero points).
What surprised me most is how convincing a handful of `if` statements and a sort can
feel — the "Because: genre match (+2.0), mood match (+1.0)..." explanations make the
system feel intentional and smart even though it's just weighted arithmetic. If I
extended this project, I'd want to add the tempo/valence features and try building a
small collaborative-filtering layer on top to see how differently it behaves from pure
content-based scoring.
