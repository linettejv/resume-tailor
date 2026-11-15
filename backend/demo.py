"""DEMO=1 mode: a scripted run with no API calls, for working on the UI for free.

It replays a realistic run, including one rejected submission, so you can see the
verification loop in the UI.
"""
from tests.fakes import FakeClient, response, text, tool_use

_BULLETS = [
    {"section_id": "pencil", "fact_ids": ["react-query"],
     "text": "Built data-heavy React screens with React Query for fetching, caching and server-state management."},
    {"section_id": "pencil", "fact_ids": ["canvas-rendering", "loader-refactor"],
     "text": "Built a Lexical-based text layer, migrated canvas rendering to Skia / CanvasKit, and refactored the asset loader to useSyncExternalStore across 8 call sites."},
    {"section_id": "pencil", "fact_ids": ["flask-apis", "sheets-pipeline"],
     "text": "Built Flask REST APIs and rebuilt a cron-based Google Sheets sync into a tracked RabbitMQ pipeline, halving API calls per sync."},
    {"section_id": "pencil", "fact_ids": ["pr-reviews"],
     "text": "Reviewed 673 pull requests across 3 repositories, raising frontend code quality."},
    {"section_id": "pencil", "fact_ids": ["customers"],
     "text": "Spoke directly with customers to understand their problems and shape product fixes."},
    {"section_id": "resume-tailor", "fact_ids": ["rt-agent", "rt-verify"],
     "text": "Built a resume-tailoring agent (Claude API, tool calling, Flask, React) with a verification step that rejects unsupported claims."},
]

_SUBMISSION = {
    "verdict": "apply",
    "fit_score": 81,
    "verdict_reason": "Strong match on React, rendering performance and API work. The main gap is TypeScript, "
                      "which the role lists as required and your fact bank doesn't mention yet.",
    "summary": "Frontend-leaning full-stack engineer, 3+ years building a production product with React, "
               "canvas rendering and Flask APIs.",
    "summary_fact_ids": ["tenure", "react-query", "canvas-rendering", "flask-apis"],
    "matched_requirements": [
        {"requirement": "React and modern state management", "fact_ids": ["react-query", "loader-refactor"]},
        {"requirement": "Rendering performance", "fact_ids": ["canvas-rendering"]},
        {"requirement": "Working with backend APIs", "fact_ids": ["flask-apis"]},
        {"requirement": "Code quality and reviews", "fact_ids": ["pr-reviews"]},
    ],
    "gaps": ["TypeScript (add it to experience.yaml if you've used it)", "Design systems / component libraries"],
    "skills": ["React", "React Query", "JavaScript", "Skia / CanvasKit", "WebGL", "D3.js", "Python", "Flask", "REST APIs"],
    "bullets": _BULLETS,
}

_BAD = {**_SUBMISSION, "bullets": [
    {**_BULLETS[0], "text": "Cut page load time by 35% with React Query caching."}, *_BULLETS[1:]
]}


def demo_client() -> FakeClient:
    return FakeClient([
        response(text("I'll read the profile first."), tool_use("d1", "get_profile", {})),
        response(tool_use("d2", "check_bullets", {"bullets": _BAD["bullets"]})),
        response(tool_use("d3", "submit_tailored_resume", _BAD)),
        response(tool_use("d4", "submit_tailored_resume", _SUBMISSION)),
    ])
