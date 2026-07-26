# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
from unittest.mock import Mock

import pytest


def test_frame_override_has_text_validation():
    # Modules to clean up after the test
    modules_to_restore = {}
    modules_to_remove = []

    try:
        # Create new mocks. We need to use a real class for QWidget instead of a Mock() so that the
        # SceneSettingsWidget which is a subclass of QWidget actually runs its methods (instead its
        # methods being mocked out).
        class MockQWidget:
            setEnabled = Mock()

            def __init__(self, parent):
                pass

        mock_q_widgets = Mock()
        mock_line_edit = Mock()

        mock_q_widgets.QWidget = MockQWidget
        mock_q_widgets.QLineEdit = mock_line_edit

        # Mock all modules needed by scene_settings_tab.py and its transitive imports
        mocks = {
            "qtpy.QtWidgets": mock_q_widgets,
            "qtpy.QtCore": Mock(),
            "qtpy.QtGui": Mock(),
            "deadline.client.ui": Mock(),
            "maya": Mock(),
            "maya.cmds": Mock(),
            "maya.mel": Mock(),
            "maya.app": Mock(),
            "maya.app.renderSetup": Mock(),
            "maya.app.renderSetup.model": Mock(),
            "maya.app.renderSetup.model.renderSetupPreferences": Mock(),
        }

        for mod_name, mock_obj in mocks.items():
            if mod_name in sys.modules:
                modules_to_restore[mod_name] = sys.modules[mod_name]
            else:
                modules_to_remove.append(mod_name)
            sys.modules[mod_name] = mock_obj

        # Remove cached imports of the module under test so it reimports with mocks
        modules_to_clear = [
            "deadline.maya_submitter.ui",
            "deadline.maya_submitter.ui.components",
            "deadline.maya_submitter.ui.components.scene_settings_tab",
            "deadline.maya_submitter.render_layers",
            "deadline.maya_submitter.cameras",
            "deadline.maya_submitter.data_classes",
        ]
        for mod_name in modules_to_clear:
            if mod_name in sys.modules:
                modules_to_restore.setdefault(mod_name, sys.modules[mod_name])
                del sys.modules[mod_name]

        from deadline.maya_submitter.ui.components.scene_settings_tab import SceneSettingsWidget

        # Stub out methods that interact with Qt state
        SceneSettingsWidget._configure_settings = Mock()  # type: ignore
        SceneSettingsWidget._fill_cameras_box = Mock()  # type: ignore

        # Create the scene widget
        SceneSettingsWidget(initial_settings=Mock())

        # Verify that the validator was set on the frame override line edit
        assert mock_line_edit.return_value.setValidator.call_count == 1
        # Make sure the mock is working and there's at least 1 call (because there's at least 1 line edit element)
        assert mock_line_edit.call_count > 0

    finally:
        # Restore original module state
        for mod_name in modules_to_remove:
            sys.modules.pop(mod_name, None)
        for mod_name, original in modules_to_restore.items():
            if original is not None:
                sys.modules[mod_name] = original
            else:
                sys.modules.pop(mod_name, None)


class TestCameraPopulation:
    """Tests that _populate_selectable_cameras correctly populates render_settings."""

    @pytest.fixture(autouse=True)
    def mock_maya_modules(self):
        """Mock Maya modules so we can import deadline.maya_submitter modules."""
        mocks = {
            "maya": Mock(),
            "maya.cmds": Mock(),
            "maya.mel": Mock(),
            "maya.app": Mock(),
            "maya.app.renderSetup": Mock(),
            "maya.app.renderSetup.model": Mock(),
            "maya.app.renderSetup.model.renderSetupPreferences": Mock(),
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

    def _make_layer(self, renderable_cameras):
        """Create a mock render layer with the given camera names."""
        layer = Mock()
        layer.renderable_camera_names = renderable_cameras
        return layer

    def test_cameras_populated_with_multiple_layers(self):
        """All-layers mode should show only cameras common to ALL layers (intersection)."""
        from unittest.mock import patch

        from deadline.maya_submitter.cameras import ALL_CAMERAS
        from deadline.maya_submitter.data_classes import RenderSubmitterUISettings
        from deadline.maya_submitter.maya_render_submitter import _populate_selectable_cameras

        render_settings = RenderSubmitterUISettings()
        render_layers = [
            self._make_layer(["cam_front", "cam_side", "cam_top"]),
            self._make_layer(["cam_front", "cam_side"]),
        ]

        with patch(
            "deadline.maya_submitter.maya_render_submitter.get_renderable_camera_names",
            return_value=["cam_front", "cam_side", "cam_top"],
        ):
            _populate_selectable_cameras(render_settings, render_layers)

        assert render_settings.current_layer_selectable_cameras == [
            ALL_CAMERAS,
            "cam_front",
            "cam_side",
            "cam_top",
        ]
        assert render_settings.all_layer_selectable_cameras == [
            ALL_CAMERAS,
            "cam_front",
            "cam_side",
        ]

    def test_cameras_default_without_population(self):
        """Without camera population, dropdown only shows ALL_CAMERAS (the bug)."""
        from deadline.maya_submitter.cameras import ALL_CAMERAS
        from deadline.maya_submitter.data_classes import RenderSubmitterUISettings

        render_settings = RenderSubmitterUISettings()

        assert render_settings.all_layer_selectable_cameras == [ALL_CAMERAS]
        assert render_settings.current_layer_selectable_cameras == [ALL_CAMERAS]

    def test_cameras_single_layer(self):
        """With a single render layer, all its cameras appear in both modes."""
        from unittest.mock import patch

        from deadline.maya_submitter.cameras import ALL_CAMERAS
        from deadline.maya_submitter.data_classes import RenderSubmitterUISettings
        from deadline.maya_submitter.maya_render_submitter import _populate_selectable_cameras

        render_settings = RenderSubmitterUISettings()
        render_layers = [self._make_layer(["persp", "renderCam"])]

        with patch(
            "deadline.maya_submitter.maya_render_submitter.get_renderable_camera_names",
            return_value=["persp", "renderCam"],
        ):
            _populate_selectable_cameras(render_settings, render_layers)

        assert render_settings.all_layer_selectable_cameras == [
            ALL_CAMERAS,
            "persp",
            "renderCam",
        ]
        assert render_settings.current_layer_selectable_cameras == [
            ALL_CAMERAS,
            "persp",
            "renderCam",
        ]

    def test_cameras_sorted_alphabetically(self):
        """Camera names should be sorted alphabetically after ALL_CAMERAS."""
        from unittest.mock import patch

        from deadline.maya_submitter.cameras import ALL_CAMERAS
        from deadline.maya_submitter.data_classes import RenderSubmitterUISettings
        from deadline.maya_submitter.maya_render_submitter import _populate_selectable_cameras

        render_settings = RenderSubmitterUISettings()
        render_layers = [self._make_layer(["zebra_cam", "alpha_cam", "middle_cam"])]

        with patch(
            "deadline.maya_submitter.maya_render_submitter.get_renderable_camera_names",
            return_value=["zebra_cam", "alpha_cam", "middle_cam"],
        ):
            _populate_selectable_cameras(render_settings, render_layers)

        assert render_settings.current_layer_selectable_cameras == [
            ALL_CAMERAS,
            "alpha_cam",
            "middle_cam",
            "zebra_cam",
        ]


class TestGuiSubmissionGlue:
    """Covers the GUI-boundary glue introduced by the BaseSubmitter refactor:
    the RenderSubmitterUISettings -> MayaSubmitterSettings adapter and the
    on_create_job_bundle_callback rewiring onto the stateful MayaSubmitter.
    These were previously untested; they are the pieces most changed by the
    refactor, so they guard against regressions in the GUI submission path.
    """

    @pytest.fixture(autouse=True)
    def mock_maya_modules(self):
        """Mock Maya modules so we can import deadline.maya_submitter.maya_render_submitter."""
        mocks = {
            "maya": Mock(),
            "maya.cmds": Mock(),
            "maya.mel": Mock(),
            "maya.app": Mock(),
            "maya.app.renderSetup": Mock(),
            "maya.app.renderSetup.model": Mock(),
            "maya.app.renderSetup.model.renderSetupPreferences": Mock(),
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
            "deadline.maya_submitter.submitter",
            "deadline.maya_submitter.maya_render_submitter",
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

    def test_ui_settings_to_submitter_settings_maps_all_fields(self):
        """The adapter maps every field from the GUI settings onto the headless
        settings — most importantly name -> job_name, and the LayerSelection enum
        and timeouts pass through unchanged.
        """
        from deadline.maya_submitter.cameras import ALL_CAMERAS
        from deadline.maya_submitter.data_classes import RenderSubmitterUISettings
        from deadline.maya_submitter.maya_render_submitter import (
            _ui_settings_to_submitter_settings,
        )
        from deadline.maya_submitter.render_layers import LayerSelection

        ui = RenderSubmitterUISettings()
        ui.name = "MyShot_v003"
        ui.description = "a description"
        ui.frame_list = "1-50"
        ui.project_path = "/proj"
        ui.output_path = "/proj/images"
        ui.priority = 60
        ui.initial_status = "SUSPENDED"
        ui.max_failed_tasks_count = 7
        ui.max_retries_per_task = 3
        ui.max_worker_count = 12
        ui.override_frame_range = True
        ui.input_filenames = ["/proj/scene.ma"]
        ui.input_directories = ["/proj"]
        ui.output_directories = ["/proj/images"]
        ui.render_layer_selection = LayerSelection.CURRENT
        ui.camera_selection = "renderCam"
        ui.include_adaptor_wheels = True

        result = _ui_settings_to_submitter_settings(ui)

        # name -> job_name (the one field that is renamed).
        assert result.job_name == "MyShot_v003"
        # Everything else maps by name.
        assert result.description == "a description"
        assert result.frame_list == "1-50"
        assert result.project_path == "/proj"
        assert result.output_path == "/proj/images"
        assert result.priority == 60
        assert result.initial_status == "SUSPENDED"
        assert result.max_failed_tasks_count == 7
        assert result.max_retries_per_task == 3
        assert result.max_worker_count == 12
        assert result.override_frame_range is True
        assert result.input_filenames == ["/proj/scene.ma"]
        assert result.input_directories == ["/proj"]
        assert result.output_directories == ["/proj/images"]
        # Enum passes through as the same LayerSelection value (not a str).
        assert result.render_layer_selection is LayerSelection.CURRENT
        assert result.camera_selection == "renderCam"
        assert result.include_adaptor_wheels is True
        # timeouts is carried over by reference (same object).
        assert result.timeouts is ui.timeouts
        # Sanity: default UI camera_selection is ALL_CAMERAS on both sides.
        assert RenderSubmitterUISettings().camera_selection == ALL_CAMERAS

    def test_ui_settings_copies_collections(self):
        """input/output collections must be copies, not aliases of the UI lists,
        so later mutation of the GUI settings can't bleed into the submitter settings.
        """
        from deadline.maya_submitter.data_classes import RenderSubmitterUISettings
        from deadline.maya_submitter.maya_render_submitter import (
            _ui_settings_to_submitter_settings,
        )

        ui = RenderSubmitterUISettings()
        ui.input_filenames = ["/a"]
        ui.input_directories = ["/b"]
        ui.output_directories = ["/c"]

        result = _ui_settings_to_submitter_settings(ui)
        ui.input_filenames.append("/leaked")

        assert result.input_filenames == ["/a"]
        assert result.input_filenames is not ui.input_filenames

    def test_on_create_job_bundle_callback_drives_one_submitter(self):
        """The callback must: build MayaSubmitterSettings via the adapter, call
        get_job_template + get_parameter_values on a SINGLE MayaSubmitter instance
        (query-once), and write the three bundle YAML files.
        """
        from unittest.mock import MagicMock, mock_open, patch

        from deadline.maya_submitter import maya_render_submitter as mrs
        from deadline.maya_submitter.data_classes import RenderSubmitterUISettings

        settings = RenderSubmitterUISettings()
        settings.name = "job"

        # One submitter instance with a pre-built (empty) scene context so no scan runs.
        submitter_instance = MagicMock()
        submitter_instance.scene_context.current_layer_selectable_cameras = []
        submitter_instance.scene_context.all_layer_selectable_cameras = []
        submitter_instance.get_job_template.return_value = {"steps": []}
        submitter_instance.get_parameter_values.return_value = [{"name": "Frames", "value": "1"}]

        widget = MagicMock()
        widget.job_attachments.attachments.input_filenames = []
        widget.job_attachments.attachments.input_directories = []
        widget.job_attachments.attachments.output_directories = []
        asset_references = MagicMock()

        with (
            patch.object(mrs, "MayaSubmitter", return_value=submitter_instance) as mock_cls,
            patch.object(mrs, "_set_render_setting", return_value=RenderSubmitterUISettings()),
            patch.object(mrs, "deadline_yaml_dump") as mock_dump,
            patch.object(mrs, "open", mock_open(), create=True),
            patch.object(mrs, "Scene") as scene_mock,
            # Sticky-settings persistence writes to disk; not what this test
            # verifies, so stub it (patch.object avoids mypy's method-assign error).
            patch.object(RenderSubmitterUISettings, "save_sticky_settings"),
        ):
            scene_mock.name.return_value = "/proj/scene.ma"
            # Not a submission-purpose modified-scene prompt: report unmodified.
            mrs.maya.cmds.file.return_value = 0
            result = mrs.on_create_job_bundle_callback(
                widget=widget,
                job_bundle_dir="/tmp/bundle",
                settings=settings,
                queue_parameters=[],
                asset_references=asset_references,
            )

        # Exactly one MayaSubmitter constructed (query-once).
        mock_cls.assert_called_once_with()
        # Both builders called on that same instance.
        assert submitter_instance.get_job_template.call_count == 1
        assert submitter_instance.get_parameter_values.call_count == 1
        # The settings handed to the builders are the adapted MayaSubmitterSettings.
        passed_settings = submitter_instance.get_job_template.call_args.args[0]
        assert passed_settings.job_name == "job"
        # Three bundle files written (template, parameter_values, asset_references).
        assert mock_dump.call_count == 3
        # Return payload carries the parameter values.
        assert result["job_parameters"] == [{"name": "Frames", "value": "1"}]
