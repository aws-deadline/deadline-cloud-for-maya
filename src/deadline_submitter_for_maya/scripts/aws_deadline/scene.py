# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Functionality used for querying scene settings
"""
import os
from dataclasses import dataclass
from enum import Enum
from typing import Iterator, Optional

import pymel.core as pmc  # pylint: disable=import-error

SCENE_REF = pmc.SCENE


class RendererNames(Enum):
    """
    A collection of supported renderers and their respective name.
    Values for each enum are the string Maya returns for the given renderer.
    """

    mayaSoftware = "mayaSoftware"
    arnold = "arnold"


class Animation:
    """
    Functionality for retrieving Animation related settings from the active Maya Scene
    """

    @staticmethod
    def activated() -> bool:
        """
        Returns whether or not Animation is activated in the scene
        """
        return SCENE_REF.defaultRenderGlobals.animation.get()

    @staticmethod
    def current_frame() -> int:
        """
        Returns the current frame number from Maya.
        """
        return int(pmc.getCurrentTime())

    @staticmethod
    def start_frame() -> int:
        """
        Returns the start frame for the scenes render
        """
        return int(SCENE_REF.defaultRenderGlobals.startFrame.get())

    @staticmethod
    def end_frame() -> int:
        """
        Returns the End frame for the scenes Render
        """
        return int(SCENE_REF.defaultRenderGlobals.endFrame.get())

    @staticmethod
    def frame_step() -> int:
        """
        Returns the frame step of the current render.
        """
        return int(SCENE_REF.defaultRenderGlobals.byFrameStep.get())

    @staticmethod
    def extension_padding() -> int:
        """
        Returns the amount that frames are padded by in the output file name.
        """
        return SCENE_REF.defaultRenderGlobals.extensionPadding.get()

    @classmethod
    def frame_list(cls) -> "FrameRange":
        """
        Retursn a FrameRange object representing the full framelist.
        """
        if not cls.activated():
            return FrameRange(start=cls.current_frame())

        return FrameRange(start=cls.start_frame(), stop=cls.end_frame(), step=cls.frame_step())


class Scene:
    """
    Functionality for retrieving settings from the active scene
    """

    Animation = Animation()

    @staticmethod
    def name() -> str:
        """
        Returns the full path to the Active Scene
        """
        return str(pmc.sceneName())

    @staticmethod
    def renderer() -> str:
        """
        Returns the name of the current renderer as defined in the scene
        """
        return SCENE_REF.defaultRenderGlobals.currentRenderer.get()

    @staticmethod
    def project_path() -> str:
        """
        Returns the base path to the project the current scene is in
        """
        return str(pmc.workspace.path)

    @staticmethod
    def output_path() -> str:
        """
        Returns the path to the default output directory.
        """
        image_rule = pmc.workspace.fileRules.get("images")
        if not image_rule:
            return str(pmc.workspace.path)

        if os.path.isabs(image_rule):
            return str(image_rule)

        return str(pmc.workspace.path / image_rule)

    @staticmethod
    def autotx() -> bool:
        """
        Returns True if Arnold auto - converts textures to TX
        """
        if Scene.renderer() != RendererNames.arnold.value:
            return False
        arnold_options = Scene._get_arnold_options()
        return arnold_options.autotx.get() if arnold_options else False

    @staticmethod
    def use_existing_tiled_textures() -> bool:
        """
        Returns True if Arnold uses existing TX textures
        """
        if Scene.renderer() != RendererNames.arnold.value:
            return False
        arnold_options = Scene._get_arnold_options()
        return arnold_options.use_existing_tiled_textures.get() if arnold_options else False

    @staticmethod
    def error_on_arnold_license_fail() -> bool:
        """
        Returns True if Arnold is set to fail render of licensing error
        """
        if Scene.renderer() != RendererNames.arnold.value:
            return False
        arnold_options = Scene._get_arnold_options()
        return arnold_options.abortOnLicenseFail.get() if arnold_options else True

    @staticmethod
    def _get_arnold_options() -> "Optional[pmc.nodetypes.AiOptions]":
        """_summary_

        Returns:
            pmc.nodetypes.AiOptions: The Default Arnold Render Options

        Raises:
            ModuleNotFoundError: When mtoa cannot be imported.
        """
        try:
            return SCENE_REF.defaultArnoldRenderOptions
        except pmc.MayaNodeError:
            try:
                from mtoa.core import createOptions  # type: ignore

                createOptions()  # defaultArnoldRenderOptions does not exist unless we call this.
            except ModuleNotFoundError:
                # This shouldn't be possible but we should handle it in case a customer figures out
                # a way of loading an arnold scene without mtoa
                pmc.confirmDialog(
                    title="mtoa not loaded",
                    message=(
                        "Renderer is set to Arnold but mtoa is not loaded. Please load the mtoa "
                        "plugin before continuing to ensure all assets are submitted."
                    ),
                )
                return None
        return SCENE_REF.defaultArnoldRenderOptions


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
