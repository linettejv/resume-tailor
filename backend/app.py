"""Flask API.

POST /api/tailor        {"job_description": "...", "label": "razorpay-frontend"}  -> verdict, bullets, trace
GET  /api/files/<name>  download a generated .tex or .pdf
GET  /api/health
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request, send_from_directory
from flask_cors import CORS

load_dotenv(Path(__file__).parent.parent / ".env")

if os.getenv("USE_SOLUTION") == "1":
    # Try the finished app before you've written your part of agent.py.
    from solutions.agent_solution import MODEL, run_agent
else:
    from agent import MODEL, run_agent
from profile_store import load_profile
from render import compile_pdf, render_tex

OUTPUT = Path(__file__).parent / "output"
OUTPUT.mkdir(exist_ok=True)

app = Flask(__name__)
CORS(app)  # the Vite dev server runs on another port


def make_client():
    if os.getenv("DEMO") == "1":
        from demo import demo_client
        return demo_client()
    import anthropic  # imported here so tests don't need an API key
    return anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment


@app.get("/api/health")
def health():
    return {"ok": True, "model": MODEL, "has_api_key": bool(os.getenv("ANTHROPIC_API_KEY"))}


@app.post("/api/tailor")
def tailor():
    body = request.get_json(silent=True) or {}
    jd = (body.get("job_description") or "").strip()
    if len(jd) < 100:
        return jsonify(error="Paste the full job description (at least 100 characters)."), 400
    if not os.getenv("ANTHROPIC_API_KEY") and os.getenv("DEMO") != "1":
        return jsonify(error="ANTHROPIC_API_KEY is not set. Add it to the .env file and restart."), 500

    profile = load_profile()  # re-read each time so edits to experience.yaml apply immediately
    started = time.time()
    try:
        result = run_agent(jd, profile, make_client())
    except Exception as e:  # surface API errors (bad key, rate limit) to the UI
        return jsonify(error=f"{type(e).__name__}: {e}"), 502

    payload = {
        "trace": result.trace,
        "turns": result.turns,
        "tokens": {"input": result.input_tokens, "output": result.output_tokens},
        "seconds": round(time.time() - started, 1),
        "stopped_reason": result.stopped_reason,
        "submission": result.submission,
        "facts": {fid: f["text"] for fid, f in profile.facts.items()},
    }
    if result.submission is None:
        return jsonify(payload | {"error": "The agent couldn't produce a valid resume. See the trace."}), 422

    label = re.sub(r"[^a-z0-9]+", "-", (body.get("label") or "job").lower()).strip("-") or "job"
    stem = f"resume_{label}_{time.strftime('%Y%m%d_%H%M%S')}"
    tex = render_tex(result.submission, profile)
    (OUTPUT / f"{stem}.tex").write_text(tex)
    payload["files"] = {"tex": f"{stem}.tex"}
    if compile_pdf(tex, OUTPUT / f"{stem}.pdf"):
        payload["files"]["pdf"] = f"{stem}.pdf"
    return jsonify(payload)


@app.get("/api/files/<path:name>")
def files(name: str):
    if not re.fullmatch(r"resume_[a-z0-9-]+_\d{8}_\d{6}\.(tex|pdf)", name):
        abort(404)
    return send_from_directory(OUTPUT, name, as_attachment=True)


if __name__ == "__main__":
    app.run(port=5001, debug=True)
