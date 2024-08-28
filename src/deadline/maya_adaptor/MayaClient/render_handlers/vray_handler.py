# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from .default_maya_handler import DefaultMayaHandler

import maya.cmds
import maya.mel


class VRayHandler(DefaultMayaHandler):
    """Render Handler for V-Ray"""

    def __init__(self):
        """
        Initializes the V-Ray Renderer Handler.
        """
        super().__init__()

    def vraySettingsNodeExists(self) -> bool:
        """
        Check if vraySettings node exists. If not found, an attempt will be made to create it.

        Returns True if vraySettings node was found or created successfully.
        """
        if maya.cmds.objExists("vraySettings"):
            return True

        print("MayaClient: vraySettings node not found in the scene!", flush=True)

        if not maya.mel.eval("exists vrayCreateVRaySettingsNode"):
            # V-Ray is probably not loaded? Wrong version? Unable to create vray node
            return False

        maya.mel.eval("vrayCreateVRaySettingsNode")
        if not maya.cmds.objExists("vraySettings"):
            print("MayaClient: Unable to create vraySettings node.", flush=True)
            return False

        print("MayaClient: Created default vraySettings node.", flush=True)
        return True

    def start_render(self, data: dict) -> None:
        """
        Starts a render.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['frame']

        Raises:
            RuntimeError: If no camera was specified or no renderable camera was found,
            when no frame was specified or when no vraySettings node found in the scene.
        """
        if not maya.cmds.pluginInfo("vrayformaya", query=True, loaded=True):
            raise RuntimeError(
                "MayaClient: The VRay for Maya plugin was not loaded. Please verify that VRay is installed."
            )

        frame = data.get("frame")
        if frame is None:
            raise RuntimeError("MayaClient: start_render called without a frame number.")

        self.camera_name = self.get_camera_to_render(data)
        if self.camera_name is None:
            raise RuntimeError("MayaClient: start_render called without a valid camera.")
        self.render_kwargs["camera"] = self.camera_name

        # In order of preference, use the task's output_file_prefix, the step's output_file_prefix, or the scene file setting.
        output_file_prefix = data.get("output_file_prefix", self.output_file_prefix)
        if output_file_prefix:
            maya.cmds.setAttr(
                "defaultRenderGlobals.imageFilePrefix", output_file_prefix, type="string"
            )

        if self.image_width is not None:
            maya.cmds.setAttr("vraySettings.width", self.image_width)
            print(f"Set image width to {self.image_width}", flush=True)
        if self.image_height is not None:
            maya.cmds.setAttr("vraySettings.height", self.image_height)
            print(f"Set image height to {self.image_height}", flush=True)

        region = [
            data.get(field)
            for field in ("region_min_x", "region_max_x", "region_min_y", "region_max_y")
        ]
        if any(v is not None for v in region):
            raise RuntimeError(
                "MayaClient: A region render was specified, but region rendering support is not implemented for the selected renderer."
            )

        if not self.vraySettingsNodeExists():
            raise RuntimeError(
                "MayaClient: start_render called with missing vraySettings node in the scene."
            )

        # Always set the animation type to 2 (specific frames) and one frame animation
        maya.cmds.setAttr("vraySettings.animType", 2)
        maya.cmds.setAttr("vraySettings.animFrames", str(frame), type="string")

        # We want to write images so force set the translator settings for rendering an image without vrscene file export.
        maya.cmds.setAttr("vraySettings.vrscene_render_on", 1)
        maya.cmds.setAttr("vraySettings.vrscene_on", 0)

        # Set the V-Ray GPU engine from 3 (RTX mode) to 2 (CUDA mode)
        if maya.cmds.getAttr("vraySettings.productionEngine") == 3:
            maya.cmds.setAttr("vraySettings.productionEngine", 2)
            print("MayaClient: Changing V-Ray GPU engine from RTX to CUDA mode.", flush=True)

        # Disable distributed rendering
        maya.cmds.setAttr("vraySettings.sys_distributed_rendering_on", 0)

        # Adjust the output settings
        maya.cmds.setAttr("vraySettings.dontSaveImage", 0)
        maya.cmds.setAttr("vraySettings.noAlpha", 0)
        maya.cmds.setAttr("vraySettings.dontSaveRgbChannel", 0)

        # Set the log message level to 3 (report errors, warnings and general information) if needed
        if maya.cmds.getAttr("vraySettings.sys_message_level") < 3:
            maya.cmds.setAttr("vraySettings.sys_message_level", 3)

        maya.cmds.vrend(**self.render_kwargs)
        print(f"MayaClient: Finished Rendering Frame {frame}\n", flush=True)

    def set_output_file_prefix(self, data: dict) -> None:
        """
        Sets the output file prefix.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['output_file_prefix']
        """
        prefix = data.get("output_file_prefix")
        if prefix and self.vraySettingsNodeExists():
            maya.cmds.setAttr("vraySettings.fileNamePrefix", prefix, type="string")

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
