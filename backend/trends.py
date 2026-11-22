"""Tracks every job you run through the app, and finds the skills the market keeps asking for.

Each accepted run is appended to output/history.jsonl (one JSON object per line).
summarize() turns the last N days into: how many jobs, the verdict split, average scores,
and the skills you lack that show up in the most jobs.
"""
from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

HISTORY = Path(__file__).parent / "output" / "history.jsonl"


def record_run(label: str, submission: dict, path: Path = HISTORY) -> None:
    entry = {
        "ts": int(time.time()),
        "label": label,
        "verdict": submission["verdict"],
        "fit_score": submission["fit_score"],
        "interest_score": submission["interest_alignment"]["score"],
        "matched_interests": submission["interest_alignment"]["matched_interests"],
        "skills_to_learn": submission.get("skills_to_learn", []),
    }
    path.parent.mkdir(exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def load_history(path: Path = HISTORY) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # skip a half-written line instead of breaking the page
    return entries


def summarize(days: int = 30, now: float | None = None, path: Path = HISTORY) -> dict:
    cutoff = (now or time.time()) - days * 86400
    runs = [e for e in load_history(path) if e["ts"] >= cutoff]
    n = len(runs)

    # Count each skill once per job, merging "node.js" / "Node.js"; show the most common spelling.
    counts: Counter[str] = Counter()
    spellings: dict[str, Counter[str]] = {}
    for e in runs:
        seen: set[str] = set()
        for skill in (s.strip() for s in e["skills_to_learn"]):
            key = skill.lower()
            if not skill or key in seen:
                continue
            seen.add(key)
            counts[key] += 1
            spellings.setdefault(key, Counter())[skill] += 1

    interests: Counter[str] = Counter(i for e in runs for i in e["matched_interests"])

    return {
        "days": days,
        "jobs": n,
        "verdicts": dict(Counter(e["verdict"] for e in runs)),
        "avg_fit": round(sum(e["fit_score"] for e in runs) / n) if n else None,
        "avg_interest": round(sum(e["interest_score"] for e in runs) / n) if n else None,
        "top_skills_to_learn": [
            {"skill": spellings[k].most_common(1)[0][0], "jobs": c, "share": round(c / n, 2)}
            for k, c in counts.most_common(8)
        ],
        "top_interests": [{"interest": i, "jobs": c} for i, c in interests.most_common(5)],
        "recent": [
            {k: e[k] for k in ("ts", "label", "verdict", "fit_score", "interest_score")}
            for e in sorted(runs, key=lambda e: e["ts"], reverse=True)[:5]
        ],
    }
