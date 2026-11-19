"""Builds must be reproducible: locked Python deps and digest-pinned base images.

Without pins, `WeasyPrint>=62.0` and `python:3.12-slim` resolve to whatever is
newest on the day of the build, so a scheduled run can break with no change in
this repository.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LOCKS = ["requirements.lock", "requirements-dev.lock"]
DOCKERFILES = ["Dockerfile", "Dockerfile.test"]
BASE_IMAGE = re.compile(r"^FROM python:\d+\.\d+\.\d+-slim-[a-z]+@sha256:[0-9a-f]{64}$", re.M)


def _requirements(lock: Path) -> list[str]:
    """Requirement lines, with hash continuation lines folded in."""
    text = lock.read_text(encoding="utf-8").replace("\\\n", " ")
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "--"))
    ]


@pytest.mark.parametrize("name", LOCKS)
def test_lock_pins_every_package_with_hashes(name: str) -> None:
    lock = ROOT / name
    assert lock.exists(), f"{name} missing"
    reqs = _requirements(lock)
    assert reqs, f"{name} has no requirements"
    for req in reqs:
        assert "==" in req, f"{name}: not pinned: {req[:80]}"
        assert "--hash=sha256:" in req, f"{name}: no hash: {req[:80]}"


def test_dev_lock_has_test_and_lint_tools() -> None:
    names = {r.split("==")[0].lower() for r in _requirements(ROOT / "requirements-dev.lock")}
    assert {"pytest", "ruff", "mypy", "weasyprint"} <= names


@pytest.mark.parametrize("name", DOCKERFILES)
def test_base_image_pinned_by_digest(name: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    assert BASE_IMAGE.search(text), f"{name}: base image needs an exact tag and @sha256 digest"


def test_dockerfiles_share_base_image() -> None:
    froms = {
        next(line for line in (ROOT / n).read_text().splitlines() if line.startswith("FROM"))
        for n in DOCKERFILES
    }
    assert len(froms) == 1, froms


@pytest.mark.parametrize(
    ("name", "lock"),
    [("Dockerfile", "requirements.lock"), ("Dockerfile.test", "requirements-dev.lock")],
)
def test_dockerfile_installs_from_lock(name: str, lock: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    assert f"--require-hashes -r {lock}" in text
    assert "--no-deps" in text, "the project install must not re-resolve dependencies"


def test_workflow_installs_from_lock() -> None:
    wf = yaml.safe_load((ROOT / ".github/workflows/generate.yml").read_text(encoding="utf-8"))
    runs = "\n".join(s.get("run", "") for s in wf["jobs"]["generate"]["steps"])
    assert "--require-hashes -r requirements-dev.lock" in runs
    assert 'pip install ".[test]"' not in runs


def test_dependabot_tracks_pins() -> None:
    cfg = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text(encoding="utf-8"))
    ecosystems = {u["package-ecosystem"] for u in cfg["updates"]}
    assert {"docker", "github-actions"} <= ecosystems
