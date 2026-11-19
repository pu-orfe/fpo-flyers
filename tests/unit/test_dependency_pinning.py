"""Builds must be reproducible, and Dependabot must be able to keep the pins current.

Without pins, `WeasyPrint>=62.0` and `python:3.12-slim` resolve to whatever is
newest on the day of the build, so a scheduled run can break with no change in
this repository. The pins live in uv.lock because Dependabot's uv updater can
regenerate it, hashes included; it could not update uv-exported requirements
files.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILES = ["Dockerfile", "Dockerfile.test"]
PINNED_FROM = re.compile(r"^FROM \S+:\d+\.\d+\.\d+[^@\s]*@sha256:[0-9a-f]{64}( AS \w+)?$")
WORKFLOWS = ["generate.yml", "ci.yml"]


def _lock() -> dict:
    return tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))


def _workflow(name: str) -> dict:
    return yaml.safe_load((ROOT / ".github/workflows" / name).read_text(encoding="utf-8"))


def _runs(name: str) -> str:
    wf = _workflow(name)
    return "\n".join(s.get("run", "") for job in wf["jobs"].values() for s in job["steps"])


def _from_lines(name: str) -> list[str]:
    lines = (ROOT / name).read_text(encoding="utf-8").splitlines()
    return [line for line in lines if line.startswith("FROM ")]


# --- the lock ---------------------------------------------------------------


def test_requirements_exports_are_gone() -> None:
    """One source of truth: Dependabot updates uv.lock and nothing else."""
    for stale in ["requirements.lock", "requirements-dev.lock", "requirements-build.in"]:
        assert not (ROOT / stale).exists(), f"{stale} would drift from uv.lock"


def test_lock_pins_every_registry_package_with_hashes() -> None:
    packages = [p for p in _lock()["package"] if p["source"].get("registry")]
    assert packages
    for pkg in packages:
        artifacts = pkg.get("wheels", []) + ([pkg["sdist"]] if "sdist" in pkg else [])
        assert artifacts, f"{pkg['name']}: no artifacts"
        assert all(a.get("hash", "").startswith("sha256:") for a in artifacts), pkg["name"]


def test_lock_covers_runtime_test_and_lint_tools() -> None:
    names = {p["name"] for p in _lock()["package"]}
    assert {"weasyprint", "pytest", "ruff", "mypy"} <= names


def test_build_backend_pinned() -> None:
    """uv.lock does not cover the build backend, so constrain it exactly."""
    uv = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["uv"]
    pins = uv["build-constraint-dependencies"]
    assert {p.split("==")[0] for p in pins} == {"setuptools", "setuptools-scm"}
    assert all("==" in p for p in pins)


# --- images -----------------------------------------------------------------


@pytest.mark.parametrize("name", DOCKERFILES)
def test_every_image_pinned_by_tag_and_digest(name: str) -> None:
    froms = _from_lines(name)
    assert froms
    for line in froms:
        assert PINNED_FROM.match(line), f"{name}: {line}"


def test_dockerfiles_share_images() -> None:
    assert _from_lines("Dockerfile") == _from_lines("Dockerfile.test")


@pytest.mark.parametrize("name", DOCKERFILES)
def test_dockerfile_installs_from_lock(name: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    assert "COPY --from=uv " in text
    assert "uv sync --locked" in text
    assert "pip install" not in text, "pip would bypass uv.lock"


# --- workflows --------------------------------------------------------------


@pytest.mark.parametrize("name", WORKFLOWS)
def test_workflow_installs_from_lock(name: str) -> None:
    runs = _runs(name)
    assert "uv sync --locked" in runs
    assert "pip install" not in runs, "pip would bypass uv.lock"


@pytest.mark.parametrize("name", WORKFLOWS)
def test_workflow_pins_uv_version(name: str) -> None:
    steps = [s for job in _workflow(name)["jobs"].values() for s in job["steps"]]
    setups = [s for s in steps if s.get("uses", "").startswith("astral-sh/setup-uv@")]
    assert setups, f"{name}: no setup-uv step"
    for s in setups:
        assert re.fullmatch(r"\d+\.\d+\.\d+", s["with"]["version"]), s


# --- dependabot -------------------------------------------------------------


def _dependabot() -> dict:
    return yaml.safe_load((ROOT / ".github/dependabot.yml").read_text(encoding="utf-8"))


def test_dependabot_tracks_every_pin() -> None:
    ecosystems = {u["package-ecosystem"] for u in _dependabot()["updates"]}
    assert {"uv", "docker", "github-actions"} <= ecosystems


def test_dependabot_keeps_python_minor() -> None:
    """Moving to a new Python minor (3.12 -> 3.15) also needs the workflow's
    python-version, so it must be a deliberate change. Dependabot should only
    propose 3.12.x patches and digest refreshes."""
    docker = next(u for u in _dependabot()["updates"] if u["package-ecosystem"] == "docker")
    ignored = {
        t
        for rule in docker.get("ignore", [])
        if rule.get("dependency-name") == "python"
        for t in rule.get("update-types", [])
    }
    assert {"version-update:semver-major", "version-update:semver-minor"} <= ignored
