# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from .default_maya_handler import DefaultMayaHandler

import maya.cmds


class ArnoldHandler(DefaultMayaHandler):
    """Render Handler for Arnold"""

    def __init__(self):
        """
        Initializes the Arnold Renderer and Arnold Renderer Handler
        """
        super().__init__()
        self.action_dict["error_on_arnold_license_fail"] = self.set_error_on_arnold_license_fail
        self.render_kwargs["batch"] = True

    def start_render(self, data: dict) -> None:
        """
        Starts a render.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['frame']

        Raises:
            RuntimeError: If no camera was specified and no renderable camera was found. If a render region is partially specified.
        """
        frame = data.get("frame")
        if frame is None:
            raise RuntimeError("MayaClient: start_render called without a frame number.")
        self.render_kwargs["seq"] = frame

        self.render_kwargs["camera"] = self.get_camera_to_render(data)

        # In order of preference, use the task's output_file_prefix, the step's output_file_prefix, or the scene file setting.
        output_file_prefix = data.get("output_file_prefix", self.output_file_prefix)
        if output_file_prefix:
            maya.cmds.setAttr(
                "defaultRenderGlobals.imageFilePrefix", output_file_prefix, type="string"
            )
            print(f"Set imageFilePrefix to {output_file_prefix}", flush=True)

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
            region_str = f"(minX={region[0]}, maxX={region[1]}, minY={region[2]}, maxY={region[3]})"

            if any(v is None for v in region):
                raise RuntimeError(
                    f"MayaClient: Region bounds {region_str} must be fully defined or all empty, but were partially specified."
                )

            # Set the region render ranges
            maya.cmds.setAttr("defaultArnoldRenderOptions.regionMinX", region[0])
            maya.cmds.setAttr("defaultArnoldRenderOptions.regionMaxX", region[1])
            maya.cmds.setAttr("defaultArnoldRenderOptions.regionMinY", region[2])
            maya.cmds.setAttr("defaultArnoldRenderOptions.regionMaxY", region[3])

            print(f"Set render region to {region_str}", flush=True)
        else:
            print("No region render", flush=True)

        # Set the arnold render type so that we don't just make .ass files, but the actual image
        maya.cmds.setAttr("defaultArnoldRenderOptions.renderType", 0)

        # Set the log verbosity high enough that we get progress reporting output
        if maya.cmds.getAttr("defaultArnoldRenderOptions.log_verbosity") < 2:
            maya.cmds.setAttr("defaultArnoldRenderOptions.log_verbosity", 2)

        maya.cmds.arnoldRender(**self.render_kwargs)
        print(f"MayaClient: Finished Rendering Frame {frame}\n", flush=True)

    def set_error_on_arnold_license_fail(self, data: dict) -> None:
        """
        Sets the property that makes Maya fail if there is no Arnold License.
        If set to False the render will complete with a watermark.

        Args:
            data (dict): : The data given from the Adaptor. Keys expected:
                ['error_on_arnold_license_fail']
        """
        val = data.get("error_on_arnold_license_fail", True)
        maya.cmds.setAttr("defaultArnoldRenderOptions.abortOnLicenseFail", val)

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
            maya.cmds.editRenderLayerGlobals(currentRenderLayer=render_layer_name)
