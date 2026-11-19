"""ci.yml must gate every PR and push to main on lint, types, lock freshness, and tests.

Before it existed, PRs were checked only by CodeQL; tests ran only inside the
scheduled flyer build, after a merge.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

CI = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"


@pytest.fixture(scope="module")
def ci() -> dict:
    assert CI.exists(), "ci.yml missing"
    return yaml.safe_load(CI.read_text(encoding="utf-8"))


def _runs(ci: dict) -> str:
    return "\n".join(s.get("run", "") for job in ci["jobs"].values() for s in job["steps"])


def test_triggers_on_pull_requests_and_main(ci: dict) -> None:
    # PyYAML reads the bare key `on` as True.
    on = ci.get("on", ci.get(True))
    assert "pull_request" in on
    assert on["push"]["branches"] == ["main"]


def test_read_only_token(ci: dict) -> None:
    assert ci["permissions"] == {"contents": "read"}


@pytest.mark.parametrize(
    "command",
    [
        "ruff check src tests",
        "ruff format --check src tests",
        "mypy",
        "pip install --require-hashes -r requirements-dev.lock",
    ],
)
def test_lint_and_type_checks(ci: dict, command: str) -> None:
    assert command in _runs(ci)


def test_lockfiles_checked_against_pyproject(ci: dict) -> None:
    runs = _runs(ci)
    assert "uv pip compile" in runs
    assert "git diff --exit-code requirements.lock requirements-dev.lock" in runs


def test_tests_run_in_container(ci: dict) -> None:
    runs = _runs(ci)
    assert "-f Dockerfile.test" in runs
    assert "tests/unit/" in runs


def test_production_image_builds(ci: dict) -> None:
    assert "docker build -f Dockerfile " in _runs(ci)
