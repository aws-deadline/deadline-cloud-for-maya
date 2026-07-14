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

    def test_timeout_injected_into_steps(self):
        """Activated timeout entries write their seconds to the matching action of every step."""
        from deadline.maya_submitter.data_classes import RenderSubmitterUISettings
        from deadline.maya_submitter.maya_render_submitter import (
            get_job_template_for_submission,
        )

        settings = RenderSubmitterUISettings()
        settings.name = "test_job"
        settings.description = ""
        settings.override_frame_range = False

        # Modify the default timeouts with non-default, distinct values so the
        # assertions cannot accidentally pass against the default seconds.
        settings.timeouts.entries["Task Run"].is_activated = True
        settings.timeouts.entries["Task Run"].seconds = 111
        settings.timeouts.entries["Maya Launch"].is_activated = True
        settings.timeouts.entries["Maya Launch"].seconds = 222
        settings.timeouts.entries["Maya Shutdown"].is_activated = True
        settings.timeouts.entries["Maya Shutdown"].seconds = 333

        context = _make_context()

        result = get_job_template_for_submission(settings, context=context)

        assert result["steps"]
        for step in result["steps"]:
            env_actions = step["stepEnvironments"][0]["script"]["actions"]
            # Task Run -> step script onRun
            assert step["script"]["actions"]["onRun"]["timeout"] == 111
            # Maya Launch / Shutdown -> step environment onEnter / onExit
            assert env_actions["onEnter"]["timeout"] == 222
            assert env_actions["onExit"]["timeout"] == 333

    def test_deactivated_timeout_not_written_to_step(self):
        """An entry with is_activated=False must not add a timeout to its action."""
        from deadline.maya_submitter.data_classes import RenderSubmitterUISettings
        from deadline.maya_submitter.maya_render_submitter import (
            get_job_template_for_submission,
        )

        settings = RenderSubmitterUISettings()
        settings.name = "test_job"
        settings.description = ""
        settings.override_frame_range = False

        # Deactivate Task Run and Maya Shutdown; keep Maya Launch activated.
        settings.timeouts.entries["Task Run"].is_activated = False
        settings.timeouts.entries["Maya Launch"].is_activated = True
        settings.timeouts.entries["Maya Launch"].seconds = 222
        settings.timeouts.entries["Maya Shutdown"].is_activated = False

        context = _make_context()

        result = get_job_template_for_submission(settings, context=context)

        assert result["steps"]
        for step in result["steps"]:
            env_actions = step["stepEnvironments"][0]["script"]["actions"]
            # Deactivated entries -> no timeout key on the action at all.
            assert "timeout" not in step["script"]["actions"]["onRun"]
            assert "timeout" not in env_actions["onExit"]
            # The one activated entry is still applied.
            assert env_actions["onEnter"]["timeout"] == 222

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


class TestOCIOInJobBundle:
    """OCIO Config File coverage for the submission flow.

    Regression coverage for the 0.15.13 OCIO submission failure that
    was fixed in 0.15.14: customers without an OCIO config in their
    Maya scene experienced "Job bundle validation failed" errors
    because the HIDDEN PATH ``OCIOConfigFile`` parameter relied on its
    empty-string default and that default was rejected by older
    versions of ``openjd-model-for-python``. This was fixed by
    upgrading the dependency in 0.15.14, but the developer test suite
    didn't exercise the customer-default code path. These tests close
    that gap by covering each branch of the OCIO submission code path
    end-to-end.
    """

    @staticmethod
    def _build_settings():
        """Build a RenderSubmitterUISettings populated for parameter generation."""
        from deadline.maya_submitter.data_classes import RenderSubmitterUISettings

        settings = RenderSubmitterUISettings()
        settings.name = "test_job"
        settings.description = ""
        settings.override_frame_range = True
        settings.frame_list = "1"
        settings.project_path = "/tmp/project"
        settings.output_path = "/tmp/output"
        return settings

    @staticmethod
    def _patch_scene(ocio_return_value):
        """Patch the Scene module-level reference and supporting helpers used
        by ``_get_parameter_values`` so we can drive its branching logic
        without a live Maya scene.
        """
        scene_mock = Mock()
        scene_mock.name.return_value = "/tmp/scene/test.ma"
        scene_mock.ocio_config_file.return_value = ocio_return_value
        scene_mock.error_on_arnold_license_fail.return_value = True

        return [
            patch("deadline.maya_submitter.maya_render_submitter.Scene", scene_mock),
            patch(
                "deadline.maya_submitter.maya_render_submitter.render_setup_include_all_lights",
                return_value=True,
            ),
            patch(
                "deadline.maya_submitter.maya_render_submitter.get_width",
                return_value=1920,
            ),
            patch(
                "deadline.maya_submitter.maya_render_submitter.get_height",
                return_value=1080,
            ),
        ]

    def test_no_ocio_omits_value_but_keeps_definition(self):
        """Maya scene without OCIO config. The submitter MUST omit
        ``OCIOConfigFile`` from parameter_values so the parameter falls
        back to its empty-string default. The job template MUST still
        declare the parameter as a HIDDEN PATH with default=''. This
        is the customer state that triggered the 0.15.13 regression.
        """
        from deadline.maya_submitter.maya_render_submitter import (
            get_job_template_for_submission,
            get_parameter_values_for_submission,
        )

        settings = self._build_settings()
        # Use mayaSoftware so the Arnold-specific branch is skipped.
        context = _make_context([_make_render_layer(renderer_name="mayaSoftware", frame_range="1")])

        patches = self._patch_scene(ocio_return_value=None)
        for p in patches:
            p.start()
        try:
            template = get_job_template_for_submission(settings, context=context)
            param_values = get_parameter_values_for_submission(settings, context=context)
        finally:
            for p in reversed(patches):
                p.stop()

        # The OCIOConfigFile parameter definition stays in the template.
        ocio_def = next(
            (p for p in template["parameterDefinitions"] if p["name"] == "OCIOConfigFile"),
            None,
        )
        assert ocio_def is not None, "OCIOConfigFile parameter definition is missing"
        assert ocio_def["type"] == "PATH"
        assert ocio_def["userInterface"]["control"] == "HIDDEN"
        assert ocio_def["default"] == ""

        # And the value is omitted (the default is what the worker will see).
        assert not any(
            v["name"] == "OCIOConfigFile" for v in param_values
        ), "OCIOConfigFile must NOT be added to parameter_values when the scene has no OCIO config"

    def test_ocio_present_adds_value_to_parameter_values(self):
        """Maya scene with a custom OCIO config. The submitter MUST
        add ``OCIOConfigFile`` to parameter_values with the path
        returned by ``Scene.ocio_config_file()``.
        """
        from deadline.maya_submitter.maya_render_submitter import (
            get_parameter_values_for_submission,
        )

        ocio_path = "/projects/show/aces_1.3/config.ocio"
        settings = self._build_settings()
        context = _make_context([_make_render_layer(renderer_name="mayaSoftware", frame_range="1")])

        patches = self._patch_scene(ocio_return_value=ocio_path)
        for p in patches:
            p.start()
        try:
            param_values = get_parameter_values_for_submission(settings, context=context)
        finally:
            for p in reversed(patches):
                p.stop()

        ocio_value = next((v for v in param_values if v["name"] == "OCIOConfigFile"), None)
        assert ocio_value is not None, "OCIOConfigFile must be added to parameter_values"
        assert ocio_value["value"] == ocio_path

    def test_hidden_path_with_empty_default_validates(self):
        """HIDDEN PATH JobParameter handling with default=''.

        This is the exact failure mode from the 0.15.13 regression — when a HIDDEN
        PATH parameter declares ``default: ''`` and ``deadline-cloud``
        attempts to validate the bundle, older versions raised "Job
        bundle validation failed". This test runs the actual validation
        code path that's used by the Submit dialog.
        """
        from deadline.client.job_bundle.parameters import validate_job_parameter

        ocio_definition = {
            "name": "OCIOConfigFile",
            "type": "PATH",
            "objectType": "FILE",
            "dataFlow": "IN",
            "userInterface": {"control": "HIDDEN"},
            "description": "The OCIO configuration file path (auto-detected from scene).",
            "default": "",
        }

        # validate_job_parameter raises ValueError/TypeError on bad definitions.
        # Must succeed cleanly with the default empty string.
        result = validate_job_parameter(ocio_definition, type_required=True)
        assert result["name"] == "OCIOConfigFile"
        assert result["default"] == ""

    def test_default_template_yaml_ocio_param_validates(self):
        """The bundled default_maya_job_template.yaml must always declare
        an ``OCIOConfigFile`` parameter that passes deadline-cloud's
        bundle parameter validation. This protects the contract that
        broke in the 0.15.13 regression (HIDDEN PATH with empty default) so future
        edits to the template can't silently regress it.
        """
        from pathlib import Path

        import yaml
        from deadline.client.job_bundle.parameters import validate_job_parameter

        # Resolve the path to default_maya_job_template.yaml relative to
        # this test file so it works in any checkout layout.
        repo_root = Path(__file__).resolve().parents[4]
        template_path = repo_root / "src/deadline/maya_submitter/default_maya_job_template.yaml"
        assert template_path.is_file(), f"Template file not found at {template_path}"

        with open(template_path, encoding="utf8") as f:
            template = yaml.safe_load(f)

        # The OCIO parameter must be declared with the exact contract the
        # adaptor's set_ocio_config_file relies on.
        ocio_def = next(
            (p for p in template["parameterDefinitions"] if p["name"] == "OCIOConfigFile"),
            None,
        )
        assert ocio_def is not None, "OCIOConfigFile parameter is missing from default template"
        assert ocio_def["type"] == "PATH"
        assert ocio_def["userInterface"]["control"] == "HIDDEN"
        assert ocio_def["default"] == ""

        # Every parameter definition (not just OCIO) must validate so the
        # default template is always submittable as-is.
        for param_def in template["parameterDefinitions"]:
            validate_job_parameter(param_def, type_required=True)

    def test_full_bundle_with_no_ocio_passes_parameter_validation(self):
        """End-to-end no-OCIO regression: build the full job template
        and parameter_values for a scene without an OCIO config (the
        customer state that broke), then run every parameter through
        deadline-cloud's bundle parameter validation. This is the
        highest-fidelity reproduction of the 0.15.13 regression in unit form.
        """
        from deadline.client.job_bundle.parameters import (
            validate_job_parameter,
            validate_job_parameter_value,
        )
        from deadline.maya_submitter.maya_render_submitter import (
            get_job_template_for_submission,
            get_parameter_values_for_submission,
        )

        settings = self._build_settings()
        context = _make_context([_make_render_layer(renderer_name="mayaSoftware", frame_range="1")])

        patches = self._patch_scene(ocio_return_value=None)
        for p in patches:
            p.start()
        try:
            template = get_job_template_for_submission(settings, context=context)
            param_values = get_parameter_values_for_submission(settings, context=context)
        finally:
            for p in reversed(patches):
                p.stop()

        # Validate every parameter definition — equivalent to what the
        # Submit dialog does before sending the bundle to the service.
        validated_defs = {
            p["name"]: validate_job_parameter(p, type_required=True)
            for p in template["parameterDefinitions"]
        }

        # Validate every supplied value against its definition.
        for v in param_values:
            if v["name"] in validated_defs:
                validate_job_parameter_value(validated_defs[v["name"]], v["value"])

        # The defining assertion: OCIOConfigFile is declared with default=''
        # and not overridden by parameter_values. If the bundle assembled
        # this way ever fails to validate again, this test will fail —
        # which is precisely what was missing when 0.15.13 shipped.
        assert validated_defs["OCIOConfigFile"]["default"] == ""
        assert not any(v["name"] == "OCIOConfigFile" for v in param_values)
