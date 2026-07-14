# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from pathlib import Path

import pytest
import yaml
from flaky import flaky

from .helpers.output_comparison import are_images_similar
from .helpers.test_runners import run_adaptor_test, run_command

from test.integ.test_const import (
    TEMPLATE,
    TEST_SCENE_FOLDER,
    OUTPUT_FOLDER,
    EXPECTED_JOB_BUNDLE_FOLDER,
    EXPECTED_OUTPUT_FOLDER,
)


@pytest.mark.adaptor
@flaky(max_runs=3, min_passes=1)
class TestAdaptors:
    """
    Tests that ensure correct output from the Maya adaptor given a job bundle and scene file.
    """

    @pytest.mark.maya_renderer
    def test_minimal_scene_adaptor(self, script_location: Path, tmp_path: Path) -> None:
        test_file_location = script_location / "minimal_test"
        scene_location = test_file_location / TEST_SCENE_FOLDER / "test.ma"
        output_path = tmp_path / OUTPUT_FOLDER

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

        run_adaptor_test(test_file_location / EXPECTED_JOB_BUNDLE_FOLDER / TEMPLATE, job_params)
        are_images_similar(
            expected_image_directory=test_file_location / EXPECTED_OUTPUT_FOLDER,
            actual_image_directory=output_path,
            tolerance=2,
        )

    @pytest.mark.redshift_renderer
    def test_redshift_scene_adaptor(self, script_location: Path, tmp_path: Path) -> None:
        test_file_location = script_location / "redshift_test"
        scene_location = test_file_location / TEST_SCENE_FOLDER / "test.ma"
        output_path = tmp_path / OUTPUT_FOLDER

        job_params = {
            "MayaSceneFile": str(scene_location),
            "OutputFilePrefix": "redshift_test",
            "Frames": "1",
            "ImageWidth": 960,
            "ImageHeight": 540,
            "OutputFilePath": str(output_path),
            "ProjectPath": str(test_file_location / "scene") + "/",
            "RenderSetupIncludeLights": "false",
        }

        run_adaptor_test(test_file_location / EXPECTED_JOB_BUNDLE_FOLDER / TEMPLATE, job_params)
        are_images_similar(
            expected_image_directory=test_file_location / EXPECTED_OUTPUT_FOLDER,
            actual_image_directory=output_path,
            tolerance=2,
        )

    @pytest.mark.mtoa_renderer
    def test_mtoa_scene_adaptor(self, script_location: Path, tmp_path: Path) -> None:
        test_file_location = script_location / "mtoa_test"
        scene_location = test_file_location / TEST_SCENE_FOLDER / "test.ma"
        output_path = tmp_path / OUTPUT_FOLDER

        job_params = {
            "MayaSceneFile": str(scene_location),
            "OutputFilePrefix": "arnoldmayascene",
            "Frames": "1",
            "ImageWidth": 960,
            "ImageHeight": 540,
            "OutputFilePath": str(output_path),
            "ProjectPath": str(test_file_location / "scene") + "/",
            "RenderSetupIncludeLights": "false",
            "ArnoldErrorOnLicenseFailure": "false",
        }

        run_adaptor_test(test_file_location / EXPECTED_JOB_BUNDLE_FOLDER / TEMPLATE, job_params)
        are_images_similar(
            expected_image_directory=test_file_location / EXPECTED_OUTPUT_FOLDER,
            actual_image_directory=output_path,
            tolerance=2,
        )

    @pytest.mark.vray_renderer
    def test_vray_scene_adaptor(self, script_location: Path, tmp_path: Path) -> None:
        test_file_location = script_location / "vray_test"
        scene_location = test_file_location / TEST_SCENE_FOLDER / "test.ma"
        output_path = tmp_path / OUTPUT_FOLDER

        job_params = {
            "MayaSceneFile": str(scene_location),
            "OutputFilePrefix": "vraymayascene",
            "Frames": "1",
            "ImageWidth": 960,
            "ImageHeight": 540,
            "OutputFilePath": str(output_path),
            "ProjectPath": str(test_file_location / "scene") + "/",
            "RenderSetupIncludeLights": "false",
        }

        run_adaptor_test(test_file_location / EXPECTED_JOB_BUNDLE_FOLDER / TEMPLATE, job_params)
        are_images_similar(
            expected_image_directory=test_file_location / EXPECTED_OUTPUT_FOLDER,
            actual_image_directory=output_path,
            tolerance=2,
        )


@pytest.mark.adaptor
class TestTaskRunTimeout:
    """
    Verifies that the onRun (Task Run) timeout written into the job template is
    enforced by the OpenJD session runner.
    """

    def test_task_run_timeout_is_enforced(self, script_location: Path) -> None:
        """
        Scene-free template whose onRun sleeps 60s but has a 5s timeout, so the
        task must be terminated by the timeout and the run must fail. No job
        params are required (the Frames parameter has a default) and no output
        is produced.
        """

        template_path = script_location / "test_time_out" / EXPECTED_JOB_BUNDLE_FOLDER / TEMPLATE

        with open(template_path) as f:
            template = yaml.safe_load(f)

        # Execute the step explicitly instead of through run_adaptor_test util because we want access to output
        for step in template["steps"]:
            output = run_command(
                [
                    "mayapy",
                    "-m",
                    "openjd",
                    "run",
                    str(template_path),
                    "--step",
                    step["name"],
                    "--job-param",
                    "{}",
                ]
            )

            combined = output.stdout.decode("utf-8", errors="replace") + output.stderr.decode(
                "utf-8", errors="replace"
            )

            # The run must fail
            assert output.returncode != 0, (
                "Expected the step to fail because the Task Run timeout should have "
                f"terminated it, but it succeeded with returncode {output.returncode}."
            )
            # and it must fail specifically because of the Task Run timeout
            assert "TIMEOUT" in combined, (
                "Expected the failure to be caused by the Task Run timeout, but no "
                f"timeout message was found in the output:\n{combined}"
            )
