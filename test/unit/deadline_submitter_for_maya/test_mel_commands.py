# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from unittest.mock import patch, Mock
import maya.api.OpenMaya as om  # pylint: disable=import-error
from qtpy.QtCore import Qt  # type: ignore
from qtpy.QtWidgets import (  # type: ignore
    QApplication,
)


@patch.object(QApplication, "instance")
@patch.object(om.MGlobal, "mayaState")
def test_deadline_cloud_submitter_cmd_sticky_setting_loaded_on_every_open(
    mock_maya_state: Mock,
    mock_q_app: Mock,
) -> None:
    # Import mel_commands fresh and patch its attributes by object, not by string
    # path. Other test modules on the same xdist worker pop/reload
    # deadline.maya_submitter.mel_commands (and maya_render_submitter) from
    # sys.modules; binding DeadlineCloudSubmitterCmd / patching by dotted path at
    # module-import time can therefore target a stale module object, making the
    # patch miss and show_maya_render_submitter appear "called 0 times". Resolving
    # the module inside the test keeps the patch and the class in sync.
    from deadline.maya_submitter import mel_commands

    mock_maya_state.return_value = om.MGlobal.kInteractive
    maya_widget: Mock = Mock()
    maya_widget.objectName.return_value = "MayaWindow"
    q_app_instance: Mock = Mock()
    q_app_instance.topLevelWidgets.return_value = [maya_widget]
    mock_q_app.return_value = q_app_instance
    submitter_dialog: Mock = Mock()

    with (
        patch.object(mel_commands, "show_maya_render_submitter") as mock_show,
        patch.object(mel_commands, "check_and_show_update_dialog", return_value=False),
        # doIt() early-returns unless maya.cmds.file(query=True, sceneName=True)
        # returns a truthy scene name. maya.cmds is a shared module-level mock that
        # other test modules replace/reset across xdist workers, so pin file() here
        # to a real path — otherwise its default mock return can be falsy and the
        # command returns before ever calling show_maya_render_submitter.
        patch.object(mel_commands.maya.cmds, "file", return_value="/tmp/scene.ma"),
    ):
        mock_show.return_value = submitter_dialog

        mel_commands.DeadlineCloudSubmitterCmd.doIt(Mock())

        mock_show.assert_called_once_with(parent=maya_widget, f=Qt.Tool, load_sticky_setting=True)

        mel_commands.DeadlineCloudSubmitterCmd.doIt(Mock())

        mock_show.assert_called_with(parent=maya_widget, f=Qt.Tool, load_sticky_setting=True)
        submitter_dialog.close.assert_called_once()
