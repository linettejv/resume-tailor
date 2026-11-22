"""Loads the fact bank (data/experience.yaml) and gives quick lookups."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

_DATA = Path(__file__).parent / "data"
# Your real fact bank is git-ignored; fall back to the example so a fresh clone still runs.
DEFAULT_PATH = _DATA / "experience.yaml" if (_DATA / "experience.yaml").exists() else _DATA / "experience.example.yaml"


@dataclass
class Profile:
    raw: dict
    facts: dict[str, dict] = field(default_factory=dict)      # fact id -> fact
    fact_owner: dict[str, str] = field(default_factory=dict)  # fact id -> role/project id

    @property
    def skills(self) -> list[str]:
        return list(self.raw.get("skills", []))

    @property
    def interests(self) -> list[str]:
        return list(self.raw.get("interests", []))

    @property
    def section_ids(self) -> list[str]:
        return [r["id"] for r in self.raw.get("roles", [])] + [
            p["id"] for p in self.raw.get("projects", [])
        ]


def load_profile(path: Path | str = DEFAULT_PATH) -> Profile:
    raw = yaml.safe_load(Path(path).read_text())
    profile = Profile(raw=raw)
    for section in raw.get("roles", []) + raw.get("projects", []):
        for fact in section.get("facts", []):
            if fact["id"] in profile.facts:
                raise ValueError(f"Duplicate fact id in experience.yaml: {fact['id']}")
            profile.facts[fact["id"]] = fact
            profile.fact_owner[fact["id"]] = section["id"]
    return profile
