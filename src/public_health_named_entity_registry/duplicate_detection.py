"""Read-only duplicate candidate detection."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from urllib.parse import urlparse

from .models import Record, RegistryData


@dataclass(frozen=True)
class DuplicateCandidate:
    entity_a: str
    entity_b: str
    score: float
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "entity_a": self.entity_a,
            "entity_b": self.entity_b,
            "score": round(self.score, 3),
            "reasons": list(self.reasons),
        }


def normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).casefold()
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def names_for(record: Record) -> set[str]:
    values = {str(record.data.get("preferred_name", ""))}
    values.update(
        str(name.get("value", ""))
        for name in record.data.get("names", [])
        if isinstance(name, dict)
    )
    return {normalize_name(value) for value in values if normalize_name(value)}


def domains_for(record: Record) -> set[str]:
    domains: set[str] = set()
    for url in record.data.get("official_urls", []):
        if not isinstance(url, str):
            continue
        host = (urlparse(url).hostname or "").casefold()
        if host.startswith("www."):
            host = host[4:]
        if host:
            domains.add(host)
    return domains


def find_duplicates(registry: RegistryData, threshold: float = 0.86) -> list[DuplicateCandidate]:
    entities = sorted(registry.records_of_type("entity"), key=lambda item: item.identifier)
    candidates: list[DuplicateCandidate] = []
    for index, left in enumerate(entities):
        left_names = names_for(left)
        for right in entities[index + 1 :]:
            right_names = names_for(right)
            reasons: list[str] = []
            overlap = left_names & right_names
            score = 0.0
            if overlap:
                score = 1.0
                reasons.append(f"normalized name overlap: {sorted(overlap)[0]}")
            elif left_names and right_names:
                score = max(
                    SequenceMatcher(None, a, b).ratio() for a in left_names for b in right_names
                )
                if score >= threshold:
                    reasons.append("similar preferred or alternate names")
            domain_overlap = domains_for(left) & domains_for(right)
            if domain_overlap:
                score = max(score, 0.98)
                reasons.append(f"official domain overlap: {sorted(domain_overlap)[0]}")
            if score >= threshold:
                candidates.append(
                    DuplicateCandidate(left.identifier, right.identifier, score, tuple(reasons))
                )
    return sorted(candidates, key=lambda item: (-item.score, item.entity_a, item.entity_b))
