# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Defines the Render submitter command which is registered in Maya.
"""
import dataclasses
import json
import traceback
from typing import Optional

import maya.api.OpenMaya as om  # pylint: disable=import-error
import pymel.core as pmc  # pylint: disable=import-error

from .. import Scene  # type: ignore
from .. import logger as deadline_logger  # type: ignore
from ..data_classes.render_submitter_settings import (
    RenderSubmitterSettings,
    RenderSubmitterUISettings,
)
from ..persistent_dataclass import PersistentDataclassError
from .maya_render_submitter import show_maya_render_submitter


class RenderSubmitterCmd(om.MPxCommand):
    """
    Class used to create the DeadlineRenderSubmitter Mel Command.
    """

    name = "DeadlineRenderSubmitter"

    def __init__(self):
        om.MPxCommand.__init__(self)

    @staticmethod
    def cmdCreator() -> "RenderSubmitterCmd":  # pylint: disable=invalid-name
        """Returns an instance of this class."""
        return RenderSubmitterCmd()

    @staticmethod
    def doIt(_):  # pylint: disable=invalid-name,
        """
        Open the Maya Integrated Submitter
        """

        # Build the GUI if we are in UI mode
        if om.MGlobal.mayaState() in [om.MGlobal.kInteractive, om.MGlobal.kBaseUIMode]:
            logger = deadline_logger()

            logger.info("Opening Amazon Deadline Cloud Submitter")
            if not Scene.name():
                logger.warning("Scene has not been saved.")

            maybe_rs_settings: Optional[RenderSubmitterSettings] = None
            try:
                maybe_rs_settings = RenderSubmitterSettings.load()
            except PersistentDataclassError:
                traceback.print_exc()

            rs_settings: RenderSubmitterUISettings = RenderSubmitterUISettings()
            if maybe_rs_settings:
                rs_settings.apply_saved_settings(maybe_rs_settings)

            # Since we're using Maya Python API 2.0, this return value will always be wrapped in a list
            # Consumers of this command will need to unpack the return value from this list
            om.MPxCommand.setResult(json.dumps(dataclasses.asdict(rs_settings)))

            main_window = pmc.ui.Window("MayaWindow").asQtObject()
            show_maya_render_submitter(parent=main_window, render_settings=rs_settings)
