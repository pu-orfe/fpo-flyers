"""The Pages deploy must not race the artifact upload.

deploy-pages looks up the "github-pages" artifact through the API. Called in
the same job, milliseconds after upload-pages-artifact finalizes, the lookup
sometimes finds nothing ("No artifacts named github-pages were found") and the
run fails. It happened with deploy-pages v4 and again with v5. GitHub's Pages
starter workflow deploys from a separate job, and the deploy is retried once.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "generate.yml"


@pytest.fixture(scope="module")
def jobs() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]


def _uses(job: dict, prefix: str) -> list[dict]:
    return [s for s in job["steps"] if s.get("uses", "").startswith(prefix)]


def test_upload_and_deploy_in_separate_jobs(jobs: dict) -> None:
    assert _uses(jobs["generate"], "actions/upload-pages-artifact@")
    assert not _uses(jobs["generate"], "actions/deploy-pages@")
    assert _uses(jobs["deploy"], "actions/deploy-pages@")


def test_deploy_waits_for_generate(jobs: dict) -> None:
    deploy = jobs["deploy"]
    assert deploy["needs"] == "generate"
    # generate runs under always(); deploy must still require its success.
    assert "needs.generate.result == 'success'" in deploy["if"]


def test_deploy_uses_pages_environment(jobs: dict) -> None:
    env = jobs["deploy"]["environment"]
    assert env["name"] == "github-pages"
    assert env["url"] == "${{ steps.deploy.outputs.page_url || steps.retry.outputs.page_url }}"


def test_deploy_retried_once_and_second_failure_fails(jobs: dict) -> None:
    steps = _uses(jobs["deploy"], "actions/deploy-pages@")
    assert len(steps) == 2
    first, retry = steps
    assert first["id"] == "deploy" and first.get("continue-on-error") is True
    assert retry["id"] == "retry"
    assert retry["if"] == "steps.deploy.outcome == 'failure'"
    # The retry must be allowed to fail the job: silence is not success.
    assert "continue-on-error" not in retry


def test_deploy_job_has_only_pages_permissions(jobs: dict) -> None:
    assert jobs["deploy"]["permissions"] == {"pages": "write", "id-token": "write"}
