# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Implementation of the Default Renderer object.
"""
import os
from collections import deque
from typing import Dict, List, Type

import pymel.core as pmc  # pylint: disable=import-error

from ..cameras import Camera
from ..render_layers import RenderLayer
from ..scene import Scene

__renderer_map: Dict[str, Type["Renderer"]] = {}


def current_renderer() -> "Renderer":
    """
    Returns a Renderer object for the currently selected renderer.
    """
    renderer_name = Scene.renderer()

    try:
        return __renderer_map[renderer_name](name=renderer_name)
    except KeyError:
        return Renderer(renderer_name)


class Resolution:
    """
    Default implementation of retrieving the Resolution from a renderer
    """

    def __init__(self):
        self._res = pmc.SCENE.defaultRenderGlobals.resolution.get()

    @property
    def width(self) -> int:
        """
        Retrieves the width as currently specified
        """
        return self._res.width.get()

    @property
    def height(self) -> int:
        """
        Retrieves the height as currently specified.
        """
        return self._res.height.get()

    def plugin_settings(self) -> Dict[str, int]:
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
        prefix = pmc.SCENE.defaultRenderGlobals.imageFilePrefix.get()
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

        if Camera.multiple_renderable() and not any(
            token in prefix for token in self.camera_tokens
        ):
            sections.appendleft("<Camera>")
        if RenderLayer.scene_contains_multiple() and not any(
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

    @staticmethod
    def get_output_directories(layer_name: str, camera_name: str) -> List[str]:
        """
        Returns a list of directories files will be output to.
        """
        render_settings = pmc.rendering.renderSettings(
            firstImageName=True, fullPath=True, layer=layer_name, camera=camera_name
        )
        base_output_file_name = render_settings[0]
        output_directory = os.path.dirname(base_output_file_name)

        output_directories: List[str] = []
        output_directories.append(output_directory)

        return output_directories
