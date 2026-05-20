"""stop_id resolution with disambiguation. Never silently picks first match."""
from __future__ import annotations


class AmbiguousStation(Exception):
    """Raised when a station name matches multiple stops."""

    def __init__(self, query: str, matches: list[dict]):
        super().__init__(
            f"{query!r} matches {len(matches)} stops: "
            + ", ".join(m["stop_id"] for m in matches)
        )
        self.query = query
        self.matches = matches


def resolve_station(stops: list[dict], name_or_id: str) -> dict:
    """Exact stop_id match wins; else case-insensitive substring on stop_name.
    Multiple matches raise AmbiguousStation. No matches raises KeyError."""
    q = name_or_id.strip()
    for s in stops:
        if s["stop_id"] == q:
            return s
    q_lower = q.lower()
    matches = [s for s in stops if q_lower in s["stop_name"].lower()]
    if not matches:
        raise KeyError(f"No station matching {name_or_id!r}")
    if len(matches) > 1:
        raise AmbiguousStation(q, matches)
    return matches[0]
