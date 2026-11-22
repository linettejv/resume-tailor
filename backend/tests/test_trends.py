from trends import record_run, summarize
from tests.test_tools import good_submission


def test_trends_count_each_skill_once_per_job(tmp_path):
    h = tmp_path / "history.jsonl"
    record_run("a", good_submission(skills_to_learn=["Node.js", "AWS", "node.js"]), h)
    record_run("b", good_submission(skills_to_learn=["node.js", "Docker Swarm"]), h)
    record_run("c", good_submission(verdict="skip", skills_to_learn=["AWS"]), h)
    t = summarize(30, path=h)
    assert t["jobs"] == 3
    top = {s["skill"].lower(): s["jobs"] for s in t["top_skills_to_learn"]}
    assert top["node.js"] == 2 and top["aws"] == 2
    assert t["verdicts"] == {"apply": 2, "skip": 1}


def test_old_runs_drop_out_of_window(tmp_path):
    h = tmp_path / "history.jsonl"
    record_run("a", good_submission(), h)
    assert summarize(30, now=10**10, path=h)["jobs"] == 0


def test_empty_history(tmp_path):
    t = summarize(30, path=tmp_path / "none.jsonl")
    assert t["jobs"] == 0 and t["avg_fit"] is None
