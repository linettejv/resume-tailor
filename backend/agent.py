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
3. Score two things separately:
   - fit_score: how well the candidate's CURRENT skills and facts match the job.
   - interest_alignment: how well the job moves them towards the areas in their 'interests' list.
   Then decide a verdict (apply, apply_with_caveats, or skip) using both. A strong skill fit in an
   area they want to leave is worth less than a decent fit in an area they want to grow into.
   Be honest; a wasted application costs the candidate time.
   List the job's required skills they don't have in skills_to_learn, using short standard names.
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

  
    for turn in range(1, MAX_TURNS + 1):
        result.turns = turn

        response = client.messages.create(
            model=model,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            max_tokens=MAX_TOKENS,
            messages=messages
         )
        result.input_tokens += response.usage.input_tokens
        result.output_tokens += response.usage.output_tokens

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            result.stopped_reason = f"model stopped ({response.stop_reason}) without submitting"
            messages.append({
                "role": "user",
                "content": "You haven't submitted yet. Call the submit_tailored_resume tool with your final answer.",
            })
            continue

        tool_results = []
        
        for block in response.content:
            if block.type == "tool_use":
                outcome = run_tool(block.name, block.input, profile)

            # for the ui 
                result.trace.append({
                    "turn": turn,
                    "tool": block.name,
                    "is_error": outcome.is_error,
                    "summary": outcome.content[:300],   # first 300 chars, to keep it short
                })

            # for the ai     
                tool_results.append({
                    "type" : "tool_result",
                    "tool_use_id":block.id,
                    "content": outcome.content,
                    "is_error": outcome.is_error
                })
    

                if outcome.final is not None:
                    result.submission = outcome.final
                    result.stopped_reason = "submitted"
                    return result

            messages.append({"role": "user", "content": tool_results})

    result.stopped_reason = f"gave up after {MAX_TURNS} turns ({result.stopped_reason or 'no submission'})"
    return result
