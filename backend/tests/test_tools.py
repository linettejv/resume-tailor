import json

from profile_store import load_profile
from tools import check_bullets, run_tool, validate_submission

P = load_profile()


def good_submission(**overrides):
    sub = {
        "verdict": "apply",
        "fit_score": 82,
        "verdict_reason": "Strong React and Flask match.",
        "summary": "Full-stack engineer who rebuilt a sync into a RabbitMQ pipeline.",
        "summary_fact_ids": ["sheets-pipeline"],
        "matched_requirements": [{"requirement": "Message queues", "fact_ids": ["sheets-pipeline"]}],
        "gaps": ["Kubernetes in production"],
        "skills": ["React", "python", "RabbitMQ"],
        "bullets": [
            {"section_id": "pencil", "text": "Reviewed 673 pull requests across 3 repositories.", "fact_ids": ["pr-reviews"]},
        ],
    }
    return sub | overrides


def test_good_submission_passes():
    assert validate_submission(good_submission(), P) == []


def test_invented_number_is_caught():
    r = check_bullets([{"section_id": "pencil", "text": "Cut latency by 40%.", "fact_ids": ["sheets-pipeline"]}], P)
    assert not r[0]["ok"] and "40" in r[0]["problems"][0]


def test_unknown_fact_and_wrong_section():
    r = check_bullets([
        {"section_id": "pencil", "text": "Did things.", "fact_ids": ["made-up"]},
        {"section_id": "pencil", "text": "Built an email agent.", "fact_ids": ["email-agent"]},
    ], P)
    assert "unknown fact ids" in r[0]["problems"][0]
    assert "different section" in r[1]["problems"][0]


def test_skill_not_in_profile_rejected():
    errors = validate_submission(good_submission(skills=["React", "Kubernetes"]), P)
    assert any("Kubernetes" in e for e in errors)


def test_rejected_submission_is_tool_error():
    out = run_tool("submit_tailored_resume", good_submission(bullets=[]), P)
    assert out.is_error and out.final is None


def test_get_profile_returns_fact_bank():
    out = run_tool("get_profile", {}, P)
    assert "sheets-pipeline" in out.content and json.loads(out.content)["basics"]
