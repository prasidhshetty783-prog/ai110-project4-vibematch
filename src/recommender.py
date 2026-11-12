import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import MISSING, asdict, dataclass, field, fields

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
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
    popularity: int = 50
    release_decade: int = 0
    mood_tags: List[str] = field(default_factory=list)
    instrumentalness: float = 0.0
    explicit: bool = False

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: Optional[float]
    likes_acoustic: Optional[bool]
    decade: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    wants_instrumental: bool = False
    avoid_explicit: bool = False
    popularity: Optional[str] = None


@dataclass(frozen=True)
class ScoringMode:
    """A named set of weights, one per core factor (Strategy pattern)."""
    name: str
    genre: float
    mood: float
    energy: float
    acoustic: float

    @property
    def related_genre(self) -> float:
        """A related genre always earns half the genre weight."""
        return self.genre / 2


MODES: Dict[str, ScoringMode] = {
    mode.name: mode
    for mode in (
        ScoringMode("balanced", genre=2.0, mood=1.0, energy=1.5, acoustic=0.5),
        ScoringMode("genre_first", genre=3.0, mood=1.0, energy=1.0, acoustic=0.5),
        ScoringMode("mood_first", genre=1.5, mood=1.5, energy=2.0, acoustic=0.5),
        ScoringMode("energy_focused", genre=1.0, mood=1.0, energy=3.0, acoustic=0.5),
    )
}


def _profile_to_prefs(user: UserProfile) -> Dict:
    """Convert a UserProfile into the prefs dict that score_song expects."""
    prefs = {
        "genre": user.favorite_genre,
        "mood": user.favorite_mood,
        "energy": user.target_energy,
        "likes_acoustic": user.likes_acoustic,
    }
    if user.decade is not None:
        prefs["decade"] = user.decade
    if user.tags:
        prefs["tags"] = list(user.tags)
    if user.wants_instrumental:
        prefs["wants_instrumental"] = True
    if user.avoid_explicit:
        prefs["avoid_explicit"] = True
    if user.popularity is not None:
        prefs["popularity"] = user.popularity
    return prefs


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        """Store the catalog of Song objects."""
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5,
                  mode: ScoringMode = MODES["balanced"],
                  diversity: bool = False) -> List[Song]:
        """Return the top k Song objects, ranked by recommend_songs."""
        by_id = {song.id: song for song in self.songs}
        dicts = [asdict(song) for song in self.songs]
        results = recommend_songs(_profile_to_prefs(user), dicts, k,
                                  mode=mode, diversity=diversity)
        return [by_id[song_dict["id"]] for song_dict, _, _ in results]

    def explain_recommendation(self, user: UserProfile, song: Song,
                               mode: ScoringMode = MODES["balanced"]) -> str:
        """Explain a song's score for this user; never returns an empty string."""
        _, reasons = score_song(_profile_to_prefs(user), asdict(song), mode=mode)
        return "; ".join(reasons) if reasons else "No matching factors"

FLOAT_FIELDS = ("energy", "tempo_bpm", "valence", "danceability", "acousticness")
_SONG_DEFAULTS = {f.name: f.default for f in fields(Song) if f.default is not MISSING}


def _cell(row: Dict, name: str) -> str:
    """Return a stripped CSV cell, or "" when the column is missing or blank."""
    value = row.get(name)
    return "" if value is None else value.strip()


def _split_tags(text: str) -> List[str]:
    """Split a ;-separated tag string into a stripped lowercase list ("" -> [])."""
    return [tag.strip().lower() for tag in text.split(";") if tag.strip()]


def load_songs(csv_path: str) -> List[Dict]:
    """Load songs from a CSV file into a list of dicts with numeric fields converted."""
    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["id"] = int(row["id"])
            for name in FLOAT_FIELDS:
                row[name] = float(row[name])
            popularity = _cell(row, "popularity")
            decade = _cell(row, "release_decade")
            instrumentalness = _cell(row, "instrumentalness")
            explicit = _cell(row, "explicit")
            row["popularity"] = int(popularity) if popularity else _SONG_DEFAULTS["popularity"]
            row["release_decade"] = int(decade) if decade else _SONG_DEFAULTS["release_decade"]
            row["mood_tags"] = _split_tags(_cell(row, "mood_tags"))
            row["instrumentalness"] = (float(instrumentalness) if instrumentalness
                                       else _SONG_DEFAULTS["instrumentalness"])
            row["explicit"] = explicit == "1" if explicit else _SONG_DEFAULTS["explicit"]
            songs.append(row)
    return songs

def _norm(value: Optional[str]) -> str:
    """Lowercase and strip a string for comparison; None becomes ""."""
    return "" if value is None else str(value).strip().lower()


def _fmt_points(points: float) -> str:
    """Format fixed points with 2 decimals, dropping one trailing zero (2.0, 1.5, 0.75)."""
    text = f"{points:.2f}"
    return text[:-1] if text.endswith("0") else text


def score_song(user_prefs: Dict, song: Dict,
               mode: ScoringMode = MODES["balanced"]) -> Tuple[float, List[str]]:
    """Score one song against user prefs and return (score, reasons)."""
    score = 0.0
    reasons: List[str] = []

    genre = _norm(user_prefs.get("genre"))
    song_genre = _norm(song.get("genre"))
    if genre and song_genre:
        if genre == song_genre:
            points = round(mode.genre, 2)
            score += points
            reasons.append(f"genre match (+{_fmt_points(points)})")
        elif genre in song_genre or song_genre in genre:
            points = round(mode.related_genre, 2)
            score += points
            reasons.append(f"related genre: {song_genre} (+{_fmt_points(points)})")

    mood = _norm(user_prefs.get("mood"))
    if mood and mood == _norm(song.get("mood")):
        points = round(mode.mood, 2)
        score += points
        reasons.append(f"mood match (+{_fmt_points(points)})")

    target = user_prefs.get("energy")
    if target is not None:
        points = round(mode.energy * (1 - abs(song["energy"] - target)), 2)
        score += points
        reasons.append(f"energy {song['energy']:.2f} vs target {target:.2f} (+{points:.2f})")

    likes_acoustic = user_prefs.get("likes_acoustic")
    if likes_acoustic is not None:
        fit = song["acousticness"] if likes_acoustic else 1 - song["acousticness"]
        points = round(mode.acoustic * fit, 2)
        score += points
        reasons.append(f"acoustic fit (+{points:.2f})")

    extra_score, extra_reasons = _score_new_attributes(user_prefs, song)
    return score + extra_score, reasons + extra_reasons


DECADE_POINTS = 0.5
TAG_POINTS = 0.5
TAG_CAP = 1.0
INSTRUMENTAL_WEIGHT = 0.5
EXPLICIT_PENALTY = 1.0
POPULARITY_WEIGHT = 0.5


def _score_new_attributes(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score the opt-in stretch prefs (fixed points, not scaled by ScoringMode)."""
    score = 0.0
    reasons: List[str] = []

    decade = user_prefs.get("decade")
    if decade is not None and decade == song.get("release_decade"):
        points = round(DECADE_POINTS, 2)
        score += points
        reasons.append(f"decade match (+{_fmt_points(points)})")

    wanted = list(dict.fromkeys(_norm(tag) for tag in user_prefs.get("tags") or []))
    song_tags = {_norm(tag) for tag in song.get("mood_tags") or []}
    matched = [tag for tag in wanted if tag and tag in song_tags]
    if matched:
        points = round(min(TAG_POINTS * len(matched), TAG_CAP), 2)
        score += points
        reasons.append(f"tag match: {', '.join(matched)} (+{_fmt_points(points)})")

    if user_prefs.get("wants_instrumental") is True:
        instrumentalness = song.get("instrumentalness", _SONG_DEFAULTS["instrumentalness"])
        points = round(INSTRUMENTAL_WEIGHT * instrumentalness, 2)
        score += points
        reasons.append(f"instrumental fit (+{points:.2f})")

    if user_prefs.get("avoid_explicit") is True and song.get("explicit"):
        points = round(EXPLICIT_PENALTY, 2)
        score -= points
        reasons.append(f"explicit content (−{_fmt_points(points)})")

    popularity = _norm(user_prefs.get("popularity"))
    if popularity in ("mainstream", "underground"):
        share = song.get("popularity", _SONG_DEFAULTS["popularity"]) / 100
        fit = share if popularity == "mainstream" else 1 - share
        points = round(POPULARITY_WEIGHT * fit, 2)
        score += points
        reasons.append(f"popularity: {popularity} (+{points:.2f})")

    return score, reasons

REPEAT_ARTIST_PENALTY = 1.0
REPEAT_GENRE_PENALTY = 0.5


def _diversity_penalty(song: Dict, picked: List[Dict]) -> Tuple[float, List[str]]:
    """Return the total penalty and its reasons for a song versus already-picked songs."""
    penalty = 0.0
    reasons: List[str] = []
    for attr, per_hit in (("artist", REPEAT_ARTIST_PENALTY), ("genre", REPEAT_GENRE_PENALTY)):
        value = _norm(song.get(attr))
        hits = sum(1 for other in picked if value and _norm(other.get(attr)) == value)
        if hits:
            points = round(per_hit * hits, 2)
            penalty += points
            reasons.append(f"diversity: repeat {attr} (−{_fmt_points(points)})")
    return penalty, reasons


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5,
                    mode: ScoringMode = MODES["balanced"],
                    diversity: bool = False) -> List[Tuple[Dict, float, str]]:
    """Score every song and return the top k as (song, score, explanation)."""
    if k <= 0:
        return []
    if diversity:
        return _diverse_top_k(user_prefs, songs, k, mode)
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song, mode=mode)
        scored.append((song, score, "; ".join(reasons)))
    ranked = sorted(scored, key=lambda item: (-round(item[1], 6), item[0]["title"]))
    return ranked[:k]


def _diverse_top_k(user_prefs: Dict, songs: List[Dict], k: int,
                   mode: ScoringMode) -> List[Tuple[Dict, float, str]]:
    """Greedily pick k songs, penalizing repeat artists and genres among earlier picks."""
    remaining = [(song, *score_song(user_prefs, song, mode=mode)) for song in songs]
    picked: List[Dict] = []
    results: List[Tuple[Dict, float, str]] = []
    while remaining and len(results) < k:
        candidates = []
        for index, (song, score, reasons) in enumerate(remaining):
            penalty, extra = _diversity_penalty(song, picked)
            candidates.append((score - penalty, song["title"], index, reasons + extra))
        adjusted, _, index, reasons = min(
            candidates, key=lambda c: (-round(c[0], 6), c[1])
        )
        song = remaining.pop(index)[0]
        picked.append(song)
        results.append((song, adjusted, "; ".join(reasons)))
    return results
