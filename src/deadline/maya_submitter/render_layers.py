# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Functionality for interacting with Maya's Render Layers
"""
from contextlib import contextmanager
from enum import IntEnum
from typing import List

import maya.cmds
import maya.mel

# DEFAULT_LAYER_NAME = "defaultRenderLayer"
# DEFAULT_LAYER_DISPLAY_NAME = "masterLayer"


class LayerSelection(IntEnum):
    """Enum used for determining how to retrieve render layers"""

    ALL = 1
    CURRENT = 2


def get_all_renderable_render_layer_names() -> List[str]:
    render_layer_names = maya.cmds.ls(type="renderLayer")
    # Filter out any render layers that are referenced in other files,
    # because they cannot be set as the current render layer.

    # ignore referenced and disconnected layers
    render_manager = maya.cmds.ls("renderLayerManager")[0]
    render_layer_names = [
        name
        for name in render_layer_names
        if not maya.cmds.referenceQuery(name, isNodeReferenced=True)
        and maya.cmds.listConnections(name, t="renderLayerManager")[0] == render_manager
    ]

    # Filter out any non-renderable layers
    render_layer_names = [name for name in render_layer_names if is_render_layer_renderable(name)]
    return render_layer_names


def get_current_render_layer_name() -> str:
    return maya.cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True)


def set_current_render_layer(render_layer_name: str) -> None:
    maya.cmds.editRenderLayerGlobals(currentRenderLayer=render_layer_name)


def is_render_layer_renderable(render_layer_name: str) -> bool:
    return maya.cmds.getAttr(f"{render_layer_name}.renderable")


def get_render_layer_display_name(render_layer_name) -> str:
    """
    Returns the external name of the render layer.
    """
    return maya.mel.eval(f'renderLayerDisplayName "{render_layer_name}"')


def render_setup_include_all_lights() -> bool:
    """
    Returns whether a Render Layer should contain all lights in the scene automatically
    (machine level setting)
    """
    # The maya.cmds.optionVar query did not work
    return bool(maya.mel.eval("optionVar -q renderSetup_includeAllLights"))


@contextmanager
def saved_current_render_layer():
    """
    Saves and restores the current render layer.
    """
    saved_render_layer_name = get_current_render_layer_name()
    yield
    set_current_render_layer(saved_render_layer_name)
