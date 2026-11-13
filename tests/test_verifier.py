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


def test_verifier_ignores_partial_word_matches():
    # "Late Statics" is not the title "Late Static" as a whole phrase.
    passed, _ = verify("The Late Statics tour was fun.", ["Sunrise City"], CATALOG)
    assert passed is True
