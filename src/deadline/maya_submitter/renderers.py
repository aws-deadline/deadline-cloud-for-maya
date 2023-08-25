# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

from collections import deque

import maya.cmds

from .cameras import get_renderable_camera_names
from .render_layers import get_all_renderable_render_layer_names

"""
Implementation of the Default Renderer object.
"""


class Resolution:
    """
    Default implementation of retrieving the Resolution from a renderer
    """

    @property
    def width(self) -> int:
        """
        Retrieves the width as currently specified
        """
        return maya.cmds.getAttr("defaultResolution.width")

    @property
    def height(self) -> int:
        """
        Retrieves the height as currently specified.
        """
        return maya.cmds.getAttr("defaultResolution.height")

    def plugin_settings(self) -> dict[str, int]:
        """
        Returns the Resolution Plugin settings
        """
        return {
            "image_width": self.width,
            "image_height": self.height,
        }


class OutputHandling:
    """
    Basic output file handling
    """

    layer_tokens = ("<Layer>", "<RenderLayer>", "%l")
    camera_tokens = ("<Camera>", "%c")

    @property
    def base_output_prefix(self):
        """
        Retrieves the output prefix as specified in the scene.
        """
        prefix = maya.cmds.getAttr("defaultRenderGlobals.imageFilePrefix")
        if prefix:
            return prefix
        return "<Scene>"

    @property
    def output_prefix_with_tokens(self):
        """
        Retrieves the Output Prefix adding in all missing tokens
        """
        prefix = self.base_output_prefix

        sections = deque(prefix.split("/"))

        if len(get_renderable_camera_names()) > 1 and not any(
            token in prefix for token in self.camera_tokens
        ):
            sections.appendleft("<Camera>")
        if len(get_all_renderable_render_layer_names()) > 1 and not any(
            token in prefix for token in self.layer_tokens
        ):
            sections.appendleft("<Layer>")

        return "/".join(sections)

    def plugin_settings(self):
        """
        Retrieves all output file related parameters
        """
        return {"output_file_prefix": self.output_prefix_with_tokens}


class Renderer:
    """
    A class used to represent the default Renderer object
    """

    def __init__(self, name):
        self.name = name
        self.resolution = Resolution()
        self.output = OutputHandling()

    def get_plugin_settings(self, _):
        """
        Returns a dictionary containing all plugin settings that the Renderer requires.
        """
        settings = {}
        settings.update(self.resolution.plugin_settings())
        settings.update(self.output.plugin_settings())
        return settings
