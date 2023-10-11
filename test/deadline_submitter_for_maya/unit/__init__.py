# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
from unittest.mock import MagicMock, Mock

# we must mock maya and UI code
mock_modules = [
    "maya",
    "maya.api",
    "maya.api.OpenMaya",
    "maya.app.renderSetup.model.renderSetupPreferences",
    "maya.app.general.fileTexturePathResolver",
    "maya.app.general.mayaMixin",
    "maya.OpenMaya",
    "maya.cmds",
    "maya.utils",
    "PySide2",
    "PySide2.QtCore",
    "PySide2.QtGui",
    "PySide2.QtWidgets",
    "mtoa.core",
    "deadline.maya_submitter.ui.render_submitter",
]

for module in mock_modules:
    sys.modules[module] = MagicMock()

# Mock the call to DeadlineCredentialsStatus.getInstance that happens at the module level
# in submit_job_to_deadline_dialog.py. That call is done at the module level to gather the
# status before the dialog is opened.
from deadline.client.ui.deadline_credentials_status import DeadlineCredentialsStatus

DeadlineCredentialsStatus.getInstance = Mock(return_value=None)


def configure_mocks():
    """Any extra mocking set up required"""
    configure_mpxcommand()


def configure_mpxcommand():
    """
    We use MPxCommand as a baseclass for a few classes, this function changes the MPxCommand class
    to not be the default MagicMock created since that causes issues testing the implemented
    functions in the superclass.
    """
    import maya.api.OpenMaya as om

    class MockClass:
        def __init__(self):
            super().__init__()

        def setResult(_):
            return None

    om.MPxCommand = MockClass


configure_mocks()
