"""The tools the agent can call, and the checks that keep it honest.

Three tools:
  get_profile             -> returns your fact bank (skills, roles, facts with ids)
  check_bullets           -> verifies draft bullets against the fact bank
  submit_tailored_resume  -> final answer; rejected with errors if anything fails a check

The model decides when to call each one. Our code never trusts its output:
every submission goes through the same checks as check_bullets.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from profile_store import Profile

MAX_BULLET_CHARS = 230
MAX_BULLETS_PER_SECTION = 6
VERDICTS = ["apply", "apply_with_caveats", "skip"]

# ---------------------------------------------------------------------------
# Tool definitions sent to Claude (name, description, JSON schema for input)
# ---------------------------------------------------------------------------

_BULLET_SCHEMA = {
    "type": "object",
    "properties": {
        "section_id": {"type": "string", "description": "Role or project id from get_profile, e.g. 'pencil'."},
        "text": {"type": "string", "description": "The resume bullet, one sentence, starting with a verb."},
        "fact_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Ids of the facts that back this bullet. Must belong to section_id.",
        },
    },
    "required": ["section_id", "text", "fact_ids"],
}

TOOL_DEFINITIONS = [
    {
        "name": "get_profile",
        "description": (
            "Returns the candidate's fact bank: basics, allowed skills, skills they are "
            "currently learning, and every role/project with its facts and fact ids. "
            "This is the only source of truth about the candidate. Call it first."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "check_bullets",
        "description": (
            "Checks draft resume bullets against the fact bank before you submit. "
            "Returns a list of problems per bullet (unknown fact ids, facts from the wrong "
            "section, numbers not found in the cited facts, too long). Fix every problem."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"bullets": {"type": "array", "items": _BULLET_SCHEMA}},
            "required": ["bullets"],
        },
    },
    {
        "name": "submit_tailored_resume",
        "description": (
            "Submit the final tailored resume and fit assessment. The submission is "
            "validated; if it fails you get an error listing what to fix, and must resubmit."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": VERDICTS},
                "fit_score": {"type": "integer", "minimum": 0, "maximum": 100},
                "verdict_reason": {"type": "string", "description": "2-3 sentences, candid."},
                "summary": {"type": "string", "description": "2-line resume summary tailored to the job."},
                "summary_fact_ids": {"type": "array", "items": {"type": "string"}},
                "matched_requirements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "requirement": {"type": "string"},
                            "fact_ids": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["requirement", "fact_ids"],
                    },
                },
                "gaps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Job requirements the fact bank does NOT support. Never hide these.",
                },
                "skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Skills to show, most relevant first. Only from the profile's skills list.",
                },
                "bullets": {"type": "array", "items": _BULLET_SCHEMA},
            },
            "required": [
                "verdict", "fit_score", "verdict_reason", "summary", "summary_fact_ids",
                "matched_requirements", "gaps", "skills", "bullets",
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def _numbers(text: str) -> set[str]:
    return {n.replace(",", "") for n in _NUMBER.findall(text)}


def check_claim(text: str, fact_ids: list[str], profile: Profile, section_id: str | None = None) -> list[str]:
    """Problems with one claim (a bullet or the summary). Empty list = OK."""
    problems = []
    if not fact_ids:
        problems.append("cites no fact ids; every claim must be backed by at least one fact")
    unknown = [f for f in fact_ids if f not in profile.facts]
    if unknown:
        problems.append(f"unknown fact ids {unknown}")
    known = [f for f in fact_ids if f in profile.facts]
    if section_id is not None:
        if section_id not in profile.section_ids:
            problems.append(f"unknown section_id '{section_id}'")
        wrong = [f for f in known if profile.fact_owner[f] != section_id]
        if wrong:
            problems.append(f"facts {wrong} belong to a different section than '{section_id}'")
    source = " ".join(profile.facts[f]["text"] for f in known)
    invented = sorted(_numbers(text) - _numbers(source))
    if invented:
        problems.append(f"numbers {invented} do not appear in the cited facts; remove them or cite the right fact")
    return problems


def check_bullets(bullets: list[dict], profile: Profile) -> list[dict]:
    report = []
    for i, b in enumerate(bullets):
        problems = check_claim(b.get("text", ""), b.get("fact_ids", []), profile, b.get("section_id"))
        if len(b.get("text", "")) > MAX_BULLET_CHARS:
            problems.append(f"too long ({len(b['text'])} chars, max {MAX_BULLET_CHARS})")
        report.append({"index": i, "text": b.get("text", ""), "ok": not problems, "problems": problems})
    return report


def validate_submission(sub: dict, profile: Profile) -> list[str]:
    """Every reason this submission can't be accepted. Empty list = accepted."""
    errors = []
    if sub.get("verdict") not in VERDICTS:
        errors.append(f"verdict must be one of {VERDICTS}")
    score = sub.get("fit_score")
    if not isinstance(score, int) or not 0 <= score <= 100:
        errors.append("fit_score must be an integer 0-100")

    for p in check_claim(sub.get("summary", ""), sub.get("summary_fact_ids", []), profile):
        errors.append(f"summary: {p}")

    allowed = {s.lower(): s for s in profile.skills}
    extra = [s for s in sub.get("skills", []) if s.lower() not in allowed]
    if extra:
        errors.append(f"skills {extra} are not in the profile; move real gaps to 'gaps' instead")

    for m in sub.get("matched_requirements", []):
        bad = [f for f in m.get("fact_ids", []) if f not in profile.facts]
        if not m.get("fact_ids") or bad:
            errors.append(f"matched requirement '{m.get('requirement')}' needs valid fact ids (bad: {bad})")

    bullets = sub.get("bullets", [])
    if not bullets:
        errors.append("no bullets submitted")
    for r in check_bullets(bullets, profile):
        if not r["ok"]:
            errors.append(f"bullet {r['index']} ('{r['text'][:60]}...'): " + "; ".join(r["problems"]))
    per_section: dict[str, int] = {}
    for b in bullets:
        per_section[b.get("section_id")] = per_section.get(b.get("section_id"), 0) + 1
    for sec, n in per_section.items():
        if n > MAX_BULLETS_PER_SECTION:
            errors.append(f"section '{sec}' has {n} bullets; max {MAX_BULLETS_PER_SECTION}")
    return errors


# ---------------------------------------------------------------------------
# Dispatcher: what agent.py calls when Claude asks for a tool
# ---------------------------------------------------------------------------

@dataclass
class ToolOutcome:
    content: str              # text sent back to Claude in the tool_result block
    is_error: bool = False    # True -> Claude is told the call failed and should fix it
    final: dict | None = None # set only when submit_tailored_resume is accepted


def run_tool(name: str, tool_input: dict, profile: Profile) -> ToolOutcome:
    if name == "get_profile":
        return ToolOutcome(json.dumps(profile.raw, indent=1))

    if name == "check_bullets":
        report = check_bullets(tool_input.get("bullets", []), profile)
        return ToolOutcome(json.dumps(report, indent=1))

    if name == "submit_tailored_resume":
        errors = validate_submission(tool_input, profile)
        if errors:
            return ToolOutcome(
                "Submission rejected. Fix these and call submit_tailored_resume again:\n- "
                + "\n- ".join(errors),
                is_error=True,
            )
        return ToolOutcome("Accepted.", final=tool_input)

    return ToolOutcome(f"Unknown tool '{name}'", is_error=True)
