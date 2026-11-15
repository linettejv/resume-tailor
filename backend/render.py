"""Turns an accepted submission into a .tex file (and a PDF if pdflatex is installed)."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from profile_store import Profile

TEMPLATES = Path(__file__).parent / "templates"

_LATEX_SPECIALS = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
    "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
}


def latex_escape(value) -> str:
    return "".join(_LATEX_SPECIALS.get(ch, ch) for ch in str(value))


_env = Environment(
    loader=FileSystemLoader(TEMPLATES),
    block_start_string="((*", block_end_string="*))",
    variable_start_string="(((", variable_end_string=")))",
    comment_start_string="((=", comment_end_string="=))",
    trim_blocks=True, lstrip_blocks=True,
    finalize=lambda v: latex_escape(v) if isinstance(v, str) else v,
)


def render_tex(submission: dict, profile: Profile) -> str:
    raw = profile.raw
    by_section: dict[str, list[str]] = {}
    for b in submission["bullets"]:
        by_section.setdefault(b["section_id"], []).append(b["text"])

    roles = [{**r, "bullets": by_section.get(r["id"], [])} for r in raw.get("roles", [])]
    projects = [
        {**p, "bullets": by_section[p["id"]]}
        for p in raw.get("projects", []) if p["id"] in by_section
    ]
    for p in projects:
        if str(p.get("link", "")).startswith("FILL IN"):
            p["link"] = ""

    return _env.get_template("resume.tex.j2").render(
        b=raw["basics"],
        summary=submission["summary"],
        skills=submission["skills"],
        learning=raw.get("learning", []),
        roles=roles,
        projects=projects,
        education=raw.get("education", []),
    )


def compile_pdf(tex: str, out_pdf: Path) -> bool:
    """Compile with pdflatex if it's installed. Returns False if not available or it fails."""
    if not shutil.which("pdflatex"):
        return False
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "resume.tex"
        src.write_text(tex)
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "resume.tex"],
            cwd=tmp, capture_output=True, timeout=60,
        )
        pdf = Path(tmp) / "resume.pdf"
        if result.returncode != 0 or not pdf.exists():
            return False
        shutil.copy(pdf, out_pdf)
        return True
