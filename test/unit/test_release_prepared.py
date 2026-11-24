# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[2] / "pipeline" / "verify-release-prepared.py"
spec = importlib.util.spec_from_file_location("verify_release_prepared", MODULE_PATH)
assert spec is not None and spec.loader is not None
prepared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepared)

TAG = "0.15.22"
COMMIT = "a" * 40
URL = "https://github.com/aws-deadline/deadline-cloud-for-maya/actions/runs/123"


def run(**changes):
    result = {
        "conclusion": "success",
        "headBranch": "mainline",
        "event": "push",
        "headSha": COMMIT,
        "displayTitle": "Release: Prepare chore(release): 0.15.22",
        "url": URL,
    }
    result.update(changes)
    return result


def test_accepts_successful_push_for_tag_commit():
    assert prepared.find_prepared_run([run()], TAG, COMMIT) == URL


def test_accepts_tag_dispatch_even_when_mainline_has_advanced():
    dispatched = run(
        event="workflow_dispatch", headSha="b" * 40, displayTitle=f"Release: Prepare {TAG}"
    )
    assert prepared.find_prepared_run([dispatched], TAG, COMMIT) == URL


@pytest.mark.parametrize(
    "changes",
    [
        {"conclusion": "failure"},
        {"conclusion": "cancelled"},
        {"headBranch": "feature-test"},
        {"headSha": "b" * 40},
        {"event": "pull_request"},
        {"url": ""},
        {"event": "workflow_dispatch", "displayTitle": "Release: Prepare 0.15.21"},
        {"headSha": "b" * 40, "displayTitle": f"Release: Prepare {TAG}"},
    ],
)
def test_rejects_runs_that_do_not_prove_preparation(changes):
    assert prepared.find_prepared_run([run(**changes)], TAG, COMMIT) is None


def test_skips_failed_run_and_finds_successful_retry():
    assert prepared.find_prepared_run([run(conclusion="failure"), run()], TAG, COMMIT) == URL
