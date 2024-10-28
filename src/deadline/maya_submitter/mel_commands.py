# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Defines the Render submitter command which is registered in Maya.
"""
import maya.api.OpenMaya as om  # pylint: disable=import-error
import maya.cmds
from qtpy.QtCore import Qt  # type: ignore
from qtpy.QtWidgets import (  # type: ignore
    QApplication,
)

from deadline.client.ui import gui_error_handler
from . import logger as deadline_logger  # type: ignore
from .maya_render_submitter import show_maya_render_submitter
from .job_bundle_output_test_runner import run_maya_render_submitter_job_bundle_output_test


class DeadlineCloudSubmitterCmd(om.MPxCommand):
    """
    Class used to create the DeadlineCloudSubmitter Mel Command.
    """

    # Current submitter dialog if any
    dialog = None
    # Scene name at dialog's time of creation
    dialog_scene_name = None

    @staticmethod
    def doIt(_):  # pylint: disable=invalid-name,
        """
        Open the Maya Integrated Submitter
        """

        # Build the GUI if we are in UI mode
        if om.MGlobal.mayaState() in [om.MGlobal.kInteractive, om.MGlobal.kBaseUIMode]:
            # Get the main Maya window so we can parent the submitter to it
            app = QApplication.instance()
            mainwin = [
                widget for widget in app.topLevelWidgets() if widget.objectName() == "MayaWindow"
            ][0]
            with gui_error_handler("Error opening the Deadline Cloud Submitter", mainwin):
                logger = deadline_logger()

                logger.info("Opening AWS Deadline Cloud Submitter")
                scene_name = maya.cmds.file(query=True, sceneName=True)
                if not scene_name:
                    maya.cmds.confirmDialog(
                        title="Deadline Cloud Submitter",
                        message="The Maya Scene is not saved to disk. Please save it before opening the submitter dialog.",
                        button="OK",
                        defaultButton="OK",
                    )
                    return

                # Delete the dialog if the scene has changed
                if DeadlineCloudSubmitterCmd.dialog_scene_name != scene_name:
                    if DeadlineCloudSubmitterCmd.dialog:
                        DeadlineCloudSubmitterCmd.dialog.close()
                    DeadlineCloudSubmitterCmd.dialog = None

                # Show existing submitter dialog, or create new one if needed
                if DeadlineCloudSubmitterCmd.dialog:
                    DeadlineCloudSubmitterCmd.dialog.show()
                else:
                    DeadlineCloudSubmitterCmd.dialog = show_maya_render_submitter(
                        parent=mainwin, f=Qt.Tool
                    )
                    DeadlineCloudSubmitterCmd.dialog_scene_name = scene_name


class DeadlineCloudJobBundleOutputTestsCmd(om.MPxCommand):
    """
    Class used to create the DeadlineCloudJobBundleOutputTests Mel Command.
    """

    @staticmethod
    def doIt(_):  # pylint: disable=invalid-name,
        """
        Runs a set of job bundle output tests from a directory.
        """
        run_maya_render_submitter_job_bundle_output_test()
