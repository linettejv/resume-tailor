"""Tests for run_agent in agent.py, using a scripted fake Claude. No API key needed.

Run:  cd backend && python -m pytest -q
"""
from agent import run_agent
from profile_store import load_profile
from tests.fakes import FakeClient, response, text, tool_use
from tests.test_tools import good_submission

P = load_profile()
JD = "Frontend engineer, React, REST APIs, message queues. " * 5


def test_happy_path_returns_submission():
    client = FakeClient([
        response(text("Reading the profile."), tool_use("t1", "get_profile", {})),
        response(tool_use("t2", "submit_tailored_resume", good_submission())),
    ])
    result = run_agent(JD, P, client)
    assert result.submission is not None
    assert result.submission["verdict"] == "apply"
    assert [t["tool"] for t in result.trace] == ["get_profile", "submit_tailored_resume"]
    assert result.input_tokens == 200


def test_tool_result_goes_back_with_matching_id():
    client = FakeClient([
        response(tool_use("toolu_abc", "get_profile", {})),
        response(tool_use("t2", "submit_tailored_resume", good_submission())),
    ])
    run_agent(JD, P, client)
    second_call = client.calls[1]
    assert second_call[-2]["role"] == "assistant"          # Claude's turn is kept in history
    last = second_call[-1]
    assert last["role"] == "user"
    assert last["content"][0]["type"] == "tool_result"
    assert last["content"][0]["tool_use_id"] == "toolu_abc"


def test_rejected_submission_lets_agent_retry():
    bad = good_submission(bullets=[{"section_id": "pencil", "text": "Cut costs by 90%.", "fact_ids": ["pr-reviews"]}])
    client = FakeClient([
        response(tool_use("t1", "submit_tailored_resume", bad)),
        response(tool_use("t2", "submit_tailored_resume", good_submission())),
    ])
    result = run_agent(JD, P, client)
    error_result = client.calls[1][-1]["content"][0]
    assert error_result["is_error"] is True and "90" in error_result["content"]
    assert result.submission is not None and result.turns == 2


def test_parallel_tool_calls_answered_in_one_message():
    client = FakeClient([
        response(
            tool_use("a", "get_profile", {}),
            tool_use("b", "check_bullets", {"bullets": good_submission()["bullets"]}),
        ),
        response(tool_use("c", "submit_tailored_resume", good_submission())),
    ])
    run_agent(JD, P, client)
    ids = [block["tool_use_id"] for block in client.calls[1][-1]["content"]]
    assert ids == ["a", "b"]


def test_gives_up_after_max_turns():
    from agent import MAX_TURNS
    client = FakeClient([response(tool_use(f"t{i}", "get_profile", {})) for i in range(MAX_TURNS)])
    result = run_agent(JD, P, client)
    assert result.submission is None
    assert "gave up" in result.stopped_reason


def test_model_stopping_early_gets_a_nudge():
    client = FakeClient([
        response(text("Here is my answer in plain text."), stop_reason="end_turn"),
        response(tool_use("t1", "submit_tailored_resume", good_submission())),
    ])
    result = run_agent(JD, P, client)
    assert result.submission is not None
    assert "submit_tailored_resume" in client.calls[1][-1]["content"]
