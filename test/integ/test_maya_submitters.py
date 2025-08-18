# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import dataclasses

import yaml
import os
import pytest
import sys

from pathlib import Path
from typing import Any
from qtpy import QtWidgets

from .helpers.test_runners import is_valid_template
from .helpers.output_comparison import are_asset_references_similar, are_parameter_values_similar

import maya.standalone
import maya.cmds as cmds


@pytest.fixture(scope="session", autouse=True)
def initialize_maya():
    """
    Fixture that ensures Maya is open and close after the test runs.
    """
    maya.standalone.initialize()
    print(f"MayaClient: Maya Version {maya.cmds.about(version=True)}")

    # Need to import here since it need maya to be initialize first to not throw an error
    from deadline.maya_submitter.maya_render_submitter import (
        show_maya_render_submitter,
        on_create_job_bundle_callback,
    )

    qt_application = QtWidgets.QApplication(sys.argv)
    yield show_maya_render_submitter, on_create_job_bundle_callback

    qt_application.shutdown()
    maya.standalone.uninitialize()


@pytest.mark.submitter
@pytest.mark.usefixtures("initialize_maya")
class TestSubmitters:
    """
    Tests that ensure submitters produce the correct job bundle given a scene file.
    """

    @dataclasses.dataclass
    class JobConfiguration:
        name: str
        asset_folder: str
        frame_list: str
        file_prefix: str

    def _cleanup_sticky_settings(self, scene_file: Path, script_location: Path):
        """
        We need to clean the sticky settings before the test runs so that we can ensure
        a clean environment.
        """

        sticky_settings_location = scene_file.with_name(
            f"{scene_file.stem}.deadline_render_settings.json"
        )
        Path(script_location / sticky_settings_location).unlink(missing_ok=True)

    @pytest.mark.parametrize(
        "job_configuration",
        [
            JobConfiguration(
                name="Minimal Maya Test",
                asset_folder="minimal_test",
                frame_list="1-2",
                file_prefix="rs_<RenderLayer>_<Camera>",
            ),
            JobConfiguration(
                name="Redshift Test",
                asset_folder="redshift_test",
                frame_list="1",
                file_prefix="redshift_test",
            ),
        ],
        ids=["Minimal Maya Test", "Redshift Test"],
    )
    def test_scene_submitter(
        self,
        initialize_maya,
        script_location: Path,
        tmp_path: Path,
        job_configuration: JobConfiguration,
    ) -> None:
        # Get submitters
        show_maya_render_submitter = initialize_maya[0]
        on_create_job_bundle_callback = initialize_maya[1]

        job_history_dir = tmp_path / "jobhistory"
        output_path = tmp_path / "output"
        project_path = script_location / job_configuration.asset_folder / "scene"
        scene_location = script_location / job_configuration.asset_folder / "scene" / "test.ma"

        # Clean up sticky setting
        self._cleanup_sticky_settings(scene_location, script_location)

        os.makedirs(job_history_dir, exist_ok=True)
        os.makedirs(output_path, exist_ok=True)

        cmds.workspace(project_path, openWorkspace=True)
        cmds.workspace(fileRule=["images", output_path])

        cmds.file(scene_location, open=True, force=True)

        cmds.setAttr("defaultResolution.width", 960)  # Set width
        cmds.setAttr("defaultResolution.height", 540)  # Set height

        # Set the render output directory
        cmds.setAttr(
            "defaultRenderGlobals.imageFilePrefix", job_configuration.file_prefix, type="string"
        )
        cmds.optionVar(iv=("renderSetup_includeAllLights", 0))

        widget = show_maya_render_submitter(None)

        settings = widget.job_settings_type()
        widget.shared_job_settings.update_settings(settings)
        widget.job_settings.update_settings(settings)

        settings.view_layer_selection = "All Renderable Layers"
        settings.camera_selection = "All Renderable Cameras"
        settings.description = ""
        settings.include_adaptor_wheels = False
        settings.override_frame_range = True
        settings.frame_list = job_configuration.frame_list

        widget.shared_job_settings.shared_job_properties_box.set_parameter_value(
            {"name": "deadline:targetTaskRunStatus", "value": "READY"}
        )
        widget.shared_job_settings.shared_job_properties_box.set_parameter_value(
            {"name": "deadline:maxFailedTasksCount", "value": 20}
        )
        widget.shared_job_settings.shared_job_properties_box.set_parameter_value(
            {"name": "deadline:maxRetriesPerTask", "value": 5}
        )
        widget.shared_job_settings.shared_job_properties_box.set_parameter_value(
            {"name": "deadline:priority", "value": 50}
        )

        on_create_job_bundle_callback(
            widget,
            job_history_dir,
            settings,
            widget.shared_job_settings.get_parameters(),
            widget.job_attachments.get_asset_references(),
            widget.host_requirements.get_requirements(),
            purpose="export",
        )
        widget.close()

        # Check that we have a valid template
        assert is_valid_template(job_history_dir / "template.yaml")

        # Check that the template is as expected.
        with (
            open(
                script_location
                / job_configuration.asset_folder
                / "expected_job_bundle"
                / "template.yaml"
            ) as expected,
            open(job_history_dir / "template.yaml") as actual,
        ):
            assert yaml.safe_load(expected) == yaml.safe_load(actual)

        # Check that the parameter values are as expected.
        expected_parameter_values = {
            "parameterValues": [
                {"name": "MayaSceneFile", "value": str(scene_location)},
                {"name": "OutputFilePrefix", "value": str(job_configuration.file_prefix)},
                {"name": "Frames", "value": job_configuration.frame_list},
                {"name": "ImageWidth", "value": 960},
                {"name": "ImageHeight", "value": 540},
                {"name": "ProjectPath", "value": str(project_path) + "/"},
                {"name": "OutputFilePath", "value": str(output_path)},
                {"name": "RenderSetupIncludeLights", "value": "false"},
                {"name": "deadline:targetTaskRunStatus", "value": "READY"},
                {"name": "deadline:maxFailedTasksCount", "value": 20},
                {"name": "deadline:maxRetriesPerTask", "value": 5},
                {"name": "deadline:priority", "value": 50},
            ]
        }

        are_parameter_values_similar(job_history_dir, expected_parameter_values)

        # Check that the asset references are as expected.
        expected_asset_references: dict[str, dict[str, Any]] = {
            "assetReferences": {
                "inputs": {
                    "directories": [],
                    "filenames": {str(scene_location)},
                },
                "outputs": {
                    "directories": [str(output_path)],
                },
                "referencedPaths": [],
            }
        }

        are_asset_references_similar(job_history_dir, expected_asset_references)
