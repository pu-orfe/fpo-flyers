"""main must only move when CI passes, and the ruleset that enforces it lives in the repo.

.github/rulesets/main.json is the source of truth; scripts/apply-ruleset.sh
creates or updates it through the GitHub API. The script tests run it against
a stub `gh` on PATH, so they check real behavior without touching GitHub.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
RULESET = ROOT / ".github" / "rulesets" / "main.json"
SCRIPT = ROOT / "scripts" / "apply-ruleset.sh"
CI = ROOT / ".github" / "workflows" / "ci.yml"
GITHUB_ACTIONS_APP_ID = 15368


@pytest.fixture(scope="module")
def ruleset() -> dict:
    return json.loads(RULESET.read_text(encoding="utf-8"))


def _rule(ruleset: dict, rule_type: str) -> dict:
    matches = [r for r in ruleset["rules"] if r["type"] == rule_type]
    assert matches, f"no {rule_type} rule"
    return matches[0]


# --- the ruleset ------------------------------------------------------------


def test_targets_default_branch_and_is_active(ruleset: dict) -> None:
    assert ruleset["target"] == "branch"
    assert ruleset["enforcement"] == "active"
    assert ruleset["conditions"]["ref_name"]["include"] == ["~DEFAULT_BRANCH"]


def test_requires_every_ci_job(ruleset: dict) -> None:
    """Adding a CI job without requiring it would let it fail silently."""
    ci_jobs = set(yaml.safe_load(CI.read_text(encoding="utf-8"))["jobs"])
    checks = _rule(ruleset, "required_status_checks")["parameters"]["required_status_checks"]
    assert {c["context"] for c in checks} == ci_jobs
    # Pin to the GitHub Actions app so another app cannot satisfy the check.
    assert all(c["integration_id"] == GITHUB_ACTIONS_APP_ID for c in checks)


def test_blocks_force_push_and_deletion(ruleset: dict) -> None:
    _rule(ruleset, "non_fast_forward")
    _rule(ruleset, "deletion")


def test_nothing_bypasses(ruleset: dict) -> None:
    """generate.yml no longer pushes to main, so nothing needs an exemption.
    (GitHub also rejects the built-in GitHub Actions app as a bypass actor.)"""
    assert ruleset["bypass_actors"] == []


# --- the apply script -------------------------------------------------------


def test_script_is_strict_and_executable() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env zsh\n")
    assert "set -euo pipefail" in text
    assert os.access(SCRIPT, os.X_OK)


STUB = """#!/bin/sh
# Stub gh: log every call; answer the two reads the script makes.
echo "$*" >> "$GH_LOG"
case "$*" in
  "repo view"*) echo "example/repo" ;;
  "api repos/example/repo/rulesets --jq"*) [ -n "$EXISTING_ID" ] && echo "$EXISTING_ID" ;;
  *"--method"*) echo "applied" ;;
esac
exit 0
"""


def _run(
    tmp_path: Path, *args: str, existing_id: str = ""
) -> tuple[subprocess.CompletedProcess, list[str]]:
    zsh = shutil.which("zsh")
    assert zsh, "zsh is required to test the apply script"
    jq = shutil.which("jq")
    assert jq, "jq is required by the apply script"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(STUB, encoding="utf-8")
    gh.chmod(0o755)
    (bin_dir / "jq").symlink_to(jq)
    log = tmp_path / "gh.log"
    log.touch()
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "GH_LOG": str(log),
        "EXISTING_ID": existing_id,
        "HOME": str(tmp_path),
    }
    result = subprocess.run(
        [zsh, str(SCRIPT), *args], capture_output=True, text=True, env=env, check=False
    )
    return result, log.read_text(encoding="utf-8").splitlines()


def _writes(calls: list[str]) -> list[str]:
    return [c for c in calls if "--method" in c]


def test_dry_run_never_writes(tmp_path: Path) -> None:
    result, calls = _run(tmp_path, "--dry-run")
    assert result.returncode == 0, result.stderr
    assert "[dry-run] would POST repos/example/repo/rulesets" in result.stdout
    assert not _writes(calls)


def test_creates_when_absent(tmp_path: Path) -> None:
    result, calls = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    writes = _writes(calls)
    assert len(writes) == 1
    assert writes[0].startswith("api --method POST repos/example/repo/rulesets --input ")


def test_updates_when_present(tmp_path: Path) -> None:
    """Safe to re-run: an existing ruleset with the same name is replaced, not duplicated."""
    result, calls = _run(tmp_path, existing_id="42")
    assert result.returncode == 0, result.stderr
    writes = _writes(calls)
    assert len(writes) == 1
    assert writes[0].startswith("api --method PUT repos/example/repo/rulesets/42 --input ")


def test_rejects_unknown_arguments(tmp_path: Path) -> None:
    result, calls = _run(tmp_path, "--force")
    assert result.returncode == 2
    assert "unknown argument" in result.stderr
    assert not _writes(calls)
