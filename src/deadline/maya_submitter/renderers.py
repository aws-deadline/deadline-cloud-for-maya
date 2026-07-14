# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

from collections import deque

import maya.cmds

from .cameras import get_renderable_camera_names
from .render_layers import get_all_renderable_render_layer_names
from .scene import RendererNames


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

# The attribute most renderers read for the output file name prefix.
_DEFAULT_PREFIX_ATTRIBUTE = "defaultRenderGlobals.imageFilePrefix"

# Renderers that store their output file name prefix somewhere other than
# defaultRenderGlobals.imageFilePrefix. V-Ray's Render Settings Common tab
# writes the "File Name Prefix" field to vraySettings.fileNamePrefix and does
# not update the legacy defaultRenderGlobals attribute, so reading the default
# attribute for a V-Ray scene picks up a stale/empty value and the submitted
# job ignores the prefix the user actually configured.
_RENDERER_PREFIX_ATTRIBUTES = {
    RendererNames.vray.value: "vraySettings.fileNamePrefix",
}


def _get_prefix_attribute() -> str:
    """
    Returns the attribute holding the output file name prefix for the scene's
    current renderer, falling back to the default attribute when the
    renderer-specific node is unavailable.
    """
    renderer = maya.cmds.getAttr("defaultRenderGlobals.currentRenderer")
    prefix_attribute = _RENDERER_PREFIX_ATTRIBUTES.get(renderer, _DEFAULT_PREFIX_ATTRIBUTE)

    # Guard against the renderer-specific node not existing (e.g. the plugin
    # isn't loaded yet). Without this, getAttr would raise during submission.
    node = prefix_attribute.split(".", 1)[0]
    if not maya.cmds.objExists(node):
        return _DEFAULT_PREFIX_ATTRIBUTE

    return prefix_attribute


def _get_base_output_prefix():
    """
    Retrieves the output prefix as specified in the scene.
    """
    prefix = maya.cmds.getAttr(_get_prefix_attribute())
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
