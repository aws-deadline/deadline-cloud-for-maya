# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Iterator, Optional

import maya.cmds

"""
Functionality used for querying scene settings
"""


class RendererNames(Enum):
    """
    A collection of supported renderers and their respective name.
    Values for each enum are the string Maya returns for the given renderer.
    """

    mayaSoftware = "mayaSoftware"
    arnold = "arnold"
    vray = "vray"
    renderman = "renderman"


class Animation:
    """
    Functionality for retrieving Animation related settings from the active Maya Scene
    """

    @staticmethod
    def current_frame() -> int:
        """
        Returns the current frame number from Maya.
        """
        return int(maya.cmds.currentTime(query=True))

    @staticmethod
    def start_frame() -> int:
        """
        Returns the start frame for the scenes render
        """
        return int(maya.cmds.getAttr("defaultRenderGlobals.startFrame"))

    @staticmethod
    def end_frame() -> int:
        """
        Returns the End frame for the scenes Render
        """
        return int(maya.cmds.getAttr("defaultRenderGlobals.endFrame"))

    @staticmethod
    def frame_step() -> int:
        """
        Returns the frame step of the current render.
        """
        return int(maya.cmds.getAttr("defaultRenderGlobals.byFrame"))

    @staticmethod
    def extension_padding() -> int:
        """
        Returns the amount that frames are padded by in the output file name.
        """
        return maya.cmds.getAttr("defaultRenderGlobals.extensionPadding")

    @classmethod
    def frame_list(cls) -> "FrameRange":
        """
        Returns a FrameRange object representing the full framelist.
        """
        if maya.cmds.getAttr("defaultRenderGlobals.animation"):
            return FrameRange(start=cls.start_frame(), stop=cls.end_frame(), step=cls.frame_step())
        else:
            return FrameRange(start=cls.current_frame())


class Scene:
    """
    Functionality for retrieving settings from the active scene
    """

    @staticmethod
    def ensure_arnold_options_loaded() -> None:
        try:
            maya.cmds.listAttr("defaultArnoldRenderOptions")
        except ValueError:
            try:
                from mtoa.core import createOptions

                createOptions()  # defaultArnoldRenderOptions are not created until this is called
            except ModuleNotFoundError:
                # This shouldn't be possible but we should handle it in case a customer figures out
                # a way of loading an arnold scene without mtoa
                maya.cmds.confirmDialog(
                    title="mtoa not loaded",
                    message=(
                        "Renderer is set to Arnold but mtoa is not loaded. Please load the mtoa "
                        "plugin before continuing to ensure all assets are submitted."
                    ),
                )

    @staticmethod
    def name() -> str:
        """
        Returns the full path to the Active Scene
        """
        return maya.cmds.file(query=True, sceneName=True)

    @staticmethod
    def renderer() -> str:
        """
        Returns the name of the current renderer as defined in the scene
        """
        return maya.cmds.getAttr("defaultRenderGlobals.currentRenderer")

    @staticmethod
    def get_output_directories(layer_name: str, camera_name: str) -> list[str]:
        """
        Returns a list of directories files will be output to.
        """
        image_paths = maya.cmds.renderSettings(
            firstImageName=True, fullPath=True, layer=layer_name, camera=camera_name
        )
        return [os.path.dirname(path) for path in image_paths]

    @staticmethod
    def project_path() -> str:
        """
        Returns the base path to the project the current scene is in
        """
        return maya.cmds.workspace(query=True, directory=True)

    @staticmethod
    def output_path() -> str:
        """
        Returns the path to the default output directory.
        """
        # This one didn't work translated to the maya.cmds equivalent
        image_rule = maya.mel.eval('workspace -q -fileRuleEntry "images"')
        if image_rule:
            return os.path.join(maya.cmds.workspace(query=True, directory=True), image_rule)
        else:
            return maya.cmds.workspace(query=True, directory=True)

    @staticmethod
    def autotx() -> bool:
        """
        Returns True if Arnold auto - converts textures to TX
        """
        if Scene.renderer() == RendererNames.arnold.value:
            Scene.ensure_arnold_options_loaded()
            return maya.cmds.getAttr("defaultArnoldRenderOptions.autotx")
        else:
            return False

    @staticmethod
    def use_existing_tiled_textures() -> bool:
        """
        Returns True if Arnold uses existing TX textures
        """
        if Scene.renderer() == RendererNames.arnold.value:
            Scene.ensure_arnold_options_loaded()
            return maya.cmds.getAttr("defaultArnoldRenderOptions.use_existing_tiled_textures")
        else:
            return False

    @staticmethod
    def error_on_arnold_license_fail() -> bool:
        """
        Returns True if Arnold is set to fail render of licensing error, or the renderer
        is not Arnold.
        """
        if Scene.renderer() == RendererNames.arnold.value:
            Scene.ensure_arnold_options_loaded()
            return maya.cmds.getAttr("defaultArnoldRenderOptions.abortOnLicenseFail")
        else:
            return True

    @staticmethod
    def yeti_cache_files() -> list[str]:
        files = []
        nodes = maya.cmds.ls(type="pgYetiMaya")
        for node in nodes:
            cache_file = maya.cmds.getAttr("%s.cacheFileName" % node)
            if cache_file:
                files.append(cache_file)
        return files


@dataclass
class FrameRange:
    """
    Class used to represent a frame range.
    """

    start: int
    stop: Optional[int] = None
    step: Optional[int] = None

    def __repr__(self) -> str:
        if self.stop is None or self.stop == self.start:
            return str(self.start)

        if self.step is None or self.step == 1:
            return f"{self.start}-{self.stop}"

        return f"{self.start}-{self.stop}:{self.step}"

    def __iter__(self) -> Iterator[int]:
        stop: int = self.stop if self.stop is not None else self.start
        step: int = self.step if self.step is not None else 1

        return iter(range(self.start, stop + step, step))
