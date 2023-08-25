# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
from unittest.mock import MagicMock

# we must mock maya, pymel, and UI code
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
    "pymel",
    "pymel.core",
    "pymel.core.general",
    "pymel.core.nodetypes",
    "pymel.core.uitypes",
    "pymel.internal.pmcmds",
    "pymel.mayautils",
    "pymel.util",
    "PySide2",
    "PySide2.QtCore",
    "PySide2.QtGui",
    "PySide2.QtWidgets",
    "mtoa.core",
    "deadline_submitter_for_maya.scripts.aws_deadline.ui.render_submitter",
]

for module in mock_modules:
    sys.modules[module] = MagicMock()


def configure_mocks():
    """Any extra mocking set up required"""
    configure_mpxcommand()
    configure_filerules_get()


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


def configure_filerules_get():
    """
    RenderSubmitterSettings initializes its default values on import.
    This involves evaulating Scene.output_path().
    This makes a call to pymel.core.workspace.fileRules.get.
    Because pymel.core is mocked out, an attempted call to this method
    will evaluate to a MagicMock.
    This is a problem because the method then calls os.path.isabs on that
    MagicMock which raises an exception which breaks the tests
    Because this happens when the renderSubmitter module is imported we cannot
    create a special case to work around this in individual tests and must
    do it here.
    """
    import pymel.core as pmc

    pmc.workspace.fileRules.get.return_value = None


configure_mocks()
