import shutil

import pytest

from profile_store import load_profile
from render import compile_pdf, render_tex
from tests.test_tools import good_submission

P = load_profile()


def test_tex_escapes_special_characters():
    sub = good_submission(summary="R&D engineer, 100% focused on C# and_more")
    tex = render_tex(sub, P)
    assert r"R\&D" in tex and r"100\%" in tex and r"C\#" in tex and r"and\_more" in tex


@pytest.mark.skipif(not shutil.which("pdflatex"), reason="pdflatex not installed")
def test_pdf_compiles(tmp_path):
    assert compile_pdf(render_tex(good_submission(), P), tmp_path / "r.pdf")
