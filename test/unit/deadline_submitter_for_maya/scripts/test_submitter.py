# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
from unittest.mock import Mock


def test_frame_override_has_text_validation():
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

        sys.modules["qtpy.QtWidgets"] = mock_q_widgets
        mock_q_widgets.QWidget = MockQWidget
        mock_q_widgets.QLineEdit = mock_line_edit

        # Reload SceneSettingsWidget with the new mocks in place.
        del sys.modules["deadline.maya_submitter.ui.components.scene_settings_tab"]
        from deadline.maya_submitter.ui.components.scene_settings_tab import SceneSettingsWidget

        # Stub out a method
        SceneSettingsWidget._configure_settings = Mock()  # type: ignore
        SceneSettingsWidget._fill_cameras_box = Mock()  # type: ignore

        # Create the scene widget
        SceneSettingsWidget(initial_settings=Mock())

        # Verify that the validator was set on the frame override line edit
        assert mock_line_edit.return_value.setValidator.call_count == 1
        # Make sure the mock is working and there's at least 1 call (because there's at least 1 line edit element)
        assert mock_line_edit.call_count > 0

    finally:
        # Reset QtWidgets mock
        sys.modules["qtpy.QtWidgets"] = Mock()
