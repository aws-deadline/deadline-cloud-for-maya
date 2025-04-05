# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from pathlib import Path

import pytest
from flaky import flaky

from .helpers.image_comparison import are_images_similar
from .helpers.test_runners import run_adaptor_test


@pytest.mark.adaptor
@flaky(max_runs=3, min_passes=1)
class TestAdaptors:
    """
    Tests that ensure correct output from the Maya adaptor given a job bundle and scene file.
    """

    def test_minimal_scene_adaptor(self, script_location: Path, tmp_path: Path) -> None:
        test_file_location = script_location / "minimal_test"
        scene_location = test_file_location / "scene" / "test.ma"
        output_path = tmp_path / "output"

        job_params = {
            "MayaSceneFile": str(scene_location),
            "OutputFilePrefix": "rs_<RenderLayer>_<Camera>",
            "Frames": "1-2",
            "ImageWidth": 960,
            "ImageHeight": 540,
            "OutputFilePath": str(output_path),
            "ProjectPath": str(test_file_location / "scene") + "/",
            "RenderSetupIncludeLights": "false",
        }

        run_adaptor_test(test_file_location / "expected_job_bundle" / "template.yaml", job_params)
        are_images_similar(
            expected_image_directory=test_file_location / "expected_images",
            actual_image_directory=output_path,
            tolerance=2,
        )
