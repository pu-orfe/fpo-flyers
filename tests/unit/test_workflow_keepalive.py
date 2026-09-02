"""Tests for the scheduled-workflow keepalive step in generate.yml.

GitHub disables scheduled workflows after 60 days without repository
activity. The ICS feed can sit unchanged for an entire summer, producing no
commits, so the check job pushes a dated no-op commit before that window
closes. These tests exercise the real shell script lifted out of the YAML.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "generate.yml"
STEP_NAME = "Keep scheduled workflow alive"


@pytest.fixture(scope="module")
def workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def keepalive_step(workflow: dict) -> dict:
    steps = workflow["jobs"]["check"]["steps"]
    matches = [s for s in steps if s.get("name") == STEP_NAME]
    assert matches, f"{STEP_NAME!r} step missing from the check job"
    return matches[0]


def test_keepalive_runs_only_on_schedule(keepalive_step: dict) -> None:
    """Manual dispatch already counts as activity; don't commit on it."""
    assert keepalive_step["if"] == "github.event_name == 'schedule'"


def test_keepalive_lives_in_the_always_running_job(workflow: dict) -> None:
    """The generate job is skipped when the feed is unchanged, which is
    exactly the quiet stretch that triggers deactivation. The keepalive has
    to live in check, which runs on every scheduled tick."""
    check_steps = {s.get("name") for s in workflow["jobs"]["check"]["steps"]}
    generate_steps = {s.get("name") for s in workflow["jobs"]["generate"]["steps"]}
    assert STEP_NAME in check_steps
    assert STEP_NAME not in generate_steps


def test_hash_commit_rebases_before_push(workflow: dict) -> None:
    """The keepalive can push after the generate job checked out, so the
    hash commit must rebase or its push is rejected non-fast-forward."""
    steps = workflow["jobs"]["generate"]["steps"]
    commit = next(s for s in steps if s.get("name") == "Commit hash file")
    run = commit["run"]
    assert "git pull --rebase" in run
    assert run.index("git pull --rebase") < run.index("git push")


def _make_repo(tmp_path: Path, days_ago: int) -> Path:
    """A clone whose HEAD commit is `days_ago` days old, with a real remote."""
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(remote)], check=True,
                   capture_output=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", str(remote), str(work)], check=True,
                   capture_output=True)

    env_git = {
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }
    stamp = subprocess.run(
        ["python3", "-c",
         f"import time;print(int(time.time()) - {days_ago} * 86400)"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    date = f"{stamp} +0000"
    (work / "README.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=work, check=True,
                   capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed"],
        cwd=work, check=True, capture_output=True,
        env={**env_git, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date,
             "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=work, check=True,
                   capture_output=True)
    return work


def _run_keepalive(step: dict, repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        cwd=repo, capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(repo.parent)},
    )


def test_keepalive_noop_when_repo_is_active(keepalive_step, tmp_path) -> None:
    repo = _make_repo(tmp_path, days_ago=10)
    before = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                            capture_output=True, text=True).stdout
    result = _run_keepalive(keepalive_step, repo)
    assert result.returncode == 0, result.stderr
    assert "no keepalive needed" in result.stdout
    after = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                           capture_output=True, text=True).stdout
    assert before == after


def test_keepalive_commits_before_the_60_day_cutoff(keepalive_step, tmp_path) -> None:
    repo = _make_repo(tmp_path, days_ago=55)
    result = _run_keepalive(keepalive_step, repo)
    assert result.returncode == 0, result.stderr
    subject = subprocess.run(["git", "log", "-1", "--format=%s"], cwd=repo,
                             check=True, capture_output=True, text=True).stdout
    assert "Keepalive" in subject
    assert "[skip ci]" in subject
    assert (repo / ".keepalive").exists()
    # And it actually reached the remote, which is what resets the timer.
    remote_head = subprocess.run(
        ["git", "log", "-1", "--format=%s", "origin/main"],
        cwd=repo, check=True, capture_output=True, text=True).stdout
    assert "Keepalive" in remote_head


def test_keepalive_fires_with_margin_before_deactivation(keepalive_step) -> None:
    """Threshold must leave room for the 30-minute cron to land a run."""
    run = keepalive_step["run"]
    assert '"$AGE_DAYS" -lt 50' in run
