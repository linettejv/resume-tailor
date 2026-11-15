# Resume Tailor

Paste a job description from LinkedIn, Wellfound or InstaHire. A Claude agent checks how well you fit, lists the gaps, and rewrites your resume for that job, **using only facts from your own fact bank**. Every bullet has to cite the facts it comes from, and code (not the model) checks this before anything is accepted.

```
 React UI ──► Flask /api/tailor ──► agent loop ──► Claude API
                                       │  ▲
                          tool calls   ▼  │  tool results (or errors)
                         get_profile · check_bullets · submit_tailored_resume
                                       │
                                       ▼
                        validated submission ──► .tex (+ PDF) download
```

## How it works

| File | What it does |
|---|---|
| `backend/data/experience.yaml` | Your fact bank. The only source of truth about you. |
| `backend/tools.py` | The 3 tools Claude can call, plus the checks: facts must exist, belong to the right job, and every number in a bullet must appear in the cited facts. |
| `backend/agent.py` | **The agent loop. You write this part** (see below). |
| `backend/render.py` | Fills the LaTeX template; compiles a PDF if `pdflatex` is installed. |
| `backend/app.py` | Flask API. |
| `backend/demo.py` | `DEMO=1` mode: replays a scripted run with no API calls. |
| `frontend/src/App.jsx` | The React page. |

The verification loop is the interesting part. If Claude writes "Cut load time by 35%" and no fact says 35%, `submit_tailored_resume` returns an error (`is_error: true`) listing the problem, and Claude has to fix it and resubmit. The UI shows this in "What the agent did".

- How `tool_use_id` links each `tool_result` to Claude's request, and why parallel tool calls go back in one message.
- Why the checks live in code instead of in the prompt (prompts can be ignored; code can't).
- Why there's a turn limit (`MAX_TURNS`): cost and runaway loops.
- What the number check can't catch (e.g. an invented claim with no numbers), and how you'd improve it (a second LLM pass that judges each bullet against its facts).
