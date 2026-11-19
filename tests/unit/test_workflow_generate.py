"""generate.yml must never push to main.

main is protected by a ruleset that requires CI (see .github/rulesets/main.json).
The built-in GitHub Actions token cannot be exempted from it, so the workflow
keeps no state in git:

- the feed hash is published with the Pages site as feed_hash.txt, and the
  check job reads the last deployed hash from there;
- the keepalive re-enables the workflow through the API instead of pushing a
  dated commit.

The step scripts are lifted from the YAML and run against stub `curl` and `gh`
commands on PATH, so these tests exercise the real shell.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

import pytest
import yaml

from fpo_flyers.feed import compute_feed_hash

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "generate.yml"
FEED = (ROOT / "tests" / "fixtures" / "sample_feed.ics").read_text(encoding="utf-8")
PAGES_URL = "https://example.github.io/repo/"


@pytest.fixture(scope="module")
def workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _step(workflow: dict, job: str, name: str) -> dict:
    matches = [s for s in workflow["jobs"][job]["steps"] if s.get("name") == name]
    assert matches, f"{name!r} missing from {job}"
    return matches[0]


def _all_runs(workflow: dict) -> str:
    return "\n".join(s.get("run", "") for j in workflow["jobs"].values() for s in j["steps"])


# --- no state in git --------------------------------------------------------


def test_never_commits_or_pushes(workflow: dict) -> None:
    runs = _all_runs(workflow)
    assert "git push" not in runs
    assert "git commit" not in runs


def test_read_only_repository_token(workflow: dict) -> None:
    assert workflow["permissions"] == {"contents": "read"}
    for name, job in workflow["jobs"].items():
        assert job.get("permissions", {}).get("contents", "read") == "read", name


def test_check_job_permissions(workflow: dict) -> None:
    # pages: read to find the site URL; actions: write for the keepalive.
    assert workflow["jobs"]["check"]["permissions"] == {
        "contents": "read",
        "pages": "read",
        "actions": "write",
    }


def test_hash_is_published_with_the_site(workflow: dict) -> None:
    generate = _step(workflow, "generate", "Generate flyers")["run"]
    assert "--hash-file output/feed_hash.txt" in generate
    build = _step(workflow, "generate", "Build site")["run"]
    # Plain cp: if the generator did not write the hash, the build fails.
    assert "cp output/feed_hash.txt _site/feed_hash.txt" in build


# --- the check step ---------------------------------------------------------

CURL_STUB = """#!/bin/sh
# Stub curl. Feed URL: print $FEED_FILE (or fail if FEED_FAIL is set).
# Published hash URL: honour -o/-w and answer with $HASH_STATUS / $HASH_BODY.
out=""; fmt=""; url=""
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    -w) fmt="$2"; shift 2 ;;
    -*) shift ;;
    *) url="$1"; shift ;;
  esac
done
echo "$url" >> "$CALL_LOG"
case "$url" in
  */feed_hash.txt)
    [ -n "$HASH_DOWN" ] && exit 7
    printf '%s' "$HASH_BODY" > "$out"
    [ -n "$fmt" ] && printf '%s' "$HASH_STATUS"
    ;;
  *)
    [ -n "$FEED_FAIL" ] && exit 22
    cat "$FEED_FILE"
    ;;
esac
"""

GH_STUB = """#!/bin/sh
echo "gh $*" >> "$CALL_LOG"
case "$*" in
  "api repos/example/repo/pages --jq .html_url") echo "$PAGES_URL" ;;
  *"--method PUT"*) ;;
  *) echo "unexpected gh call: $*" >&2; exit 1 ;;
esac
"""


def _bin(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    stubs = [("curl", CURL_STUB), ("gh", GH_STUB)]
    if not shutil.which("sha256sum", path="/usr/bin:/bin"):
        # macOS ships shasum instead; same output format. The runner has sha256sum.
        stubs.append(("sha256sum", '#!/bin/sh\nexec shasum -a 256 "$@"\n'))
    for name, text in stubs:
        stub = bin_dir / name
        stub.write_text(text, encoding="utf-8")
        stub.chmod(0o755)
    return bin_dir


def _run_check(
    workflow: dict, tmp_path: Path, **env: str
) -> tuple[subprocess.CompletedProcess, dict]:
    feed_file = tmp_path / "feed.ics"
    feed_file.write_text(FEED, encoding="utf-8")
    output = tmp_path / "github_output"
    output.touch()
    base = {
        "PATH": f"{_bin(tmp_path)}:/usr/bin:/bin",
        "FEED_FILE": str(feed_file),
        "CALL_LOG": str(tmp_path / "calls.log"),
        "GITHUB_OUTPUT": str(output),
        "GITHUB_REPOSITORY": "example/repo",
        "PAGES_URL": PAGES_URL,
        "ICS_FEED_URL": "https://feed.example/ical.ics",
        "HASH_STATUS": "200",
        "HASH_BODY": "",
    }
    script = _step(workflow, "check", "Check feed for changes")["run"]
    result = subprocess.run(
        ["bash", "-e", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env={**base, **env},
    )
    outputs = dict(line.split("=", 1) for line in output.read_text().splitlines() if "=" in line)
    return result, outputs


def test_check_hash_matches_python(workflow, tmp_path) -> None:
    """The shell hash and compute_feed_hash() must agree, or every run regenerates."""
    result, _ = _run_check(workflow, tmp_path, HASH_STATUS="404")
    assert result.returncode == 0, result.stderr
    assert f"current={compute_feed_hash(FEED)}" in result.stdout


def test_check_unchanged_when_published_hash_matches(workflow, tmp_path) -> None:
    result, outputs = _run_check(workflow, tmp_path, HASH_BODY=compute_feed_hash(FEED) + "\n")
    assert result.returncode == 0, result.stderr
    assert outputs == {"changed": "false"}
    calls = (tmp_path / "calls.log").read_text()
    assert f"{PAGES_URL}feed_hash.txt" in calls


def test_check_changed_when_published_hash_differs(workflow, tmp_path) -> None:
    result, outputs = _run_check(workflow, tmp_path, HASH_BODY="0" * 64)
    assert result.returncode == 0, result.stderr
    assert outputs == {"changed": "true"}


def test_check_changed_before_first_publish(workflow, tmp_path) -> None:
    result, outputs = _run_check(workflow, tmp_path, HASH_STATUS="404")
    assert result.returncode == 0, result.stderr
    assert outputs == {"changed": "true"}


@pytest.mark.parametrize(
    "env",
    [
        {"HASH_STATUS": "500"},
        {"HASH_DOWN": "1"},
        {"FEED_FAIL": "1"},
    ],
    ids=["hash-http-500", "hash-unreachable", "feed-unreachable"],
)
def test_check_fails_loudly_on_errors(workflow, tmp_path, env) -> None:
    """An error must fail the run, not silently pass as 'changed' or 'unchanged'."""
    result, outputs = _run_check(workflow, tmp_path, **env)
    assert result.returncode != 0
    assert "changed" not in outputs


# --- the keepalive ----------------------------------------------------------


def test_keepalive_runs_only_on_schedule(workflow) -> None:
    step = _step(workflow, "check", "Keep scheduled workflow alive")
    assert step["if"] == "github.event_name == 'schedule'"


def test_keepalive_lives_in_the_always_running_job(workflow) -> None:
    """generate is skipped while the feed is unchanged, which is exactly the
    quiet stretch that triggers deactivation."""
    names = {s.get("name") for s in workflow["jobs"]["generate"]["steps"]}
    assert "Keep scheduled workflow alive" not in names


def _repo(tmp_path: Path, days_ago: int) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    stamp = f"{int(time.time()) - days_ago * 86400} +0000"
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
        "GIT_AUTHOR_DATE": stamp,
        "GIT_COMMITTER_DATE": stamp,
    }
    for cmd in (["git", "init", "-q"], ["git", "commit", "-q", "--allow-empty", "-m", "seed"]):
        subprocess.run(cmd, cwd=repo, check=True, capture_output=True, env=env)
    return repo


def _run_keepalive(
    workflow, tmp_path: Path, days_ago: int
) -> tuple[subprocess.CompletedProcess, str]:
    repo = _repo(tmp_path, days_ago)
    log = tmp_path / "calls.log"
    log.touch()
    result = subprocess.run(
        ["bash", "-e", "-c", _step(workflow, "check", "Keep scheduled workflow alive")["run"]],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{_bin(tmp_path)}:/usr/bin:/bin",
            "HOME": str(tmp_path),
            "CALL_LOG": str(log),
            "GITHUB_REPOSITORY": "example/repo",
        },
    )
    return result, log.read_text()


def test_keepalive_noop_when_repo_is_active(workflow, tmp_path) -> None:
    result, calls = _run_keepalive(workflow, tmp_path, days_ago=10)
    assert result.returncode == 0, result.stderr
    assert "no keepalive needed" in result.stdout
    assert calls == ""


def test_keepalive_reenables_through_api_before_cutoff(workflow, tmp_path) -> None:
    result, calls = _run_keepalive(workflow, tmp_path, days_ago=55)
    assert result.returncode == 0, result.stderr
    assert "gh api --method PUT repos/example/repo/actions/workflows/generate.yml/enable" in calls


def test_keepalive_fires_with_margin_before_deactivation(workflow) -> None:
    """Threshold must leave room for the 30-minute cron to land a run."""
    run = _step(workflow, "check", "Keep scheduled workflow alive")["run"]
    assert '"$AGE_DAYS" -lt 50' in run


# --- carried over from the old keepalive tests -----------------------------


def _uses(workflow: dict, prefix: str) -> str:
    steps = [s for job in workflow["jobs"].values() for s in job["steps"]]
    return next(s["uses"] for s in steps if s.get("uses", "").startswith(prefix))


def test_pages_actions_on_v5(workflow: dict) -> None:
    """The upload and deploy actions must move together: each major expects
    the artifact format of its counterpart."""
    assert _uses(workflow, "actions/upload-pages-artifact@") == "actions/upload-pages-artifact@v5"
    assert _uses(workflow, "actions/deploy-pages@") == "actions/deploy-pages@v5"


def test_generate_job_has_test_tools(workflow: dict) -> None:
    """The generate job runs the unit tests on the bare runner, not in
    Dockerfile.test, so it needs the same test-only tools: zsh and jq run
    scripts/apply-ruleset.sh in tests/unit/test_ruleset.py. The Ubuntu runner
    has jq but not zsh."""
    install = _step(workflow, "generate", "Install system dependencies")["run"]
    assert "zsh" in install.split()
