# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).parents[2] / ".github" / "workflows"


def workflow(name):
    # BaseLoader preserves the GitHub Actions "on" key rather than treating it as a boolean.
    return yaml.load((WORKFLOWS / name).read_text(), Loader=yaml.BaseLoader)


@pytest.mark.parametrize("platform", ["linux", "windows"])
def test_gui_workflows_test_release_tags_and_run_on_mainline(platform):
    data = workflow(f"integ_gui_{platform}.yml")
    assert "mainline" in data["on"]["push"]["branches"]
    assert data["on"]["workflow_call"]["inputs"]["tag"]["required"] == "true"
    gui = data["jobs"][f"GuiTests{platform.title()}"]
    assert "refs/heads/mainline" in gui["if"]
    assert gui["concurrency"]["group"] == "maya-gui-tests"
    assert gui["concurrency"]["queue"] == "max"
    assert gui["concurrency"].get("cancel-in-progress", "false") == "false"
    for job in data["jobs"].values():
        for step in job["steps"]:
            if step.get("name") == "Checkout":
                assert "refs/tags/{0}" in step["with"]["ref"]
                assert "inputs.tag" in step["with"]["ref"]


def test_prepare_cannot_stage_installers_before_all_release_tests_pass():
    jobs = workflow("release_prepare.yml")["jobs"]
    gates = {"UnitTests", "IntegrationTests", "GuiTestsLinux", "GuiTestsWindows"}
    assert gates <= set(jobs["BuildInstaller"]["needs"])
    assert "BuildInstaller" in jobs["PublishToCodeArtifact"]["needs"]
    expected_tag = "${{ needs.TagRelease.outputs.tag }}"
    for name in gates:
        assert jobs[name]["with"]["tag"] == expected_tag
    assert not any("pypi-publish" in job.get("uses", "") for job in jobs.values())
    assert "Release" not in jobs


def test_publish_requires_conda_and_preparation_evidence():
    data = workflow("release_publish.yml")
    assert "push" not in data["on"]
    assert data["on"]["schedule"]
    jobs = data["jobs"]
    assert "IsCondaReady" not in jobs
    check = next(step for step in jobs["CheckConda"]["steps"] if step.get("id") == "readiness")
    assert check["with"]["package-name"] == "maya-openjd"
    assert check["with"]["required-platforms"] == "linux-64"
    assert check["with"]["timeout-days"] == "10"
    assert "VerifyPrepared" in jobs["AuthorizePublish"]["needs"]
    assert "needs.VerifyPrepared.result == 'success'" in jobs["AuthorizePublish"]["if"]
    assert "refs/heads/mainline" in jobs["CheckConda"]["if"]
    assert data["concurrency"]["group"] != workflow("release_prepare.yml")["concurrency"]["group"]


def test_weekly_bump_skips_when_no_new_release_is_needed():
    data = workflow("release_bump.yml")
    assert data["on"]["schedule"][0]["cron"] == "0 14 * * 1"
    assert "refs/heads/mainline" in data["jobs"]["CheckForBump"]["if"]
    assert "needs.CheckForBump.outputs.should_bump == 'true'" in data["jobs"]["Bump"]["if"]
