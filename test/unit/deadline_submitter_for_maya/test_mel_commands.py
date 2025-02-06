# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from deadline.maya_submitter.mel_commands import DeadlineCloudSubmitterCmd
from unittest.mock import patch, Mock
import maya.api.OpenMaya as om  # pylint: disable=import-error
from qtpy.QtCore import Qt  # type: ignore
from qtpy.QtWidgets import (  # type: ignore
    QApplication,
)


@patch("deadline.maya_submitter.mel_commands.show_maya_render_submitter")
@patch.object(QApplication, "instance")
@patch.object(om.MGlobal, "mayaState")
def test_deadline_cloud_submitter_cmd_sticky_setting_load_only_once(
    mock_maya_state: Mock, mock_q_app: Mock, mock_show_maya_render_submitter: Mock
) -> None:
    mock_maya_state.return_value = om.MGlobal.kInteractive
    maya_widget: Mock = Mock()
    maya_widget.objectName.return_value = "MayaWindow"
    q_app_instance: Mock = Mock()
    q_app_instance.topLevelWidgets.return_value = [maya_widget]
    mock_q_app.return_value = q_app_instance
    submitter_dialog: Mock = Mock()
    mock_show_maya_render_submitter.return_value = submitter_dialog

    DeadlineCloudSubmitterCmd.doIt(Mock())

    mock_show_maya_render_submitter.assert_called_once_with(
        parent=maya_widget, f=Qt.Tool, load_sticky_setting=True
    )

    DeadlineCloudSubmitterCmd.doIt(Mock())

    mock_show_maya_render_submitter.assert_called_with(
        parent=maya_widget, f=Qt.Tool, load_sticky_setting=False
    )
    submitter_dialog.close.assert_called_once()
