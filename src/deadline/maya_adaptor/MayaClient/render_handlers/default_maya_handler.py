# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import maya.cmds
import maya.mel

from ..dir_map import DirectoryMapping


def _get_render_layer_display_name(render_layer_name: str) -> str:
    return maya.mel.eval(f'renderLayerDisplayName "{render_layer_name}"')


class DefaultMayaHandler:
    cameras: Optional[List[str]] = None
    render_kwargs: Dict[str, Any]

    def __init__(self):
        self.action_dict = {
            "start_render": self.start_render,
            "camera": self.set_camera,
            "image_height": self.set_image_height,
            "image_width": self.set_image_width,
            "output_file_path": self.set_output_file_path,
            "output_file_prefix": self.set_output_file_prefix,
            "path_mapping": self.set_path_mapping,
            "project_path": self.set_project_path,
            "render_layer": self.set_render_layer,
            "render_setup_include_lights": self.set_render_setup_include_lights,
            "scene_file": self.set_scene_file,
        }
        self.image_width = None
        self.image_height = None
        self.camera_name = None
        self.output_file_prefix = None
        self.render_kwargs = {}

    def get_camera_to_render(self, data: dict) -> list[str]:
        # The ls function returns all of the camera shapes, but the cameras themselves are represented by
        # the transform node which is the parent of the shape.
        camera_shape_names = maya.cmds.ls(cameras=True)
        camera_names = maya.cmds.listRelatives(camera_shape_names, parent=True)

        camera_name = data.get("camera", self.camera_name)
        if camera_name:
            if camera_name not in camera_names:
                raise RuntimeError(f"The specified camera, '{camera_name}', does not exist.")

            if not maya.cmds.getAttr(f"{camera_name}.renderable"):
                raise RuntimeError(f"The specified camera, '{camera_name}', is not renderable.")
        else:
            raise RuntimeError("No cameras was specified to render.")

        return camera_name

    def get_render_layer_to_render(self, data: dict) -> Optional[str]:
        display_name = data.get("render_layer")
        if display_name:
            # ignore referenced and disconnected layers
            render_manager = maya.cmds.ls("renderLayerManager")[0]
            render_layer_map = {
                _get_render_layer_display_name(name): name
                for name in maya.cmds.ls(type="renderLayer")
                if not maya.cmds.referenceQuery(name, isNodeReferenced=True)
                and maya.cmds.listConnections(name, t="renderLayerManager")[0] == render_manager
            }

            if display_name in render_layer_map:
                return render_layer_map[display_name]
            else:
                raise RuntimeError(
                    f"Error: Render layer '{display_name}' not found. Available render layers are: "
                    f"{sorted(render_layer_map.keys())}"
                )
        else:
            return None

    def start_render(self, data: dict) -> None:
        """
        Starts a render in the mayasoftware renderer.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['frame']
                Optional keys: ['camera']

        Raises:
            RuntimeError: If no camera was specified and no renderable camera was found
        """
        frame = data.get("frame")
        if frame is None:
            raise RuntimeError("MayaClient: start_render called without a frame number.")
        maya.cmds.setAttr("defaultRenderGlobals.startFrame", frame)
        maya.cmds.setAttr("defaultRenderGlobals.endFrame", frame)

        camera = self.get_camera_to_render(data)
        print(f"Rendering camera: {camera}", flush=True)

        # In order of preference, use the task's output_file_prefix, the step's output_file_prefix, or the scene file setting.
        output_file_prefix = data.get("output_file_prefix", self.output_file_prefix)
        if output_file_prefix:
            maya.cmds.setAttr(
                "defaultRenderGlobals.imageFilePrefix", output_file_prefix, type="string"
            )

        if self.image_width is not None:
            maya.cmds.setAttr("defaultResolution.width", self.image_width)
            print(f"Set image width to {self.image_width}", flush=True)
        if self.image_height is not None:
            maya.cmds.setAttr("defaultResolution.height", self.image_height)
            print(f"Set image height to {self.image_height}", flush=True)

        region = [
            data.get(field)
            for field in ("region_min_x", "region_max_x", "region_min_y", "region_max_y")
        ]
        if any(v is not None for v in region):
            raise RuntimeError(
                "MayaClient: A region render was specified, but region rendering support is not implemented for the selected renderer."
            )

        maya.cmds.render(camera, **self.render_kwargs)

        print(f"MayaClient: Finished Rendering Frame {frame}\n", flush=True)

    def set_camera(self, data: dict) -> None:
        """
        Sets the Camera that will be rendered.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['camera']

        Raises:
            RuntimeError: If the camera is not renderable or does not exist
        """
        self.camera_name = data.get("camera")

    def set_image_height(self, data: dict) -> None:
        """
        Sets the image height.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['image_height']
        """
        self.image_height = data.get("image_height")

    def set_image_width(self, data: dict) -> None:
        """
        Sets the image width.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['image_width']
        """
        self.image_width = data.get("image_width")

    def set_output_file_path(self, data: dict) -> None:
        """
        Sets the output file path.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['output_file_path']
        """
        render_dir = data.get("output_file_path")
        if render_dir:
            maya.cmds.workspace(fileRule=["images", render_dir])

    def set_output_file_prefix(self, data: dict) -> None:
        """
        Sets the output file prefix.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['output_file_prefix']
        """
        self.output_file_prefix = data.get("output_file_prefix")

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
            os.makedirs(path, exist_ok=True)
            maya.cmds.workspace(path, openWorkspace=True)
            maya.cmds.workspace(directory=path)

    def set_render_layer(self, data: dict) -> None:
        """
        Sets the render layer.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['render_layer']

        Raises:
            RuntimeError: If the render layer cannot be found
        """
        render_layer_name = self.get_render_layer_to_render(data)
        if render_layer_name:
            self.render_kwargs["layer"] = render_layer_name

    def set_render_setup_include_lights(self, data: dict) -> None:
        """
        Sets the renderSetup_includeAllLights flag.

        Args:
            data (dict): The data given from the Adaptor. Keys expected:
                ['render_setup_include_lights']
        """
        include_lights = data.get("render_setup_include_lights", True)
        maya.cmds.optionVar(intValue=("renderSetup_includeAllLights", int(include_lights)))

    def set_scene_file(self, data: dict):
        """Opens a scene file in maya.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['scene_file']

        Raises:
            FileNotFoundError: If the file provided in the data dictionary does not exist.
        """
        file_path = data.get("scene_file", "")
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"The scene file '{file_path}' does not exist")
        maya.cmds.file(file_path, open=True, force=True)

        pre_render_mel = maya.cmds.getAttr("defaultRenderGlobals.preMel")
        if pre_render_mel:
            try:
                maya.mel.eval(pre_render_mel)
            except Exception as e:
                print("Warning: preMel Failed: %s" % e)
