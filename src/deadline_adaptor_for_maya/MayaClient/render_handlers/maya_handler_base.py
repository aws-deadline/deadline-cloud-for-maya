# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import os as _os
from typing import TYPE_CHECKING as _TYPE_CHECKING
from typing import Any as _Any
from typing import Dict as _Dict
from typing import List as _List
from typing import Optional as _Optional

try:
    import pymel.core as pm

    from ..pymel_additions import DirectoryMapping

except ModuleNotFoundError:  # pragma: no cover
    raise OSError("Could not find the pymel module. Are you running this inside of MayaPy?")

from .render_handler_interface import RenderHandlerInterface as _RenderHandlerInterface

if _TYPE_CHECKING:
    from pymel.core.nodetypes import Camera, RenderLayer


class MayaHandlerBase(_RenderHandlerInterface):
    cameras: _Optional[_List] = None
    render_kwargs: _Dict[str, _Any]

    def __init__(self):
        super().__init__()
        self.render_kwargs = {}

    def start_render(self, data: dict) -> None:
        """
        Starts a render in the mayasoftware renderer.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['frame']

        Raises:
            RuntimeError: If no camera was specified and no renderable camera was found
        """
        frame = data.get("frame")
        if frame is None:
            raise RuntimeError("MayaClient: start_render called without a frame number.")
        pm.SCENE.defaultRenderGlobals.startFrame.set(frame)
        pm.SCENE.defaultRenderGlobals.endFrame.set(frame)

        if not self.cameras:
            print(
                "No camera was specified, defaulting to render on all renderable cameras.",
                flush=True,
            )
            self.cameras = [cam for cam in pm.ls(cameras=1) if cam.renderable.get()]
            if not self.cameras:
                raise RuntimeError(
                    "No camera was specified, and no renderable camera could be found."
                )
            else:
                print(f"Rendering on cameras: {[str(c) for c in self.cameras]}", flush=True)

        pm.render(self.cameras, **self.render_kwargs)
        print(f"MayaClient: Finished Rendering Frame {frame}\n", flush=True)

    def set_animation(self, data: dict) -> None:
        """
        Sets the Animation flag in maya

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['animation']
        """
        pm.SCENE.defaultRenderGlobals.animation.set(bool(data.get("animation", True)))

    def set_camera(self, data: dict) -> None:
        """
        Sets the Camera that will be renderered.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['camera']

        Raises:
            RuntimeError: If the camera is not renderable or does not exist
        """
        self.cameras = [self._find_camera(data)]

    def set_image_height(self, data: dict) -> None:
        """
        Sets the image height.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['image_height']
        """
        yresolution = int(data.get("image_height", 0))
        if yresolution:
            self.render_kwargs["yresolution"] = yresolution

    def set_image_width(self, data: dict) -> None:
        """
        Sets the image width.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['image_width']
        """
        xresolution = int(data.get("image_width", 0))
        if xresolution:
            self.render_kwargs["xresolution"] = xresolution

    def set_output_file_path(self, data: dict) -> None:
        """
        Sets the output file path.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['output_file_path']
        """
        render_dir = data.get("output_file_path")
        if render_dir:
            pm.workspace.fileRules["images"] = render_dir

    def set_output_file_prefix(self, data: dict) -> None:
        """
        Sets the output file prefix.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['output_file_prefix']
        """
        prefix = data.get("output_file_prefix")
        if prefix:
            pm.SCENE.defaultRenderGlobals.imageFilePrefix.set(prefix)

    def set_path_mapping(self, data: dict) -> None:
        """
        Sets Pathmapping rules within Maya

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['path_mapping_rules']
        """
        rules = data.get("path_mapping_rules", dict())
        if not rules:
            return

        DirectoryMapping.set_activated(True)
        for source, dest in rules.items():
            DirectoryMapping.mappings[source] = dest

    def set_project_path(self, data: dict) -> None:
        """
        Sets the project path.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['project_path']
        """
        path = data.get("project_path")
        if path:
            _os.makedirs(path, exist_ok=True)
            pm.workspace.open(path)

    def set_render_layer(self, data: dict) -> None:
        """
        Sets the render layer.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['render_layer']

        Raises:
            RuntimeError: If the render layer cannot be found
        """
        self.render_kwargs["layer"] = self._find_render_layer(data)

    def set_render_setup_include_lights(self, data: dict) -> None:
        """
        Sets the renderSetup_includeAllLights flag.

        Args:
            data (dict): The data given from the Adaptor. Keys expected:
                ['render_setup_include_lights']
        """
        include_lights = data.get("render_setup_include_lights", True)
        pm.optionVar["renderSetup_includeAllLights"] = int(include_lights)

    def set_scene_file(self, data: dict):
        """Opens a scene file in maya.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['scene_file']

        Raises:
            FileNotFoundError: If the file provided in the data dictionary does not exist.
        """
        file_path = data.get("scene_file", "")
        if not _os.path.isfile(file_path):
            raise FileNotFoundError(f"The scene file '{file_path}' does not exist")
        pm.openFile(file_path, force=True)

    def _find_camera(self, data: dict) -> Camera:
        """
        Finds the Camera that will be renderered.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['camera']

        Raises:
            RuntimeError: If the camera is not renderable or does not exist

        Returns:
            _type_: _description_
        """
        camera_name = data.get("camera")
        if not camera_name:
            raise RuntimeError("MayaClient: set_camera was called without providing a camera name.")

        for cam in pm.ls(cameras=1):
            if cam == camera_name or cam.getParent() == camera_name:
                if not cam.renderable.get():
                    raise RuntimeError(f"The camera '{camera_name}' is not renderable.")
                return cam
        else:
            raise RuntimeError(f"The camera '{camera_name}' does not exist.")

    def _find_render_layer(self, data: dict) -> RenderLayer:
        """
        Finds the render layer requested.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['render_layer']

        Raises:
            RuntimeError: If the render layer cannot be found
        """
        layer_name = data.get("render_layer")
        layer = next((rlayer for rlayer in pm.ls(type="renderLayer") if rlayer == layer_name), None)
        if layer:
            return layer
        else:
            raise RuntimeError(
                f"Error: Render layer '{layer_name}' not found. Available render layers are: "
                f"{pm.ls(type='renderLayer')}"
            )
