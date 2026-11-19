"""Every JavaScript action in every workflow must run natively on Node 24.

GitHub deprecated Node 20 for Actions. Majors below these target Node 20 and
are force-run on Node 24 with a warning on every run.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOWS = sorted((Path(__file__).resolve().parents[2] / ".github" / "workflows").glob("*.yml"))

# First major of each action that targets Node 24.
NODE24_MIN_MAJOR = {
    "actions/checkout": 5,
    "actions/setup-python": 6,
    "actions/upload-pages-artifact": 5,
    "actions/deploy-pages": 5,
}


def _uses() -> list[str]:
    return [
        step["uses"]
        for path in WORKFLOWS
        for job in yaml.safe_load(path.read_text(encoding="utf-8"))["jobs"].values()
        for step in job["steps"]
        if "uses" in step
    ]


def test_every_action_is_known() -> None:
    """A new action must be added to NODE24_MIN_MAJOR, or this test is blind to it."""
    unknown = {u.split("@")[0] for u in _uses()} - NODE24_MIN_MAJOR.keys()
    assert not unknown, f"add Node 24 minimum majors for: {sorted(unknown)}"


@pytest.mark.parametrize("uses", _uses())
def test_action_targets_node24(uses: str) -> None:
    name, ref = uses.split("@")
    assert ref.startswith("v"), f"{uses}: expected a vN tag"
    major = int(ref[1:].split(".")[0])
    assert major >= NODE24_MIN_MAJOR[name], f"{uses} targets Node 20"
