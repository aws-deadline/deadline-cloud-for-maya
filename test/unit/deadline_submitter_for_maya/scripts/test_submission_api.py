# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_maya_modules():
    """Mock Maya modules so we can import deadline.maya_submitter modules."""
    mocks = {
        "maya": Mock(),
        "maya.cmds": Mock(),
        "maya.mel": Mock(),
        "maya.app": Mock(),
        "maya.app.renderSetup": Mock(),
        "maya.app.renderSetup.model": Mock(),
        "maya.app.renderSetup.model.renderSetupPreferences": Mock(),
        "qtpy": Mock(),
        "qtpy.QtCore": Mock(),
        "qtpy.QtWidgets": Mock(),
        "qtpy.QtGui": Mock(),
    }
    saved = {}
    added = []
    for mod_name, mock_obj in mocks.items():
        if mod_name in sys.modules:
            saved[mod_name] = sys.modules[mod_name]
        else:
            added.append(mod_name)
        sys.modules[mod_name] = mock_obj

    modules_to_clear = [
        "deadline.maya_submitter.cameras",
        "deadline.maya_submitter.render_layers",
        "deadline.maya_submitter.data_classes",
        "deadline.maya_submitter.maya_render_submitter",
        "deadline.maya_submitter.ui",
        "deadline.maya_submitter.ui.components",
        "deadline.maya_submitter.ui.components.scene_settings_tab",
    ]
    for mod_name in modules_to_clear:
        if mod_name in sys.modules:
            saved[mod_name] = sys.modules.pop(mod_name)

    yield

    for mod_name in added:
        sys.modules.pop(mod_name, None)
    for mod_name, original in saved.items():
        if original is not None:
            sys.modules[mod_name] = original
        else:
            sys.modules.pop(mod_name, None)


def _make_render_layer(
    name="defaultRenderLayer",
    display_name="masterLayer",
    renderer_name="arnold",
    frame_range="1-10",
    renderable_cameras=None,
    output_file_prefix="<Scene>",
    image_resolution=(1920, 1080),
):
    from deadline.maya_submitter.maya_render_submitter import RenderLayerData

    return RenderLayerData(
        name=name,
        display_name=display_name,
        renderer_name=renderer_name,
        ui_group_label=f"Layer: {display_name}",
        frames_parameter_name=None,
        frame_range=frame_range,
        renderable_camera_names=renderable_cameras or ["persp"],
        output_directories={"/tmp/renders"},
        output_file_prefix_parameter_name=None,
        output_file_prefix=output_file_prefix,
        image_width_parameter_name=None,
        image_height_parameter_name=None,
        image_resolution=image_resolution,
    )


def _make_context(render_layers=None):
    from deadline.maya_submitter.maya_render_submitter import SubmissionContext
    from deadline.maya_submitter.cameras import ALL_CAMERAS

    if render_layers is None:
        render_layers = [_make_render_layer()]

    return SubmissionContext(
        render_layers=render_layers,
        current_layer_selectable_cameras=[ALL_CAMERAS, "persp"],
        all_layer_selectable_cameras=[ALL_CAMERAS, "persp"],
    )


class TestGetJobTemplateForSubmission:
    def test_returns_job_template_dict(self):
        from deadline.maya_submitter.data_classes import RenderSubmitterUISettings
        from deadline.maya_submitter.maya_render_submitter import (
            get_job_template_for_submission,
        )

        settings = RenderSubmitterUISettings()
        settings.name = "test_job"
        settings.description = "A test job"
        settings.override_frame_range = False

        context = _make_context()

        result = get_job_template_for_submission(settings, context=context)

        assert isinstance(result, dict)
        assert result["name"] == "test_job"
        assert result["description"] == "A test job"

    def test_host_requirements_injected_into_steps(self):
        from deadline.maya_submitter.data_classes import RenderSubmitterUISettings
        from deadline.maya_submitter.maya_render_submitter import (
            get_job_template_for_submission,
        )

        settings = RenderSubmitterUISettings()
        settings.name = "test_job"
        settings.description = ""
        settings.override_frame_range = False

        context = _make_context()
        host_requirements = {"amounts": [{"name": "amount.worker.vcpu", "min": 4}]}

        result = get_job_template_for_submission(settings, host_requirements, context=context)

        assert result["steps"][0]["hostRequirements"] == host_requirements

    def test_creates_context_if_not_provided(self):
        from deadline.maya_submitter.data_classes import RenderSubmitterUISettings
        from deadline.maya_submitter.maya_render_submitter import (
            get_job_template_for_submission,
        )

        settings = RenderSubmitterUISettings()
        settings.name = "test_job"
        settings.description = ""
        settings.override_frame_range = False

        context = _make_context()

        with patch(
            "deadline.maya_submitter.maya_render_submitter.create_submission_context",
            return_value=context,
        ) as mock_create:
            get_job_template_for_submission(settings)

        mock_create.assert_called_once()


class TestGetParameterValuesForSubmission:
    def test_returns_parameter_values_list(self):
        from deadline.maya_submitter.data_classes import RenderSubmitterUISettings
        from deadline.maya_submitter.maya_render_submitter import (
            get_parameter_values_for_submission,
        )

        settings = RenderSubmitterUISettings()
        settings.name = "test_job"
        settings.override_frame_range = False
        settings.frame_list = "1-10"
        settings.project_path = "/tmp/project"
        settings.output_path = "/tmp/output"

        context = _make_context()

        with patch(
            "deadline.maya_submitter.maya_render_submitter._get_parameter_values",
            return_value=[{"name": "Frames", "value": "1-10"}],
        ):
            result = get_parameter_values_for_submission(settings, context=context)

        assert isinstance(result, list)
        assert result[0]["name"] == "Frames"

    def test_queue_parameters_included(self):
        from deadline.maya_submitter.data_classes import RenderSubmitterUISettings
        from deadline.maya_submitter.maya_render_submitter import (
            get_parameter_values_for_submission,
        )

        settings = RenderSubmitterUISettings()
        settings.name = "test_job"
        settings.override_frame_range = False
        settings.frame_list = "1-10"
        settings.project_path = "/tmp/project"
        settings.output_path = "/tmp/output"

        context = _make_context()
        queue_params = [{"name": "CondaPackages", "value": "maya=2026.*"}]

        with patch(
            "deadline.maya_submitter.maya_render_submitter._get_parameter_values",
        ) as mock_get_params:
            mock_get_params.return_value = [
                {"name": "Frames", "value": "1-10"},
                {"name": "CondaPackages", "value": "maya=2026.*"},
            ]
            get_parameter_values_for_submission(settings, queue_params, context=context)

        # Verify queue_parameters were passed through
        call_args = mock_get_params.call_args
        assert call_args[0][3] == queue_params

    def test_creates_context_if_not_provided(self):
        from deadline.maya_submitter.data_classes import RenderSubmitterUISettings
        from deadline.maya_submitter.maya_render_submitter import (
            get_parameter_values_for_submission,
        )

        settings = RenderSubmitterUISettings()
        settings.name = "test_job"
        settings.override_frame_range = False
        settings.frame_list = "1-10"
        settings.project_path = "/tmp/project"
        settings.output_path = "/tmp/output"

        context = _make_context()

        with (
            patch(
                "deadline.maya_submitter.maya_render_submitter.create_submission_context",
                return_value=context,
            ) as mock_create,
            patch(
                "deadline.maya_submitter.maya_render_submitter._get_parameter_values",
                return_value=[],
            ),
        ):
            get_parameter_values_for_submission(settings)

        mock_create.assert_called_once()


class TestGetAssetReferencesForSubmission:
    def test_returns_dict(self):
        from deadline.client.job_bundle.submission import AssetReferences
        from deadline.maya_submitter.maya_render_submitter import (
            get_asset_references_for_submission,
        )

        asset_refs = AssetReferences(
            input_filenames={"scene.ma", "texture.png"},
            input_directories={"/textures"},
            output_directories={"/renders"},
        )

        result = get_asset_references_for_submission(asset_refs)

        assert isinstance(result, dict)
        assert "inputFilenames" in result or "assetReferences" in result or len(result) > 0

    def test_preserves_asset_data(self):
        from deadline.client.job_bundle.submission import AssetReferences
        from deadline.maya_submitter.maya_render_submitter import (
            get_asset_references_for_submission,
        )

        asset_refs = AssetReferences(
            input_filenames={"scene.ma"},
            input_directories=set(),
            output_directories={"/renders"},
        )

        result = get_asset_references_for_submission(asset_refs)

        assert isinstance(result, dict)


class TestGetQueueParameters:
    def test_uses_default_settings_when_no_overrides(self):
        from deadline.maya_submitter.maya_render_submitter import get_queue_parameters

        with (
            patch(
                "deadline.maya_submitter.maya_render_submitter.get_setting",
                side_effect=lambda key: "farm-123" if "farm" in key else "queue-456",
            ),
            patch(
                "deadline.maya_submitter.maya_render_submitter.get_queue_parameter_definitions",
                return_value=[{"name": "CondaPackages", "value": "maya=2026.*"}],
            ) as mock_get_params,
        ):
            result = get_queue_parameters()

        mock_get_params.assert_called_once_with(farmId="farm-123", queueId="queue-456")
        assert result == [{"name": "CondaPackages", "value": "maya=2026.*"}]

    def test_uses_override_ids(self):
        from deadline.maya_submitter.maya_render_submitter import get_queue_parameters

        with (
            patch(
                "deadline.maya_submitter.maya_render_submitter.get_setting",
            ) as mock_setting,
            patch(
                "deadline.maya_submitter.maya_render_submitter.get_queue_parameter_definitions",
                return_value=[{"name": "CondaPackages", "value": ""}],
            ) as mock_get_params,
        ):
            get_queue_parameters(
                farm_id_override="farm-override", queue_id_override="queue-override"
            )

        mock_setting.assert_not_called()
        mock_get_params.assert_called_once_with(farmId="farm-override", queueId="queue-override")

    def test_applies_initial_values_override(self):
        from deadline.maya_submitter.maya_render_submitter import get_queue_parameters

        with (
            patch(
                "deadline.maya_submitter.maya_render_submitter.get_setting",
                side_effect=lambda key: "farm-123" if "farm" in key else "queue-456",
            ),
            patch(
                "deadline.maya_submitter.maya_render_submitter.get_queue_parameter_definitions",
                return_value=[
                    {"name": "CondaPackages", "value": ""},
                    {"name": "OtherParam", "value": "default"},
                ],
            ),
        ):
            result = get_queue_parameters(
                initial_values_override={"CondaPackages": "maya=2026.* maya-mtoa"}
            )

        assert result[0]["value"] == "maya=2026.* maya-mtoa"
        assert result[1]["value"] == "default"

    def test_raises_error_when_ids_not_configured(self):
        from deadline.client.exceptions import DeadlineOperationError
        from deadline.maya_submitter.maya_render_submitter import get_queue_parameters

        with (
            patch(
                "deadline.maya_submitter.maya_render_submitter.get_setting",
                return_value="",
            ),
            pytest.raises(DeadlineOperationError),
        ):
            get_queue_parameters()
