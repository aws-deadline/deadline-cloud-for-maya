# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Drive the Maya submitter in GUI Maya, against the mock Deadline Cloud service.

Each test opens a scene from job_bundle_output_tests/ in Maya, opens the
submitter the way the shelf button does, and works the dialog through the
accessibility tree. Exported bundles compare against that folder's expected
bundles, which job_bundle_output_test_runner.py generated in GUI Maya.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
import yaml
from deadline_test_fixtures.job_bundle import find_complete_job_bundle

from ._bundles import (
    assert_bundles_equal,
    copy_case_scene,
    expected_bundle,
    normalize_bundle,
)

# renderman needs RenderMan for Maya, which the runner doesn't install.
EXPORT_CASES = ["cube", "layers", "layers_no_variation", "referenced_layers"]
CREATE_JOB_TIMEOUT = 120.0


def _assert_no_unmatched_requests(backend) -> None:
    assert (
        backend.unmatched_requests == []
    ), f"The submitter called routes the mock doesn't serve: {backend.unmatched_requests}"


def _exported_bundle(export_dir: Path) -> Path:
    bundle = find_complete_job_bundle(export_dir)
    assert bundle is not None, f"No complete job bundle under {export_dir}"
    return bundle


@pytest.mark.parametrize("case", EXPORT_CASES)
def test_export_bundle_matches_expected(open_submitter, tmp_path, case):
    scene_dir = tmp_path / "scene"
    scene_file = copy_case_scene(case, scene_dir)

    submitter = open_submitter(scene_file)
    submitter.dialog.export_bundle()

    actual = normalize_bundle(_exported_bundle(submitter.export_dir), scene_dir)
    assert_bundles_equal(expected_bundle(case), actual)
    _assert_no_unmatched_requests(submitter.backend)


def test_frame_range_override_reaches_bundle(open_submitter, tmp_path):
    scene_dir = tmp_path / "scene"
    scene_file = copy_case_scene("cube", scene_dir)

    submitter = open_submitter(scene_file)
    submitter.dialog.override_frame_range("1-3")
    submitter.dialog.export_bundle()

    actual = normalize_bundle(_exported_bundle(submitter.export_dir), scene_dir)
    expected = expected_bundle("cube")
    # Only the Frames value differs from the scene's own frame range.
    parameters = json.loads(expected["parameter_values.yaml"])
    for parameter in parameters["parameterValues"]:
        if parameter["name"] == "Frames":
            parameter["value"] = "1-3"
    assert json.loads(actual["parameter_values.yaml"]) == parameters
    assert actual["template.yaml"] == expected["template.yaml"]


def test_submit_creates_job(open_submitter, tmp_path):
    scene_dir = tmp_path / "scene"
    scene_file = copy_case_scene("cube", scene_dir)

    submitter = open_submitter(scene_file)
    submitter.dialog.submit()

    deadline = time.monotonic() + CREATE_JOB_TIMEOUT
    jobs: list = []
    while time.monotonic() < deadline and not jobs:
        jobs = submitter.backend.resources["jobs"]
        time.sleep(1.0)
    assert len(jobs) == 1, f"Expected one job within {CREATE_JOB_TIMEOUT:.0f}s, got {len(jobs)}"
    (job,) = jobs
    assert job["lifecycleStatus"] == "CREATE_COMPLETE"
    expected_template = yaml.safe_load(expected_bundle("cube")["template.yaml"])
    assert yaml.safe_load(job["template"]) == expected_template
    _assert_no_unmatched_requests(submitter.backend)
