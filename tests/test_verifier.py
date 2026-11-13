from src.verifier import verify

CATALOG = ["Sunrise City", "Storm Runner", "Rooftop Lights", "Late Static"]


def test_verifier_passes_clean_explanation():
    text = "Sunrise City is a happy pop pick, and Rooftop Lights is a close match."
    passed, problems = verify(text, ["Sunrise City", "Rooftop Lights"], CATALOG)
    assert passed is True
    assert problems == []


def test_verifier_catches_catalog_title_outside_top_k():
    text = "Sunrise City fits, and Storm Runner would also work well."
    passed, problems = verify(text, ["Sunrise City", "Rooftop Lights"], CATALOG)
    assert passed is False
    assert len(problems) == 1
    assert "Storm Runner" in problems[0]


def test_verifier_matches_titles_case_insensitively():
    passed, problems = verify("SUNRISE CITY is great.", ["sunrise city"], CATALOG)
    assert passed is True
    assert problems == []


def test_verifier_fails_per_case_reply_when_named_song_is_outside_top_5():
    import json
    from pathlib import Path

    from src.recommender import load_songs

    replies = Path(__file__).resolve().parent / "fixtures" / "explainer_responses.json"
    with open(replies, encoding="utf-8") as f:
        normal_1_reply = json.load(f)["normal-1"]
    catalog = [s["title"] for s in load_songs(str(Path(__file__).resolve().parent.parent / "data" / "songs.csv"))]
    top5 = ["Library Rain", "Midnight Coding", "Focus Flow", "Spacewalk Thoughts", "Coffee Shop Stories"]

    assert verify(normal_1_reply, top5, catalog) == (True, [])
    # Drop Focus Flow from the allowed list: the reply still names it, so it must fail.
    passed, problems = verify(normal_1_reply, [t for t in top5 if t != "Focus Flow"], catalog)
    assert passed is False
    assert any("Focus Flow" in p for p in problems)


def test_verifier_ignores_partial_word_matches():
    # "Late Statics" is not the title "Late Static" as a whole phrase.
    passed, _ = verify("The Late Statics tour was fun.", ["Sunrise City"], CATALOG)
    assert passed is True
