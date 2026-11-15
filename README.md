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

## Setup (Mac)

```bash
# backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# frontend (in a second terminal)
cd frontend
npm install
```

Copy `.env.example` to `.env` and paste in your key from console.anthropic.com. (The API is billed separately from your Claude subscription. Add a small amount of credit, e.g. $5, which covers many runs.)

## Plan: build it in 4 sessions

**Session 1: see it working (20 min, free).** Run the finished version in demo mode so you know what you're building:
```bash
cd backend && DEMO=1 USE_SOLUTION=1 python app.py     # terminal 1
cd frontend && npm run dev                            # terminal 2, then open http://localhost:5173
```
Paste any job description (100+ characters) and click **Tailor my resume**.

**Session 2: fill in your fact bank.** Open `backend/data/experience.yaml`. Replace every `FILL IN`, check the lines marked `confirm`, and add your other real bullets from your master resume. Better facts give better resumes. Run `python -m pytest -q` afterwards to make sure the file still loads.

**Session 3: write the agent loop (the resume-worthy part).** Open `backend/agent.py` and follow TODO 1–5 in `run_agent`. Check yourself with the fake Claude client (free, no API key needed):
```bash
cd backend && python -m pytest tests/test_agent.py -q
```
When all 6 tests pass, your loop works. If you're stuck for more than about 20 minutes, look at `solutions/agent_solution.py`, then close it and write your own.

**Session 4: real runs.** With your key in `.env`:
```bash
cd backend && python app.py
```
Try 3–4 real job descriptions. Read the output critically. If a bullet is weak, the fix is usually a better fact in `experience.yaml` or a tweak to `SYSTEM_PROMPT`.

## Then make it resume-ready
- Push to GitHub with this README and a short screen recording or GIF of a run.
- Add an eval: save 10 real job descriptions with the verdict you'd give each (`evals/cases.yaml`), write a script that runs the agent on all of them, and report how often it agrees with you. Put that number in your resume bullet.
- Optional: deploy with Docker, which is good practice for your Kubernetes learning.

## Things to be ready to explain in interviews
- Why the API is stateless, and why the loop resends the whole `messages` history every turn.
- How `tool_use_id` links each `tool_result` to Claude's request, and why parallel tool calls go back in one message.
- Why the checks live in code instead of in the prompt (prompts can be ignored; code can't).
- Why there's a turn limit (`MAX_TURNS`): cost and runaway loops.
- What the number check can't catch (e.g. an invented claim with no numbers), and how you'd improve it (a second LLM pass that judges each bullet against its facts).
