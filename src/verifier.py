"""Check an LLM explanation for catalog songs that were not in the recommended list."""
import re


def _title_pattern(title: str) -> re.Pattern[str]:
    """Return a case-insensitive pattern that matches a title as whole words only."""
    return re.compile(rf"(?<!\w){re.escape(title)}(?!\w)", re.IGNORECASE)


def verify(text: str, allowed_titles: list[str],
           catalog_titles: list[str]) -> tuple[bool, list[str]]:
    """Return (passed, problems): fails if text names a catalog title that is not in allowed_titles."""
    allowed = {title.strip().lower() for title in allowed_titles}
    problems: list[str] = []
    seen: set[str] = set()
    for title in catalog_titles:
        key = title.strip().lower()
        if not key or key in allowed or key in seen:
            continue
        seen.add(key)
        if _title_pattern(title.strip()).search(text):
            problems.append(f"names '{title}', which is not in the recommended list")
    return (not problems, problems)
