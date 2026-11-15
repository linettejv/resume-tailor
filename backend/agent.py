"""The agent: Claude + tools in a loop until it submits a resume that passes every check."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from profile_store import Profile
from tools import TOOL_DEFINITIONS, run_tool

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_TURNS = 10          # hard stop so a confused model can't loop (and spend) forever
MAX_TOKENS = 4096

SYSTEM_PROMPT = """You are a candid career coach and resume writer.

You get a job description. Your job:
1. Call get_profile to read the candidate's fact bank. It is the ONLY source of truth.
2. Pick the job's 5-8 most important requirements and match each to facts.
3. Decide a verdict: apply, apply_with_caveats, or skip. Be honest; a wasted application costs the candidate time.
4. Write tailored bullets that use the job's language where the facts truly support it.
   Every bullet must cite the fact ids it comes from. Never add numbers, tools or outcomes
   that aren't in the cited facts. Rewording and reordering is fine; inventing is not.
5. Call check_bullets on your drafts and fix every problem.
6. Call submit_tailored_resume. If it is rejected, fix the listed problems and resubmit.

Put unsupported requirements in 'gaps' instead of stretching the facts.
Skills the candidate is only learning must never appear as experience."""


@dataclass
class AgentResult:
    submission: dict | None                          # the accepted submission, or None if the agent gave up
    trace: list[dict] = field(default_factory=list)  # every tool call, for the UI and for debugging
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    stopped_reason: str = ""


def run_agent(job_description: str, profile: Profile, client, model: str = MODEL) -> AgentResult:
    """Run the tool-use loop.

    `client` is an anthropic.Anthropic() instance (or a fake one in tests).
    """
    result = AgentResult(submission=None)
    messages = [{"role": "user", "content": f"Job description:\n\n{job_description}"}]

    # ---------------------------------------------------------------------
    # YOUR PART, Linette. Tests in tests/test_agent.py tell you when it works:
    #     cd backend && python -m pytest tests/test_agent.py -q
    # Stuck for more than ~20 minutes? Peek at solutions/agent_solution.py.
    # ---------------------------------------------------------------------
    for turn in range(1, MAX_TURNS + 1):
        result.turns = turn

        # TODO 1: Call Claude.
        #   response = client.messages.create(model=..., max_tokens=MAX_TOKENS,
        #                                     system=SYSTEM_PROMPT, tools=TOOL_DEFINITIONS, messages=messages)
        #   Then add response.usage.input_tokens / output_tokens to result.input_tokens / output_tokens.
        raise NotImplementedError("TODO 1: call client.messages.create")

        # TODO 2: Append Claude's turn to `messages` as {"role": "assistant", "content": response.content}.
        #   Why: the API is stateless. Claude only "remembers" what you send back each time.

        # TODO 3: If response.stop_reason != "tool_use", Claude answered in plain text instead of
        #   submitting. Set result.stopped_reason, append a user message nudging it to call
        #   submit_tailored_resume, and `continue` to the next turn.

        # TODO 4: Otherwise, loop over response.content. For each block with block.type == "tool_use":
        #   - outcome = run_tool(block.name, block.input, profile)
        #   - add {"turn", "tool", "is_error", "summary": outcome.content[:300]} to result.trace
        #   - build a tool_result block:
        #       {"type": "tool_result", "tool_use_id": block.id,
        #        "content": outcome.content, "is_error": outcome.is_error}
        #   - if outcome.final is not None: the submission passed every check. Save it in
        #     result.submission, set result.stopped_reason = "submitted", and return result.

        # TODO 5: Append ALL the tool_result blocks in ONE user message:
        #   {"role": "user", "content": tool_results}
        #   (Claude can ask for several tools at once; each needs its own result, same message.)

    result.stopped_reason = f"gave up after {MAX_TURNS} turns ({result.stopped_reason or 'no submission'})"
    return result
