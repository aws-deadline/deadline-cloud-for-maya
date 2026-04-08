# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from pathlib import Path

import pytest
from flaky import flaky

from .helpers.output_comparison import are_images_similar
from .helpers.test_runners import run_adaptor_test

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
    def test_token_resolution_adaptor(self, script_location: Path, tmp_path: Path) -> None:
        """Tests that <Scene> and <RenderLayer> tokens in OutputFilePrefix are resolved
        to actual values in the rendered output file paths."""
        test_file_location = script_location / "minimal_test"
        scene_location = test_file_location / TEST_SCENE_FOLDER / "test.ma"
        output_path = tmp_path / OUTPUT_FOLDER

        job_params: dict = {
            "MayaSceneFile": str(scene_location),
            "OutputFilePrefix": "<Scene>/<RenderLayer>/<RenderLayer>",
            "Frames": "1",
            "ImageWidth": 960,
            "ImageHeight": 540,
            "OutputFilePath": str(output_path),
            "ProjectPath": str(test_file_location / "scene") + "/",
            "RenderSetupIncludeLights": "false",
        }

        run_adaptor_test(test_file_location / EXPECTED_JOB_BUNDLE_FOLDER / TEMPLATE, job_params)

        # Verify tokens were resolved: output should be under {scene_name}/{layer_name}/
        # and NOT contain literal "<Scene>" or "<RenderLayer>" in file paths
        output_files: list[Path] = list(output_path.rglob("*"))
        rendered_files: list[Path] = [f for f in output_files if f.is_file()]
        assert len(rendered_files) > 0, "No rendered files found"
        for rendered_file in rendered_files:
            relative: str = str(rendered_file.relative_to(output_path))
            assert "<Scene>" not in relative, f"Unresolved <Scene> token in: {relative}"
            assert "<RenderLayer>" not in relative, f"Unresolved <RenderLayer> token in: {relative}"

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
