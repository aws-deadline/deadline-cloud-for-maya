# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from dataclasses import dataclass

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

    @dataclass
    class JobConfiguration:
        name: str
        asset_folder: str
        frame_list: str
        file_prefix: str
        expected_scene_file_paths: list[str]

    def _cleanup_sticky_settings(self, scene_file: Path, script_location: Path):
        """
        We need to clean the sticky settings before the test runs so that we can ensure
        a clean environment.
        """

        sticky_settings_location = scene_file.with_name(
            f"{scene_file.stem}.deadline_render_settings.json"
        )
        Path(script_location / sticky_settings_location).unlink(missing_ok=True)

    def _get_expected_parameter_values(
        self,
        scene_location: Path,
        project_path: Path,
        output_path: Path,
        job_configuration: JobConfiguration,
    ) -> dict[str, list]:
        """
        Build expected parameter values dynamically based on renderer type.
        """
        # Base parameters common to all renderers
        base_params = [
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

        # Add renderer-specific parameters
        renderer_params = {
            "Arnold Test": [
                {"name": "ArnoldErrorOnLicenseFailure", "value": "false"},
            ]
        }

        # Combine base + renderer-specific params
        all_params = base_params + renderer_params.get(job_configuration.name, [])

        return {"parameterValues": all_params}

    @pytest.mark.parametrize(
        "job_configuration",
        [
            JobConfiguration(
                name="Minimal Maya Test",
                asset_folder="minimal_test",
                frame_list="1-2",
                file_prefix="rs_<RenderLayer>_<Camera>",
                expected_scene_file_paths=[],
            ),
            JobConfiguration(
                name="Redshift Test",
                asset_folder="redshift_test",
                frame_list="1",
                file_prefix="redshift_test",
                expected_scene_file_paths=[],
            ),
            JobConfiguration(
                name="Arnold Test",
                asset_folder="mtoa_test",
                frame_list="1",
                file_prefix="arnoldmayascene",
                expected_scene_file_paths=[],
            ),
            JobConfiguration(
                name="VRay Test",
                asset_folder="vray_test",
                frame_list="1",
                file_prefix="vraymayascene",
                expected_scene_file_paths=[],
            ),
        ],
        ids=["Minimal Maya Test", "Redshift Test", "Arnold Test", "VRay Test"],
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
        expected_parameter_values = self._get_expected_parameter_values(
            scene_location,
            project_path,
            output_path,
            job_configuration,
        )

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

        are_asset_references_similar(
            job_history_dir, expected_asset_references, job_configuration.expected_scene_file_paths
        )

    def test_scene_submitter_with_ocio_config(
        self,
        initialize_maya,
        script_location: Path,
        tmp_path: Path,
    ) -> None:
        """OCIO config file regression coverage.

        Companion to the 0.15.13 OCIO submission failure that was fixed
        in 0.15.14 (the customer-default code path was uncovered by
        existing tests).

        The four parametrized tests above implicitly cover the
        no-custom-OCIO case (scene's ``cfp`` is the default
        ``<MAYA_RESOURCES>/...`` path which ``Scene.ocio_config_file()``
        correctly returns ``None`` for, so ``OCIOConfigFile`` is omitted
        from parameter_values and falls back to its empty-string default
        in the template). That's the customer state that broke when
        ``openjd-model-for-python < 0.9.1`` rejected empty defaults on
        HIDDEN PATH parameters.

        This test covers the custom-OCIO case — scene **with** a custom
        OCIO config. We programmatically apply the config via
        ``cmds.colorManagementPrefs(e=True, configFilePath=...)``
        post-scene-open (simulating a customer with a studio-wide OCIO
        config set in Maya's preferences). The submitter must then pick
        it up via ``Scene.ocio_config_file()`` and emit it as the
        ``OCIOConfigFile`` parameter value in the bundle.
        """
        show_maya_render_submitter = initialize_maya[0]
        on_create_job_bundle_callback = initialize_maya[1]

        asset_folder = "ocio_test"
        file_prefix = "ocio_test"
        frame_list = "1"

        job_history_dir = tmp_path / "jobhistory"
        output_path = tmp_path / "output"
        project_path = script_location / asset_folder / "scene"
        scene_location = project_path / "test.ma"
        ocio_config_path = project_path / "config.ocio"

        # Sanity check the fixture exists before doing any Maya work.
        assert ocio_config_path.is_file(), f"OCIO config fixture missing at {ocio_config_path}"

        # Clean up sticky setting
        self._cleanup_sticky_settings(scene_location, script_location)

        os.makedirs(job_history_dir, exist_ok=True)
        os.makedirs(output_path, exist_ok=True)

        cmds.workspace(project_path, openWorkspace=True)
        cmds.workspace(fileRule=["images", output_path])

        cmds.file(scene_location, open=True, force=True)

        cmds.setAttr("defaultResolution.width", 960)
        cmds.setAttr("defaultResolution.height", 540)
        cmds.setAttr("defaultRenderGlobals.imageFilePrefix", file_prefix, type="string")
        cmds.optionVar(iv=("renderSetup_includeAllLights", 0))

        # The crux of this test: apply a custom OCIO config to Maya's
        # color management preferences. Scene.ocio_config_file() reads
        # this back via colorManagementPrefs(query=True, configFilePath=True).
        cmds.colorManagementPrefs(e=True, cmEnabled=True)
        cmds.colorManagementPrefs(e=True, configFilePath=str(ocio_config_path))

        widget = show_maya_render_submitter(None)

        settings = widget.job_settings_type()
        widget.shared_job_settings.update_settings(settings)
        widget.job_settings.update_settings(settings)

        settings.view_layer_selection = "All Renderable Layers"
        settings.camera_selection = "All Renderable Cameras"
        settings.description = ""
        settings.include_adaptor_wheels = False
        settings.override_frame_range = True
        settings.frame_list = frame_list

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

        # Template must be valid Open Job Description.
        assert is_valid_template(job_history_dir / "template.yaml")

        # Template should be identical to the mtoa_test template — the
        # OCIO state lives in parameter_values, not in the template.
        with (
            open(
                script_location / asset_folder / "expected_job_bundle" / "template.yaml"
            ) as expected,
            open(job_history_dir / "template.yaml") as actual,
        ):
            assert yaml.safe_load(expected) == yaml.safe_load(actual)

        # Expected parameter values include OCIOConfigFile (the bug fix
        # under test) and ArnoldErrorOnLicenseFailure (because we use
        # the Arnold-based mtoa scene as the OCIO test base).
        expected_parameter_values = {
            "parameterValues": [
                {"name": "MayaSceneFile", "value": str(scene_location)},
                {"name": "OutputFilePrefix", "value": file_prefix},
                {"name": "Frames", "value": frame_list},
                {"name": "ImageWidth", "value": 960},
                {"name": "ImageHeight", "value": 540},
                {"name": "ProjectPath", "value": str(project_path) + "/"},
                {"name": "OutputFilePath", "value": str(output_path)},
                {"name": "RenderSetupIncludeLights", "value": "false"},
                {"name": "OCIOConfigFile", "value": str(ocio_config_path)},
                {"name": "ArnoldErrorOnLicenseFailure", "value": "false"},
                {"name": "deadline:targetTaskRunStatus", "value": "READY"},
                {"name": "deadline:maxFailedTasksCount", "value": 20},
                {"name": "deadline:maxRetriesPerTask", "value": 5},
                {"name": "deadline:priority", "value": 50},
            ]
        }

        are_parameter_values_similar(job_history_dir, expected_parameter_values)

        # Asset references match the mtoa_test pattern, plus the OCIO
        # config file. Once colorManagementPrefs(configFilePath=...) is
        # set, Maya's filePathEditor reports the OCIO config as a scene
        # reference, so AssetIntrospector.parse_scene_assets() picks it
        # up and adds it to inputs.filenames. We use the
        # expected_scene_file_paths regex parameter to match it
        # dynamically rather than hard-coding the absolute path (which
        # may be canonicalized differently on the runner).
        # Note: the OCIOConfigFile PATH job parameter independently
        # delivers the file via Job Attachments — having the config in
        # both places is benign (the Job Attachments dataFlow:IN PATH
        # parameter and inputs.filenames both end up uploaded once).
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

        are_asset_references_similar(job_history_dir, expected_asset_references, [r"config\.ocio$"])
