# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Functionality which contains all Commands that will be added to Maya.
"""
from typing import TYPE_CHECKING, List, Type

if TYPE_CHECKING:
    import maya.api.OpenMaya as om  # pylint: disable=import-error

from . import renderSubmitter

__all__ = ["get_commands"]
__cmds__ = [renderSubmitter.RenderSubmitterCmd]


def get_commands() -> "List[Type[om.MPxCommand]]":
    """
    Return a list of commands
    """
    return __cmds__
