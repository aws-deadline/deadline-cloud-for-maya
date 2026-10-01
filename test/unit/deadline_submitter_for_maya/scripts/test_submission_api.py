# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Tests for the Maya submission engine (deadline.maya_submitter.submitter).

Drives the stateful ``MayaSubmitter`` and the module-level builders directly.
The previous ``get_*_for_submission`` free-function wrappers were removed when
the engine moved to ``submitter.py``; these tests inject a pre-built
``MayaSceneContext`` so no live Maya scene is needed.
"""

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

    # Only clear the Qt-dependent UI modules so they re-import under the mocks
    # above. Do NOT clear the engine modules (submitter, cameras, render_layers,
    # data_classes): sibling test modules import those at module top, and
    # popping+re-importing them here creates a second module object. Under
    # pytest-xdist that leaves the sibling's top-level `MayaSubmitter` bound to
    # the old object while `patch(...)` targets the new one, so the patches miss
    # and the real Maya-querying code runs (flaky, worker-order dependent).
    modules_to_clear = [
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
    from deadline.maya_submitter.submitter import RenderLayerData

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
    from deadline.maya_submitter.submitter import MayaSceneContext
    from deadline.maya_submitter.cameras import ALL_CAMERAS

    if render_layers is None:
        render_layers = [_make_render_layer()]

    return MayaSceneContext(
        render_layers=render_layers,
        current_layer_selectable_cameras=[ALL_CAMERAS, "persp"],
        all_layer_selectable_cameras=[ALL_CAMERAS, "persp"],
    )


def _make_settings(**overrides):
    """Build a MayaSubmitterSettings for engine tests.

    Defaults mirror the old RenderSubmitterUISettings-based fixtures: a named
    job with the frame-range override on so single-value assertions are stable.
    """
    from deadline.maya_submitter.submitter import MayaSubmitterSettings

    settings = MayaSubmitterSettings()
    settings.job_name = overrides.pop("job_name", "test_job")
    settings.description = overrides.pop("description", "")
    settings.override_frame_range = overrides.pop("override_frame_range", False)
    for key, value in overrides.items():
        setattr(settings, key, value)
    return settings


class TestGetSettings:
    """Coverage for get_settings(), the default source of `settings` inside the
    inherited get_submission_context() and thus the linchpin of the headless /
    AYON submission path.
    """

    @staticmethod
    def _patch_scene(scene_name="/proj/shot/scene.ma", project="/proj", output="/proj/images"):
        scene_mock = Mock()
        scene_mock.name.return_value = scene_name
        scene_mock.project_path.return_value = project
        scene_mock.output_path.return_value = output
        anim_mock = Mock()
        anim_mock.frame_list.return_value = "1-10"
        return (
            patch("deadline.maya_submitter.submitter.Scene", scene_mock),
            patch("deadline.maya_submitter.submitter.Animation", anim_mock),
        )

    def test_get_settings_reads_scene(self):
        from deadline.maya_submitter.submitter import MayaSubmitter, MayaSubmitterSettings

        patches = self._patch_scene()
        for p in patches:
            p.start()
        try:
            settings = MayaSubmitter().get_settings()
        finally:
            for p in reversed(patches):
                p.stop()

        assert isinstance(settings, MayaSubmitterSettings)
        # job_name is the scene file's basename; scene-derived paths/frames flow through.
        assert settings.job_name == "scene.ma"
        assert settings.project_path == "/proj"
        assert settings.output_path == "/proj/images"
        assert settings.frame_list == "1-10"
        # Attachment defaults derive from the scene.
        assert settings.input_filenames == ["/proj/shot/scene.ma"]
        assert settings.input_directories == ["/proj"]
        assert settings.output_directories == ["/proj/images"]

    def test_get_settings_unsaved_scene_defaults_job_name(self):
        from deadline.maya_submitter.submitter import MayaSubmitter

        # Unsaved scene → empty name/paths → job_name falls back to "Untitled"
        # and the empty collections stay empty (no [""] entries).
        patches = self._patch_scene(scene_name="", project="", output="")
        for p in patches:
            p.start()
        try:
            settings = MayaSubmitter().get_settings()
        finally:
            for p in reversed(patches):
                p.stop()

        assert settings.job_name == "Untitled"
        assert settings.input_filenames == []
        assert settings.input_directories == []
        assert settings.output_directories == []

    def test_headless_round_trip(self):
        """get_settings() -> get_job_template() -> get_parameter_values() locks
        down the headless contract end-to-end (a fresh submitter, scene context
        injected so no live scan is needed).
        """
        from deadline.maya_submitter.submitter import MayaSubmitter

        patches = self._patch_scene()
        for p in patches:
            p.start()
        try:
            submitter = MayaSubmitter(scene_context=_make_context())
            settings = submitter.get_settings()
            job_template = submitter.get_job_template(settings)
            parameter_values = submitter.get_parameter_values(settings, [])
        finally:
            for p in reversed(patches):
                p.stop()

        assert job_template["name"] == "scene.ma"
        assert isinstance(job_template.get("steps"), list) and job_template["steps"]
        assert isinstance(parameter_values, list) and parameter_values
        # ProjectPath/OutputFilePath parameter values reflect the scene-derived settings.
        pv = {p["name"]: p["value"] for p in parameter_values if "name" in p and "value" in p}
        assert pv.get("ProjectPath") == "/proj"
        assert pv.get("OutputFilePath") == "/proj/images"


class TestGetJobTemplate:
    def test_returns_job_template_dict(self):
        from deadline.maya_submitter.submitter import MayaSubmitter

        settings = _make_settings(job_name="test_job", description="A test job")
        submitter = MayaSubmitter(scene_context=_make_context())

        result = submitter.get_job_template(settings)

        assert isinstance(result, dict)
        assert result["name"] == "test_job"
        assert result["description"] == "A test job"

    def test_host_requirements_injected_into_steps(self):
        from deadline.maya_submitter.submitter import MayaSubmitter

        settings = _make_settings(job_name="test_job")
        submitter = MayaSubmitter(scene_context=_make_context())
        host_requirements = {"amounts": [{"name": "amount.worker.vcpu", "min": 4}]}

        result = submitter.get_job_template(settings, host_requirements)

        assert result["steps"][0]["hostRequirements"] == host_requirements

    def test_timeout_injected_into_steps(self):
        """Activated timeout entries write their seconds to the matching action of every step."""
        from deadline.maya_submitter.submitter import MayaSubmitter

        settings = _make_settings(job_name="test_job")

        # Modify the default timeouts with non-default, distinct values so the
        # assertions cannot accidentally pass against the default seconds.
        settings.timeouts.entries["Task Run"].is_activated = True
        settings.timeouts.entries["Task Run"].seconds = 111
        settings.timeouts.entries["Maya Launch"].is_activated = True
        settings.timeouts.entries["Maya Launch"].seconds = 222
        settings.timeouts.entries["Maya Shutdown"].is_activated = True
        settings.timeouts.entries["Maya Shutdown"].seconds = 333

        submitter = MayaSubmitter(scene_context=_make_context())

        result = submitter.get_job_template(settings)

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
        from deadline.maya_submitter.submitter import MayaSubmitter

        settings = _make_settings(job_name="test_job")

        # Deactivate Task Run and Maya Shutdown; keep Maya Launch activated.
        settings.timeouts.entries["Task Run"].is_activated = False
        settings.timeouts.entries["Maya Launch"].is_activated = True
        settings.timeouts.entries["Maya Launch"].seconds = 222
        settings.timeouts.entries["Maya Shutdown"].is_activated = False

        submitter = MayaSubmitter(scene_context=_make_context())

        result = submitter.get_job_template(settings)

        assert result["steps"]
        for step in result["steps"]:
            env_actions = step["stepEnvironments"][0]["script"]["actions"]
            # Deactivated entries -> no timeout key on the action at all.
            assert "timeout" not in step["script"]["actions"]["onRun"]
            assert "timeout" not in env_actions["onExit"]
            # The one activated entry is still applied.
            assert env_actions["onEnter"]["timeout"] == 222

    def test_scans_scene_if_no_context_injected(self):
        from deadline.maya_submitter.submitter import MayaSubmitter

        settings = _make_settings(job_name="test_job")
        context = _make_context()

        with patch(
            "deadline.maya_submitter.submitter.create_scene_context",
            return_value=context,
        ) as mock_create:
            MayaSubmitter().get_job_template(settings)

        mock_create.assert_called_once()

    def test_missing_wheels_dir_raises_runtimeerror(self):
        """With include_adaptor_wheels on but no wheels dir, the guard must raise a
        user-facing RuntimeError — not fall through to a bare FileNotFoundError from
        os.listdir. Regression test for the previously-inverted guard
        (`not exists and is_dir`, which was always False).

        Exercises the builder directly (single render layer) so the real default
        template loads; only the wheels-dir existence check is stubbed absent.
        """
        from pathlib import Path

        from deadline.maya_submitter.submitter import (
            MayaSubmitter,
            get_default_job_template,
        )

        settings = _make_settings(job_name="test_job")
        settings.include_adaptor_wheels = True
        layer = _make_render_layer(renderer_name="mayaSoftware", frame_range="1")

        # Make only the wheels directory look absent (the guard calls .exists() on
        # the wheels Path). Other Path.exists() calls are unaffected.
        real_exists = Path.exists

        def fake_exists(self):
            if self.name == "wheels":
                return False
            return real_exists(self)

        with patch("deadline.maya_submitter.submitter.Path.exists", new=fake_exists):
            with pytest.raises(RuntimeError, match="wheels directory does not exist"):
                MayaSubmitter._get_job_template(
                    default_job_template=get_default_job_template(),
                    settings=settings,
                    renderers={"mayaSoftware"},
                    render_layers=[layer],
                    all_layer_selectable_cameras=[],
                    current_layer_selectable_cameras=[],
                )


class TestGetParameterValues:
    def test_returns_parameter_values_list(self):
        from deadline.maya_submitter.submitter import MayaSubmitter

        settings = _make_settings(
            job_name="test_job",
            frame_list="1-10",
            project_path="/tmp/project",
            output_path="/tmp/output",
        )
        submitter = MayaSubmitter(scene_context=_make_context())

        with patch(
            "deadline.maya_submitter.submitter.MayaSubmitter._get_parameter_values",
            return_value=[{"name": "Frames", "value": "1-10"}],
        ):
            result = submitter.get_parameter_values(settings, [])

        assert isinstance(result, list)
        assert result[0]["name"] == "Frames"

    def test_queue_parameters_passed_through(self):
        from deadline.maya_submitter.submitter import MayaSubmitter

        settings = _make_settings(
            job_name="test_job",
            frame_list="1-10",
            project_path="/tmp/project",
            output_path="/tmp/output",
        )
        submitter = MayaSubmitter(scene_context=_make_context())
        queue_params = [{"name": "CondaPackages", "value": "maya=2026.*"}]

        with patch(
            "deadline.maya_submitter.submitter.MayaSubmitter._get_parameter_values",
        ) as mock_get_params:
            mock_get_params.return_value = [
                {"name": "Frames", "value": "1-10"},
                {"name": "CondaPackages", "value": "maya=2026.*"},
            ]
            submitter.get_parameter_values(settings, queue_params)

        # Verify queue_parameters were passed through as the 4th positional arg.
        call_args = mock_get_params.call_args
        assert call_args[0][3] == queue_params

    def test_scans_scene_if_no_context_injected(self):
        from deadline.maya_submitter.submitter import MayaSubmitter

        settings = _make_settings(
            job_name="test_job",
            frame_list="1-10",
            project_path="/tmp/project",
            output_path="/tmp/output",
        )
        context = _make_context()

        with (
            patch(
                "deadline.maya_submitter.submitter.create_scene_context",
                return_value=context,
            ) as mock_create,
            patch(
                "deadline.maya_submitter.submitter.MayaSubmitter._get_parameter_values",
                return_value=[],
            ),
        ):
            MayaSubmitter().get_parameter_values(settings, [])

        mock_create.assert_called_once()


class TestGetAssetReferences:
    def test_returns_asset_references(self):
        """get_asset_references introspects the scene and classifies auto-detected
        paths into input files vs directories (existing paths only), plus the scene
        file itself. Returns the typed AssetReferences, not a dict.
        """
        from deadline.client.job_bundle.submission import AssetReferences
        from deadline.maya_submitter.submitter import MayaSubmitter

        settings = _make_settings(output_directories=["/renders"])
        # Injected context → no real scene scan for the output-dir collection.
        submitter = MayaSubmitter(scene_context=_make_context())

        with (
            patch("deadline.maya_submitter.submitter.Scene") as scene_mock,
            patch("deadline.maya_submitter.submitter.AssetIntrospector") as introspector,
            patch("deadline.maya_submitter.submitter.os.path.exists", return_value=True),
            patch(
                "deadline.maya_submitter.submitter.os.path.isdir",
                side_effect=lambda p: p == "/textures",
            ),
        ):
            scene_mock.name.return_value = "scene.ma"
            introspector.return_value.parse_scene_assets.return_value = [
                "/textures",  # a directory
                "/assets/wood.png",  # a file
            ]
            result = submitter.get_asset_references(settings)

        assert isinstance(result, AssetReferences)
        # scene file + introspected file are inputs; the directory is an input dir.
        assert "scene.ma" in result.input_filenames
        assert "/assets/wood.png" in result.input_filenames
        assert "/textures" in result.input_directories

    def test_drops_nonexistent_introspected_paths(self):
        """Auto-detected paths that don't exist on disk cannot be uploaded and are dropped."""
        from deadline.client.job_bundle.submission import AssetReferences
        from deadline.maya_submitter.submitter import MayaSubmitter

        settings = _make_settings(output_directories=["/renders"])
        submitter = MayaSubmitter(scene_context=_make_context())

        with (
            patch("deadline.maya_submitter.submitter.Scene") as scene_mock,
            patch("deadline.maya_submitter.submitter.AssetIntrospector") as introspector,
            patch("deadline.maya_submitter.submitter.os.path.exists", return_value=False),
        ):
            scene_mock.name.return_value = "scene.ma"
            introspector.return_value.parse_scene_assets.return_value = ["/missing/tex.png"]
            result = submitter.get_asset_references(settings)

        assert isinstance(result, AssetReferences)
        assert "/missing/tex.png" not in result.input_filenames
        assert "/missing/tex.png" not in result.input_directories

    def test_output_directories_combine_settings_and_layers(self):
        """Output dirs = settings.output_directories ∪ each render layer's output_directories."""
        from deadline.client.job_bundle.submission import AssetReferences
        from deadline.maya_submitter.submitter import MayaSubmitter

        settings = _make_settings(output_directories=["/renders"])
        # Layer carries its own scene-derived output dir (see _make_render_layer).
        context = _make_context([_make_render_layer()])
        submitter = MayaSubmitter(scene_context=context)

        with (
            patch("deadline.maya_submitter.submitter.Scene") as scene_mock,
            patch("deadline.maya_submitter.submitter.AssetIntrospector") as introspector,
        ):
            scene_mock.name.return_value = "scene.ma"
            introspector.return_value.parse_scene_assets.return_value = []
            result = submitter.get_asset_references(settings)

        assert isinstance(result, AssetReferences)
        # settings default + the layer's /tmp/renders (from _make_render_layer).
        assert "/renders" in result.output_directories
        assert "/tmp/renders" in result.output_directories


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
        """Build a MayaSubmitterSettings populated for parameter generation."""
        return _make_settings(
            job_name="test_job",
            override_frame_range=True,
            frame_list="1",
            project_path="/tmp/project",
            output_path="/tmp/output",
        )

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
            patch("deadline.maya_submitter.submitter.Scene", scene_mock),
            patch(
                "deadline.maya_submitter.submitter.render_setup_include_all_lights",
                return_value=True,
            ),
            patch(
                "deadline.maya_submitter.submitter.get_width",
                return_value=1920,
            ),
            patch(
                "deadline.maya_submitter.submitter.get_height",
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
        from deadline.maya_submitter.submitter import MayaSubmitter

        settings = self._build_settings()
        # Use mayaSoftware so the Arnold-specific branch is skipped.
        context = _make_context([_make_render_layer(renderer_name="mayaSoftware", frame_range="1")])
        submitter = MayaSubmitter(scene_context=context)

        patches = self._patch_scene(ocio_return_value=None)
        for p in patches:
            p.start()
        try:
            template = submitter.get_job_template(settings)
            param_values = submitter.get_parameter_values(settings, [])
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
        from deadline.maya_submitter.submitter import MayaSubmitter

        ocio_path = "/projects/show/aces_1.3/config.ocio"
        settings = self._build_settings()
        context = _make_context([_make_render_layer(renderer_name="mayaSoftware", frame_range="1")])
        submitter = MayaSubmitter(scene_context=context)

        patches = self._patch_scene(ocio_return_value=ocio_path)
        for p in patches:
            p.start()
        try:
            param_values = submitter.get_parameter_values(settings, [])
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
        from deadline.maya_submitter.submitter import MayaSubmitter

        settings = self._build_settings()
        context = _make_context([_make_render_layer(renderer_name="mayaSoftware", frame_range="1")])
        submitter = MayaSubmitter(scene_context=context)

        patches = self._patch_scene(ocio_return_value=None)
        for p in patches:
            p.start()
        try:
            template = submitter.get_job_template(settings)
            param_values = submitter.get_parameter_values(settings, [])
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
