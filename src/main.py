"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

import sys

from tabulate import tabulate

from src.recommender import load_songs, recommend_songs

HEADERS = ["#", "Title", "Artist", "Score", "Why"]
# Wrap Title, Artist and Why so a grid table stays under 100 characters wide.
MAX_COL_WIDTHS = [None, 18, 16, None, 42]

PROFILES = [
    ("High-Energy Pop",
     {"genre": "pop", "mood": "happy", "energy": 0.9, "likes_acoustic": False}),
    ("Chill Lofi",
     {"genre": "lofi", "mood": "chill", "energy": 0.35, "likes_acoustic": True}),
    ("Deep Intense Rock",
     {"genre": "rock", "mood": "intense", "energy": 0.92, "likes_acoustic": False}),
    ("Conflicting (sad but high energy)",
     {"genre": "classical", "mood": "sad", "energy": 0.95, "likes_acoustic": True}),
    ("Unknown genre",
     {"genre": "k-pop", "mood": "euphoric", "energy": 0.5}),
    ("Focus Study (tags + instrumental, no explicit)",
     {"genre": "lofi", "mood": "chill", "energy": 0.35, "likes_acoustic": True,
      "tags": ["focus", "rainy"], "wants_instrumental": True,
      "avoid_explicit": True}),
]

# Profiles re-run with the diversity re-rank on; prefs are reused from PROFILES.
DIVERSITY_DEMOS = [
    ("Chill Lofi (diversity ON)", dict(PROFILES)["Chill Lofi"]),
]


def print_profile(name: str, prefs: dict, songs: list, k: int = 5,
                  diversity: bool = False) -> None:
    """Print the top k recommendations for one profile as a grid table."""
    print(f"=== {name} === {prefs}")
    results = recommend_songs(prefs, songs, k, diversity=diversity)
    rows = [
        [rank, song["title"], song["artist"], score, explanation]
        for rank, (song, score, explanation) in enumerate(results, 1)
    ]
    print(tabulate(rows, headers=HEADERS, tablefmt="grid", floatfmt=".2f",
                   maxcolwidths=MAX_COL_WIDTHS))


def main() -> None:
    """Load the catalog and print recommendations for every profile and diversity demo."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")
    for name, prefs in PROFILES:
        print()
        print_profile(name, prefs, songs)
    for name, prefs in DIVERSITY_DEMOS:
        print()
        print_profile(name, prefs, songs, diversity=True)


if __name__ == "__main__":
    main()
