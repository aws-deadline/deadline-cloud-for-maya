# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from collections import defaultdict as _defaultdict

from .arnold_handler import ArnoldHandler as _ArnoldHandler
from .maya_handler_base import MayaHandlerBase as _MayaHandlerBase
from .render_handler_interface import RenderHandlerInterface as _RenderHandlerInterface

renderers = _defaultdict(
    lambda: _MayaHandlerBase,
    {
        "mayaSoftware": _MayaHandlerBase,
        "arnold": _ArnoldHandler,
    },
)


def get_render_handler(renderer: str = "mayaSoftware") -> _RenderHandlerInterface:
    """
    Returns the render handler instance for the given renderer.

    Args:
        renderer (str, optional): The renderer to get the render handler of.
            Defaults to "mayaSoftware".

    Returns:
        _RenderHandlerInterface: The Render Handler instance for the given renderer
    """
    return renderers[renderer]()
