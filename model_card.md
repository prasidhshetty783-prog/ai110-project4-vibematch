# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**VibeFinder 1.0**

---

## 2. Intended Use

VibeFinder suggests songs from a small catalog based on one listener's stated taste: a favorite genre, a favorite mood, a target energy level, and whether they like acoustic sounds. It returns a ranked top list and explains every point it gave.

Three optional extras sit on top of that: four switchable ranking modes (`balanced`, `genre_first`, `mood_first`, `energy_focused`), a diversity re-rank that stops one artist or genre from filling a list, and five optional preferences (decade, mood tags, instrumental, avoid explicit, popularity). All three are off by default.

It assumes the listener can describe their taste up front and that this taste stays the same across the whole session. It is built for classroom exploration of how recommenders work, not for real listeners. The catalog is 20 invented songs, so it should not be used to judge real music or real people.

---

## 3. How the Model Works

Think of it as a judge who looks at one song at a time and hands out points:

- **Genre:** a full match earns 2 points. If one genre name is part of the other (like "pop" and "indie pop"), it earns 1 point.
- **Mood:** the same mood earns 1 point.
- **Energy:** the closer a song's energy is to the listener's target, the more points it earns, up to 1.5. Being too high or too low costs the same, so it is "closest wins", not "louder wins".
- **Acoustic fit:** up to 0.5 points. A listener who likes acoustic songs earns more for acoustic ones, and a listener who does not earns more for non-acoustic ones.

Every song gets scored, the list is sorted from highest to lowest, ties go to the title in alphabetical order, and the top few are shown with the reason behind each point. If the listener leaves a preference out, that factor simply adds nothing.

**Ranking modes.** Each mode is a set of weights for the four core factors. `balanced` is the recipe above. `genre_first` makes an exact genre match worth 3.0, `mood_first` weights mood 1.5 and energy 2.0, and `energy_focused` weights energy 3.0 and genre 1.0. A related genre always earns half of the genre weight. The scoring code reads the weights and never checks a mode name.

**Diversity re-rank.** The top list is built one pick at a time. A candidate loses 1.0 for each already-picked song by the same artist and 0.5 for each already-picked song in the same genre, and the penalty is printed as a reason.

**Optional preferences.** A listener can also ask for a decade (+0.5), mood tags (+0.5 each, at most +1.0), instrumental songs (up to +0.5), no explicit songs (−1.0 for explicit ones), and mainstream or underground songs (up to +0.5). The points are fixed and do not change with the ranking mode.

Changes from the starter: the starter had empty functions, so loading the CSV, scoring, ranking and the class-based version are all new. The class version reuses the same scoring function, so there is only one place where scores are decided. I also round each factor's points to two decimals before adding them. Without that, one song's printed score (2.42) did not match the points listed under it (1.0 + 1.43).

The extras were added behind switches whose defaults reproduce the core results exactly. I checked that by comparing the full ranked lists (titles, scores and reasons) against the previous commit for the five core profiles, in all four modes, with diversity on and off: 40 combinations, 0 differences.

---

## 4. Data

The catalog has 20 songs: the 10 that came with the starter plus 10 added to cover new genres, moods, and cases where energy and acousticness disagree. All titles and artists are fictional.

- **Genres:** 17 different genres. Lofi has 3 songs, pop has 2, and the other 15 genres have exactly 1 song each.
- **Moods:** 15 different moods. Happy and chill have 3 songs each, intense has 2, and the rest have 1.
- **Features per song:** genre, mood, energy, acousticness, tempo, valence and danceability, plus five columns added later: popularity (0–100), release decade, mood tags, instrumentalness and an explicit flag. Genre, mood, energy and acousticness are always scored. The five added columns are scored only when the listener sets the matching optional preference. Tempo, valence and danceability are loaded but never scored.
- **Invented values:** the five added columns were written to look plausible for each fictional song, and I approved them in a review table before they went into the CSV. Four songs are explicit, the catalog spans eight decades (1950 to 2020), and 25 different tags are used. They are not measured data.
- **Missing:** lyrics, language, any real popularity or release data, and anything about how people actually listen. There is no way to say "I like songs like this one".

---

## 5. Strengths

- **Clear, ordinary tastes work well.** The Chill Lofi profile returned three lofi songs first and an ambient "chill" song next. The Deep Intense Rock profile put the only rock song first by a wide margin (4.93 against 2.95).
- **It explains itself.** Every score is the exact sum of the reasons printed under it, so a reader can check any result by hand.
- **Closest-wins energy behaves sensibly.** A 0.82-energy song and a 0.78-energy song score almost the same for a 0.80 target, which is what a listener would expect.
- **Predictable.** The same input always gives the same output, including ties.

---

## 6. Limitations and Bias

- **Genre and mood outweigh everything else.** Together they are worth up to 3.0 points, while energy adds at most 1.5. For a "sad but high energy" listener, a slow classical piece (energy 0.18 against a target of 0.95) still ranked first. Doubling the energy weight did not change that.
- **Thin genres get a free pass.** 15 of the 17 genres have a single song, which earns the full genre bonus whether or not it fits the rest of the profile.
- **The related-genre rule is crude and inconsistent.** It only checks whether one name contains the other. A made-up genre "k-pop" gave pop songs +1.0, but indie pop got nothing, even though it is just as close to pop. Listeners whose genre name happens to share letters with a catalog genre are treated better than listeners whose does not.
- **Mood matching is literal.** "melancholy" does not match "sad", and "euphoric" does not match "happy".
- **A few songs repeat.** Gym Hero appears in four of the five test profiles. It is high-energy and barely acoustic, so it earns energy and acoustic points from almost any upbeat listener.
- **Energy and acousticness are linked in this data** (correlation about -0.66), so a high-energy listener who dislikes acoustic songs is rewarded twice for the same trait.
- **No learning.** The system uses only what the listener types in. It cannot pick up on skips, replays or the taste of similar listeners.
- **Diversity only works inside one list.** The re-rank lowers Gym Hero's appearances from four of six profiles to three of six, but it cannot stop one song from being the answer for several different listeners.
- **The attribute data is invented,** so anything built on it (tags, decade, instrumental, popularity, explicit) shows how the rules behave, not what real listeners want. Tags are matched as exact words, so "calm" does not match "chill".
- **Optional preferences rarely reorder a profile that already fits.** The Focus Study profile kept the exact top 5 order of plain Chill Lofi. Each song in it gained between 0.83 and 1.46 points.
- **A −1.0 explicit penalty is a nudge, not a filter.** For the pop profile it moved Gym Hero from #2 to #3, and the song stayed in the top 5.

---

## 7. Evaluation

**Profiles tested:** High-Energy Pop, Chill Lofi, Deep Intense Rock, and two stress cases: Conflicting (classical, sad, energy 0.95) and Unknown genre ("k-pop", euphoric, energy 0.5). A sixth profile, Focus Study, is Chill Lofi with the tags `focus` and `rainy`, instrumental songs wanted and explicit songs penalized. I also re-ran Chill Lofi with diversity on, and ran High-Energy Pop, Chill Lofi and Conflicting in all four ranking modes.

**What I looked for:** whether the top results matched intuition, whether each score equaled the sum of its reasons, and whether odd inputs (a missing preference, an unknown genre, an empty profile) could crash or distort the ranking, and whether each extra feature, when switched off, left every old result unchanged.

**What surprised me:**
- The made-up genre "k-pop" still earned genre points through the name-contains-name rule.
- A rounding bug: Barn Dance Revival's score printed as 2.42 while its reasons added up to 2.43. Checking the numbers by hand caught it, and rounding each factor before adding fixed it.
- Cutting the genre weight from 2.0 to 0.5 pushed Gym Hero from #2 to #4 for the pop profile, while doubling the energy weight changed almost nothing.
- In the ranking modes, the #1 song never changed for the pop, lofi and conflicting profiles. Only #2 and #3 moved. For the pop profile, `mood_first` and `energy_focused` put Rooftop Lights above Gym Hero, and `genre_first` kept Gym Hero second.
- With diversity on, Focus Flow fell from 3.81 to 1.81 (−1.0 repeat artist, −1.0 repeat genre) and left the Chill Lofi top 5.
- The Focus Study profile did not change the top 5 order at all. Tags changed the order only for a different profile: adding `party` and `workout` tags to High-Energy Pop put Gym Hero (4.93) ahead of Sunrise City (4.79).

**Tests:** 53 automated tests cover the scoring rules (exact, related and missing genre, normalization, score equals sum of reasons), the ranking (order, ties, `k` limits, input not changed), the class-based version matching the function version, loading the CSV with the right types (including an older CSV without the five new columns), the four ranking modes, the diversity penalties (exactly 1.0 for a repeat artist, 0.5 for a repeat genre, no penalty for a related genre), every optional preference with exact points, and a golden-rule test showing the optional features change nothing when they are off. Separately, I checked on 32,800 scored rows that every score equals the sum of the reasons printed under it, using every mix of one to three optional preferences, in all modes, with diversity on and off.

---

## 8. Future Work

- Score tempo, valence and danceability, which are already loaded.
- Replace the name-contains-name rule with a real similarity table, so indie pop and pop count as close in both directions and unknown genres get nothing by accident.
- Treat close moods (sad and melancholy) as partial matches.
- Fix Gym Hero appearing for most upbeat profiles. The diversity re-rank is built but only works inside one list, so this needs more song features, such as tempo and valence, so similar songs can be told apart.
- Replace the invented popularity, decade, tag, instrumentalness and explicit values with real data, and match tags by meaning instead of exact words.
- Add more songs per genre so a single song no longer wins by default.

---

## 9. Personal Reflection

**What I learned.** A recommender like this is a scoring rule followed by a sort, and the weights decide almost everything. I also learned to check the output by hand. Barn Dance Revival printed a score of 2.42 while its reasons added up to 2.43, so the explanation and the score disagreed. Rounding each factor before adding fixed it, and I only found it because I added the reasons up myself.

**What surprised me.** Three things. First, the made-up genre "k-pop" still earned both pop songs +1.0, only because "pop" is part of the name. Second, how much of the work was checking the AI. The agent said Coffee Shop Stories made a top 5 because of a single tag, but it was already #5 without any tags. That kind of confident, wrong detail only showed up when I compared against a real run. Third, the ranking modes moved #2 and #3 but never the #1 song in 12 runs.

**How it changed my view of music apps.** When an app keeps recommending the same few songs, that may say more about its weights and its data than about my taste. In my project, Gym Hero showed up for most upbeat profiles because of how the points add up. I can check my recommender line by line, but I cannot do that with a real app, because its reasoning is hidden inside a learned model. And a precise-looking score is not proof that the data behind it is true: my popularity, decade, tag, instrumental and explicit values are invented, and the output looks just as confident.
