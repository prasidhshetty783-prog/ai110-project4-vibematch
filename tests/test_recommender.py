import re
from dataclasses import asdict

import pytest

from src.main import PROFILES
from src.recommender import (
    MODES,
    Song,
    UserProfile,
    Recommender,
    load_songs,
    recommend_songs,
    score_song,
)

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


def make_song(**overrides) -> dict:
    """Build a song dict with neutral defaults, overridden per test."""
    song = {
        "id": 1,
        "title": "Test Song",
        "artist": "Test Artist",
        "genre": "rock",
        "mood": "sad",
        "energy": 0.5,
        "tempo_bpm": 100.0,
        "valence": 0.5,
        "danceability": 0.5,
        "acousticness": 0.5,
    }
    song.update(overrides)
    return song


POP_PREFS = {"genre": "pop", "mood": "happy", "energy": 0.8}


def test_score_song_exact_match_scores_all_three_factors():
    song = make_song(genre="pop", mood="happy", energy=0.82, acousticness=0.18)
    score, reasons = score_song(POP_PREFS, song)
    assert score == pytest.approx(4.47)
    assert len(reasons) == 3
    assert reasons[0] == "genre match (+2.0)"


def test_score_song_related_genre_adds_one_point():
    song = make_song(genre="indie pop")
    score, reasons = score_song({"genre": "pop"}, song)
    assert score == pytest.approx(1.0)
    assert reasons == ["related genre: indie pop (+1.0)"]


def test_score_song_empty_prefs_scores_zero():
    score, reasons = score_song({}, make_song())
    assert score == pytest.approx(0.0)
    assert reasons == []


def test_score_song_normalizes_genre_and_mood():
    song = make_song(genre="pop", mood="happy")
    score, reasons = score_song({"genre": " POP ", "mood": "Happy "}, song)
    assert score == pytest.approx(3.0)
    assert reasons == ["genre match (+2.0)", "mood match (+1.0)"]


def test_score_song_score_equals_sum_of_reason_points():
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False}
    song = make_song(genre="pop", mood="happy", energy=0.85, acousticness=0.37)
    score, reasons = score_song(prefs, song)
    assert len(reasons) == 4
    points = [float(re.search(r"\(([+-][\d.]+)\)$", r).group(1)) for r in reasons]
    assert score == pytest.approx(sum(points))


def test_recommend_songs_ranks_highest_first_and_returns_k():
    songs = [
        make_song(id=1, title="Weak", genre="rock", energy=0.1),
        make_song(id=2, title="Best", genre="pop", mood="happy", energy=0.8),
        make_song(id=3, title="Middle", genre="pop", energy=0.5),
    ]
    results = recommend_songs(POP_PREFS, songs, k=2)
    assert len(results) == 2
    top_song, top_score, top_explanation = results[0]
    assert top_song["title"] == "Best"
    assert top_score == pytest.approx(4.5)
    assert top_explanation == "genre match (+2.0); mood match (+1.0); energy 0.80 vs target 0.80 (+1.50)"


def test_recommend_songs_breaks_ties_by_title():
    songs = [
        make_song(id=1, title="Charlie"),
        make_song(id=2, title="Alpha"),
        make_song(id=3, title="Bravo"),
    ]
    results = recommend_songs({}, songs, k=3)
    assert [song["title"] for song, _, _ in results] == ["Alpha", "Bravo", "Charlie"]
    assert all(score == pytest.approx(0.0) for _, score, _ in results)


def test_recommend_songs_k_bounds_and_input_unchanged():
    songs = [make_song(id=i, title=f"Song {i}", energy=i / 10) for i in range(1, 4)]
    original_order = [song["title"] for song in songs]
    assert recommend_songs(POP_PREFS, songs, k=0) == []
    assert recommend_songs(POP_PREFS, songs, k=-1) == []
    assert len(recommend_songs(POP_PREFS, songs, k=100)) == len(songs)
    assert [song["title"] for song in songs] == original_order


def test_recommender_matches_recommend_songs():
    songs = [
        Song(id=1, title="Pop Hit", artist="A", genre="pop", mood="happy", energy=0.8,
             tempo_bpm=120, valence=0.9, danceability=0.8, acousticness=0.1),
        Song(id=2, title="Indie Pop Gem", artist="B", genre="indie pop", mood="happy", energy=0.7,
             tempo_bpm=110, valence=0.8, danceability=0.7, acousticness=0.4),
        Song(id=3, title="Lofi Loop", artist="C", genre="lofi", mood="chill", energy=0.3,
             tempo_bpm=80, valence=0.5, danceability=0.5, acousticness=0.9),
        Song(id=4, title="Rock Anthem", artist="D", genre="rock", mood="happy", energy=0.9,
             tempo_bpm=140, valence=0.6, danceability=0.6, acousticness=0.05),
    ]
    user = UserProfile(favorite_genre="pop", favorite_mood="happy",
                       target_energy=0.8, likes_acoustic=False)
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False}

    oop_titles = [song.title for song in Recommender(songs).recommend(user, k=4)]
    functional = recommend_songs(prefs, [asdict(song) for song in songs], k=4)
    assert oop_titles == [song["title"] for song, _, _ in functional]


def test_load_songs_reads_catalog_with_types():
    songs = load_songs("data/songs.csv")
    assert len(songs) == 20
    assert all(isinstance(song["id"], int) for song in songs)
    assert all(isinstance(song["energy"], float) for song in songs)


POP_SONG = make_song(genre="pop", mood="happy", energy=0.82)
INDIE_POP_SONG = make_song(genre="indie pop", mood="happy", energy=0.76)


@pytest.mark.parametrize("mode_name, pop_expected, indie_expected", [
    ("balanced", 4.47, 3.44),        # 2.0 + 1.0 + 1.47  |  1.0 + 1.0 + 1.44
    ("genre_first", 4.98, 3.46),     # 3.0 + 1.0 + 0.98  |  1.5 + 1.0 + 0.96
    ("mood_first", 4.96, 4.17),      # 1.5 + 1.5 + 1.96  |  0.75 + 1.5 + 1.92
    ("energy_focused", 4.94, 4.38),  # 1.0 + 1.0 + 2.94  |  0.5 + 1.0 + 2.88
])
def test_score_song_each_mode_exact_points(mode_name, pop_expected, indie_expected):
    mode = MODES[mode_name]
    pop_score, _ = score_song(POP_PREFS, POP_SONG, mode=mode)
    indie_score, _ = score_song(POP_PREFS, INDIE_POP_SONG, mode=mode)
    assert pop_score == pytest.approx(pop_expected)
    assert indie_score == pytest.approx(indie_expected)


def test_mood_first_related_genre_reason_shows_half_weight():
    _, reasons = score_song(POP_PREFS, INDIE_POP_SONG, mode=MODES["mood_first"])
    assert reasons == [
        "related genre: indie pop (+0.75)",
        "mood match (+1.5)",
        "energy 0.76 vs target 0.80 (+1.92)",
    ]


def test_score_song_default_mode_is_balanced():
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": True}
    for song in (POP_SONG, INDIE_POP_SONG):
        assert score_song(prefs, song) == score_song(prefs, song, mode=MODES["balanced"])


def test_recommend_songs_mode_changes_order():
    songs = [
        make_song(id=1, title="Pop Slow", genre="pop", energy=0.3),
        make_song(id=2, title="Rock Match", genre="rock", energy=0.8),
    ]
    prefs = {"genre": "pop", "energy": 0.8}
    balanced = recommend_songs(prefs, songs, k=2)
    energy = recommend_songs(prefs, songs, k=2, mode=MODES["energy_focused"])
    # balanced: 2.0 + 0.75 = 2.75 vs 1.5  |  energy_focused: 1.0 + 1.5 = 2.5 vs 3.0
    assert [s["title"] for s, _, _ in balanced] == ["Pop Slow", "Rock Match"]
    assert [s["title"] for s, _, _ in energy] == ["Rock Match", "Pop Slow"]
    assert [score for _, score, _ in energy] == pytest.approx([3.0, 2.5])


def test_recommender_passes_mode_through():
    songs = [
        Song(id=1, title="Pop Slow", artist="A", genre="pop", mood="sad", energy=0.3,
             tempo_bpm=100, valence=0.5, danceability=0.5, acousticness=0.5),
        Song(id=2, title="Rock Match", artist="B", genre="rock", mood="sad", energy=0.8,
             tempo_bpm=100, valence=0.5, danceability=0.5, acousticness=0.5),
    ]
    user = UserProfile(favorite_genre="pop", favorite_mood="happy",
                       target_energy=0.8, likes_acoustic=False)
    rec = Recommender(songs)
    titles = [song.title for song in rec.recommend(user, k=2, mode=MODES["energy_focused"])]
    assert titles == ["Rock Match", "Pop Slow"]
    assert rec.explain_recommendation(user, songs[0], mode=MODES["genre_first"]).startswith(
        "genre match (+3.0)"
    )


def test_diversity_repeat_artist_penalty_is_exactly_one():
    songs = [
        make_song(id=1, title="Alpha", artist="Same", genre="rock"),
        make_song(id=2, title="Bravo", artist="Same", genre="jazz"),
    ]
    results = recommend_songs({}, songs, k=2, diversity=True)
    assert [score for _, score, _ in results] == pytest.approx([0.0, -1.0])
    assert results[1][2] == "diversity: repeat artist (\u22121.0)"


def test_diversity_repeat_genre_penalty_is_exactly_half():
    songs = [
        make_song(id=1, title="Alpha", artist="One", genre="rock"),
        make_song(id=2, title="Bravo", artist="Two", genre="Rock "),
    ]
    results = recommend_songs({}, songs, k=2, diversity=True)
    assert [score for _, score, _ in results] == pytest.approx([0.0, -0.5])
    assert results[1][2] == "diversity: repeat genre (\u22120.5)"


def test_diversity_related_genre_is_not_penalized():
    songs = [
        make_song(id=1, title="Alpha", artist="One", genre="pop"),
        make_song(id=2, title="Bravo", artist="Two", genre="indie pop"),
    ]
    results = recommend_songs({}, songs, k=2, diversity=True)
    assert results[1][1] == pytest.approx(0.0)
    assert results[1][2] == ""


def test_diversity_two_picked_same_artist_gives_minus_two():
    songs = [
        make_song(id=i, title=title, artist="Same", genre=genre)
        for i, (title, genre) in enumerate([("Alpha", "rock"), ("Bravo", "jazz"), ("Charlie", "folk")], 1)
    ]
    results = recommend_songs({}, songs, k=3, diversity=True)
    assert results[2][0]["title"] == "Charlie"
    assert results[2][1] == pytest.approx(-2.0)
    assert results[2][2] == "diversity: repeat artist (\u22122.0)"


def test_diversity_reasons_add_up_to_adjusted_score():
    songs = [
        make_song(id=1, title="Alpha", artist="Same", genre="pop", mood="happy", energy=0.8),
        make_song(id=2, title="Bravo", artist="Same", genre="pop", mood="happy", energy=0.82),
    ]
    results = recommend_songs(POP_PREFS, songs, k=2, diversity=True)
    song, score, explanation = results[1]
    assert explanation == (
        "genre match (+2.0); mood match (+1.0); energy 0.82 vs target 0.80 (+1.47); "
        "diversity: repeat artist (\u22121.0); diversity: repeat genre (\u22120.5)"
    )
    points = [float(m.replace("\u2212", "-"))
              for m in re.findall(r"\(([+\u2212][\d.]+)\)", explanation)]
    assert score == pytest.approx(sum(points)) == pytest.approx(2.97)


def test_diversity_false_equals_default():
    songs = [
        make_song(id=1, title="Pop One", artist="X", genre="pop", energy=0.8),
        make_song(id=2, title="Pop Two", artist="X", genre="pop", energy=0.7),
        make_song(id=3, title="Indie Gem", artist="Y", genre="indie pop", energy=0.9),
    ]
    assert recommend_songs(POP_PREFS, songs, k=3, diversity=False) == recommend_songs(POP_PREFS, songs, k=3)


def test_diversity_changes_order():
    songs = [
        make_song(id=1, title="Pop One", artist="X", genre="pop"),
        make_song(id=2, title="Pop Two", artist="X", genre="pop"),
        make_song(id=3, title="Indie Gem", artist="Y", genre="indie pop"),
    ]
    prefs = {"genre": "pop"}
    plain = recommend_songs(prefs, songs, k=3)
    diverse = recommend_songs(prefs, songs, k=3, diversity=True)
    assert [s["title"] for s, _, _ in plain] == ["Pop One", "Pop Two", "Indie Gem"]
    # Pop Two drops to 2.0 - 1.0 - 0.5 = 0.5, below Indie Gem's 1.0
    assert [s["title"] for s, _, _ in diverse] == ["Pop One", "Indie Gem", "Pop Two"]
    assert [score for _, score, _ in diverse] == pytest.approx([2.0, 1.0, 0.5])


def test_diversity_k_bounds_and_input_unchanged():
    songs = [make_song(id=i, title=f"Song {i}", artist="Same") for i in range(1, 4)]
    original = [dict(song) for song in songs]
    assert recommend_songs(POP_PREFS, songs, k=0, diversity=True) == []
    assert recommend_songs(POP_PREFS, songs, k=-1, diversity=True) == []
    assert len(recommend_songs(POP_PREFS, songs, k=100, diversity=True)) == len(songs)
    assert songs == original


def test_recommender_passes_diversity_through():
    def song(id_, title, artist, genre):
        return Song(id=id_, title=title, artist=artist, genre=genre, mood="sad", energy=0.5,
                    tempo_bpm=100, valence=0.5, danceability=0.5, acousticness=0.5)
    songs = [song(1, "Pop One", "X", "pop"), song(2, "Pop Two", "X", "pop"),
             song(3, "Indie Gem", "Y", "indie pop")]
    user = UserProfile(favorite_genre="pop", favorite_mood="happy",
                       target_energy=0.5, likes_acoustic=False)
    rec = Recommender(songs)
    assert [s.title for s in rec.recommend(user, k=3)] == ["Pop One", "Pop Two", "Indie Gem"]
    assert [s.title for s in rec.recommend(user, k=3, diversity=True)] == ["Pop One", "Indie Gem", "Pop Two"]


# --- New song attributes (stretch feature 4) ---

NEW_SONG_KEYS = ("popularity", "release_decade", "mood_tags", "instrumentalness", "explicit")


def reason_points(explanation: str) -> list:
    """Pull every signed point value out of an explanation (handles the real minus sign)."""
    return [float(m.replace("\u2212", "-"))
            for m in re.findall(r"\(([+\u2212][\d.]+)\)", explanation)]


def test_decade_match_adds_exactly_half():
    song = make_song(release_decade=1990)
    assert score_song({"decade": 1990}, song) == (0.5, ["decade match (+0.5)"])
    assert score_song({"decade": 1995}, song) == (0.0, [])


def test_one_tag_overlap_adds_exactly_half():
    song = make_song(mood_tags=["night", "cozy"])
    assert score_song({"tags": [" Night "]}, song) == (0.5, ["tag match: night (+0.5)"])


def test_tags_cap_at_one_point():
    song = make_song(mood_tags=["focus", "rainy", "cozy"])
    score, reasons = score_song({"tags": ["focus", "rainy", "cozy"]}, song)
    assert score == pytest.approx(1.0)
    assert reasons == ["tag match: focus, rainy, cozy (+1.0)"]


def test_duplicate_user_tags_count_once():
    song = make_song(mood_tags=["focus"])
    assert score_song({"tags": ["focus", "FOCUS"]}, song) == (0.5, ["tag match: focus (+0.5)"])


def test_wants_instrumental_adds_half_times_instrumentalness():
    song = make_song(instrumentalness=0.92)
    score, reasons = score_song({"wants_instrumental": True}, song)
    assert score == pytest.approx(0.46)
    assert reasons == ["instrumental fit (+0.46)"]


def test_avoid_explicit_subtracts_exactly_one():
    song = make_song(explicit=True)
    score, reasons = score_song({"avoid_explicit": True}, song)
    assert score == pytest.approx(-1.0)
    assert reasons == ["explicit content (\u22121.0)"]


def test_avoid_explicit_on_clean_song_has_no_penalty():
    assert score_song({"avoid_explicit": True}, make_song(explicit=False)) == (0.0, [])


@pytest.mark.parametrize("pref, expected, reason", [
    ("mainstream", 0.44, "popularity: mainstream (+0.44)"),    # 0.5 * 88/100
    ("underground", 0.06, "popularity: underground (+0.06)"),  # 0.5 * (1 - 88/100)
])
def test_popularity_points(pref, expected, reason):
    score, reasons = score_song({"popularity": pref}, make_song(popularity=88))
    assert score == pytest.approx(expected)
    assert reasons == [reason]


def test_scaled_new_factors_always_show_two_decimals():
    song = make_song(instrumentalness=0.8, popularity=20)
    prefs = {"wants_instrumental": True, "popularity": "mainstream"}
    assert score_song(prefs, song)[1] == ["instrumental fit (+0.40)", "popularity: mainstream (+0.10)"]


def test_popularity_unknown_value_is_ignored():
    assert score_song({"popularity": "medium"}, make_song(popularity=88)) == (0.0, [])


def test_new_attribute_points_ignore_scoring_mode():
    song = make_song(release_decade=2020, mood_tags=["focus"], instrumentalness=0.9,
                     explicit=True, popularity=20)
    prefs = {"decade": 2020, "tags": ["focus"], "wants_instrumental": True,
             "avoid_explicit": True, "popularity": "underground"}
    results = {name: score_song(prefs, song, mode=mode) for name, mode in MODES.items()}
    # 0.5 + 0.5 + 0.45 - 1.0 + 0.4, the same in every mode
    assert all(score == pytest.approx(0.85) for score, _ in results.values())
    assert len({tuple(reasons) for _, reasons in results.values()}) == 1


def test_score_equals_sum_of_reasons_with_all_new_prefs():
    prefs = {"genre": "lofi", "mood": "chill", "energy": 0.35, "likes_acoustic": True,
             "decade": 2020, "tags": ["focus", "rainy"], "wants_instrumental": True,
             "avoid_explicit": True, "popularity": "mainstream"}
    song = make_song(genre="lofi", mood="chill", energy=0.42, acousticness=0.71,
                     release_decade=2020, mood_tags=["rainy", "focus"],
                     instrumentalness=0.88, explicit=True, popularity=62)
    score, reasons = score_song(prefs, song)
    assert len(reasons) == 9
    assert score == pytest.approx(sum(reason_points("; ".join(reasons))))


def test_load_songs_new_columns_have_correct_types():
    songs = load_songs("data/songs.csv")
    assert len(songs) == 20
    for song in songs:
        assert type(song["popularity"]) is int and 0 <= song["popularity"] <= 100
        assert type(song["release_decade"]) is int
        assert isinstance(song["mood_tags"], list) and song["mood_tags"]
        assert all(tag == tag.strip().lower() for tag in song["mood_tags"])
        assert type(song["instrumentalness"]) is float and 0.0 <= song["instrumentalness"] <= 1.0
        assert type(song["explicit"]) is bool


def test_load_songs_without_new_columns_fills_defaults(tmp_path):
    csv_file = tmp_path / "old.csv"
    csv_file.write_text(
        "id,title,artist,genre,mood,energy,tempo_bpm,valence,danceability,acousticness\n"
        "1,Old Song,Old Artist,pop,happy,0.8,120,0.9,0.8,0.2\n",
        encoding="utf-8",
    )
    [song] = load_songs(str(csv_file))
    assert song["popularity"] == 50
    assert song["release_decade"] == 0
    assert song["mood_tags"] == []
    assert song["instrumentalness"] == 0.0
    assert song["explicit"] is False


def ranked(results):
    """Reduce recommend_songs output to comparable (title, score, explanation) tuples."""
    return [(song["title"], score, explanation) for song, score, explanation in results]


@pytest.mark.parametrize("mode_name", list(MODES))
@pytest.mark.parametrize("diversity", [False, True])
def test_golden_rule_new_columns_change_nothing_without_new_prefs(mode_name, diversity):
    songs = load_songs("data/songs.csv")
    stripped = [{k: v for k, v in song.items() if k not in NEW_SONG_KEYS} for song in songs]
    neutral = {"decade": None, "tags": [], "wants_instrumental": False,
               "avoid_explicit": False, "popularity": None}
    mode = MODES[mode_name]
    # The golden rule covers only profiles that set none of the new prefs.
    core_profiles = [prefs for _, prefs in PROFILES if not set(prefs) & set(neutral)]
    assert len(core_profiles) == 5
    for prefs in core_profiles:
        expected = ranked(recommend_songs(prefs, stripped, k=len(songs), mode=mode, diversity=diversity))
        assert ranked(recommend_songs(prefs, songs, k=len(songs), mode=mode, diversity=diversity)) == expected
        assert ranked(recommend_songs({**prefs, **neutral}, songs, k=len(songs),
                                      mode=mode, diversity=diversity)) == expected


def test_recommender_passes_new_profile_fields_through():
    def song(id_, title, **extra):
        return Song(id=id_, title=title, artist=title, genre="lofi", mood="chill", energy=0.4,
                    tempo_bpm=80, valence=0.5, danceability=0.5, acousticness=0.5, **extra)
    songs = [song(1, "Alpha Vocal", explicit=True),
             song(2, "Bravo Instrumental", instrumentalness=0.9, mood_tags=["focus"])]
    plain = UserProfile(favorite_genre="lofi", favorite_mood="chill",
                        target_energy=0.4, likes_acoustic=True)
    picky = UserProfile(favorite_genre="lofi", favorite_mood="chill",
                        target_energy=0.4, likes_acoustic=True,
                        tags=["focus"], wants_instrumental=True, avoid_explicit=True)
    rec = Recommender(songs)
    assert [s.title for s in rec.recommend(plain, k=2)] == ["Alpha Vocal", "Bravo Instrumental"]
    assert [s.title for s in rec.recommend(picky, k=2)] == ["Bravo Instrumental", "Alpha Vocal"]
    assert rec.explain_recommendation(picky, songs[1]).endswith(
        "tag match: focus (+0.5); instrumental fit (+0.45)"
    )
    assert rec.explain_recommendation(picky, songs[0]).endswith(
        "instrumental fit (+0.00); explicit content (\u22121.0)"
    )
