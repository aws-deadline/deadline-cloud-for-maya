# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from .default_maya_handler import DefaultMayaHandler
from .arnold_handler import ArnoldHandler
from .vray_handler import VRayHandler
from .renderman_handler import RenderManHandler

__all__ = ["DefaultMayaHandler", "get_render_handler"]


def get_render_handler(renderer: str = "mayaSoftware") -> DefaultMayaHandler:
    """
    Returns the render handler instance for the given renderer.

    Args:
        renderer (str, optional): The renderer to get the render handler of.
            Defaults to "mayaSoftware".

    Returns the Render Handler instance for the given renderer.
    """
    if renderer == "arnold":
        return ArnoldHandler()
    elif renderer == "vray":
        return VRayHandler()
    elif renderer == "renderman":
        return RenderManHandler()
    else:
        return DefaultMayaHandler()
