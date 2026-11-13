import logging

from src.recommender import load_songs
from src.retriever import DEFAULT_NOTES_PATH, DEFAULT_SONGS_PATH, load_notes, retrieve


def test_all_20_catalog_songs_have_a_note():
    songs = load_songs(str(DEFAULT_SONGS_PATH))
    notes = load_notes(DEFAULT_NOTES_PATH)
    assert len(songs) == 20
    assert [s["id"] for s in songs if s["id"] not in notes] == []
    assert all(notes[s["id"]].strip() for s in songs)


def test_load_notes_parses_each_section(tmp_path):
    path = tmp_path / "notes.md"
    path.write_text(
        "# Song notes\n\n"
        "## 7 | Demo — Band\nLine one.\nLine two.\n\n"
        "## 8 | Other — Band\nOnly line.\n",
        encoding="utf-8",
    )
    assert load_notes(path) == {7: "Line one. Line two.", 8: "Only line."}


def test_retrieve_returns_notes_in_rank_order():
    notes = {3: "Note three.", 1: "Note one.", 2: "Note two."}
    results = retrieve([3, 1, 2], notes=notes)
    assert [r["id"] for r in results] == [3, 1, 2]
    assert [r["title"] for r in results] == ["Storm Runner", "Sunrise City", "Midnight Coding"]
    assert [r["note"] for r in results] == ["Note three.", "Note one.", "Note two."]


def test_retrieve_with_real_notes_keeps_input_order():
    results = retrieve([5, 1, 20])
    assert [r["id"] for r in results] == [5, 1, 20]
    assert all(r["note"] for r in results)


def test_missing_note_falls_back_to_csv_fields_and_logs(caplog):
    with caplog.at_level(logging.WARNING, logger="src.retriever"):
        results = retrieve([1, 999], notes={})

    sunrise = results[0]
    assert sunrise["title"] == "Sunrise City"
    assert "pop track by Neon Echo" in sunrise["note"]
    assert "energy 0.82" in sunrise["note"]
    assert "tempo of 118 BPM" in sunrise["note"]
    assert "2010s" in sunrise["note"]
    assert "not flagged explicit" in sunrise["note"]

    unknown = results[1]
    assert unknown["title"] == "Unknown song"
    assert "999" in unknown["note"]

    messages = [r.getMessage() for r in caplog.records]
    assert any("song id 1" in m for m in messages)
    assert any("song id 999" in m for m in messages)
