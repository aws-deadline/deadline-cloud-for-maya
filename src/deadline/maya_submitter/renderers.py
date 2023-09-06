# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

from collections import deque

import maya.cmds

from .cameras import get_renderable_camera_names
from .render_layers import get_all_renderable_render_layer_names


def get_width() -> int:
    """
    Retrieves the width as currently specified
    """
    return maya.cmds.getAttr("defaultResolution.width")


def get_height() -> int:
    """
    Retrieves the height as currently specified.
    """
    return maya.cmds.getAttr("defaultResolution.height")


_LAYER_TOKENS = ("<Layer>", "<RenderLayer>", "%l")
_CAMERA_TOKENS = ("<Camera>", "%c")


def _get_base_output_prefix():
    """
    Retrieves the output prefix as specified in the scene.
    """
    prefix = maya.cmds.getAttr("defaultRenderGlobals.imageFilePrefix")
    if prefix:
        return prefix
    return "<Scene>"


def get_output_prefix_with_tokens():
    """
    Retrieves the Output Prefix adding in all missing tokens
    """
    prefix = _get_base_output_prefix()

    sections = deque(prefix.split("/"))

    if len(get_renderable_camera_names()) > 1 and not any(
        token in prefix for token in _CAMERA_TOKENS
    ):
        sections.appendleft("<Camera>")
    if len(get_all_renderable_render_layer_names()) > 1 and not any(
        token in prefix for token in _LAYER_TOKENS
    ):
        sections.appendleft("<Layer>")

    return "/".join(sections)
