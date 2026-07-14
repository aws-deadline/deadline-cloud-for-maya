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


class TestCondaChannelHostRequirement:
    """Tests for _augment_host_requirements_for_conda_channel.

    The "deadline-cloud" conda channel only ships Linux Maya packages, so a job that
    relies solely on it must be constrained to Linux fleets.
    """

    @pytest.fixture(autouse=True)
    def mock_maya_modules(self):
        """Mock Maya modules so we can import the submitter module."""
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

    @staticmethod
    def _augment(queue_parameters, host_requirements=None):
        from deadline.maya_submitter.maya_render_submitter import (
            _augment_host_requirements_for_conda_channel,
        )

        return _augment_host_requirements_for_conda_channel(queue_parameters, host_requirements)

    def test_deadline_cloud_channel_adds_linux_requirement(self):
        """The exact 'deadline-cloud' channel adds a Linux OS host requirement."""
        result = self._augment([{"name": "CondaChannels", "value": "deadline-cloud"}], None)

        assert result == {"attributes": [{"name": "attr.worker.os.family", "anyOf": ["linux"]}]}

    def test_channel_read_from_default_when_no_value(self):
        """The channel is read from 'default' when no explicit 'value' is set."""
        result = self._augment([{"name": "CondaChannels", "default": "deadline-cloud"}], None)

        assert result == {"attributes": [{"name": "attr.worker.os.family", "anyOf": ["linux"]}]}

    def test_custom_channel_left_untouched(self):
        """A custom channel may carry Windows packages, so no OS constraint is added."""
        result = self._augment([{"name": "CondaChannels", "value": "my-custom-channel"}], None)

        assert result is None

    def test_deadline_cloud_with_extra_channel_left_untouched(self):
        """When extra channels are present we cannot assume Linux-only, so leave it alone."""
        result = self._augment(
            [{"name": "CondaChannels", "value": "deadline-cloud conda-forge"}], None
        )

        assert result is None

    def test_no_conda_channels_parameter_left_untouched(self):
        """Without a CondaChannels parameter, host requirements are unchanged."""
        sentinel = {"attributes": [{"name": "attr.worker.os.family", "anyOf": ["windows"]}]}
        result = self._augment([{"name": "RezPackages", "value": "foo"}], sentinel)

        assert result is sentinel

    def test_merges_into_existing_host_requirements_without_mutating(self):
        """Existing (non-OS) host requirements are preserved and the input isn't mutated."""
        existing = {"amounts": [{"name": "amount.worker.vcpu", "min": 4}]}
        result = self._augment([{"name": "CondaChannels", "value": "deadline-cloud"}], existing)

        assert result == {
            "amounts": [{"name": "amount.worker.vcpu", "min": 4}],
            "attributes": [{"name": "attr.worker.os.family", "anyOf": ["linux"]}],
        }
        # The caller-owned dict must not be mutated.
        assert "attributes" not in existing

    def test_intersects_existing_os_constraint_to_linux(self):
        """An existing OS anyOf that includes linux is narrowed to linux only."""
        existing = {
            "attributes": [
                {"name": "attr.worker.os.family", "anyOf": ["linux", "windows"]},
            ]
        }
        result = self._augment([{"name": "CondaChannels", "value": "deadline-cloud"}], existing)

        assert result == {"attributes": [{"name": "attr.worker.os.family", "anyOf": ["linux"]}]}

    def test_leaves_windows_only_constraint_alone(self):
        """If the user explicitly required windows-only (no linux), we don't widen it."""
        existing = {
            "attributes": [
                {"name": "attr.worker.os.family", "anyOf": ["windows"]},
            ]
        }
        result = self._augment([{"name": "CondaChannels", "value": "deadline-cloud"}], existing)

        # The job will not match any fleet, but that's the user's explicit choice;
        # we never silently widen a constraint they set.
        assert result == {"attributes": [{"name": "attr.worker.os.family", "anyOf": ["windows"]}]}
