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
            RuntimeError: If no camera was specified and no renderable camera was found
        """
        frame = data.get("frame")
        if frame is None:
            raise RuntimeError("MayaClient: start_render called without a frame number.")
        self.render_kwargs["seq"] = frame

        self.render_kwargs["camera"] = self.get_camera_to_render(data)

        if "width" not in self.render_kwargs:
            self.render_kwargs["width"] = maya.cmds.getAttr("defaultResolution.width")
            print(
                f"No width was specified, defaulting to {self.render_kwargs['width']}",
                flush=True,
            )
        if "height" not in self.render_kwargs:
            self.render_kwargs["height"] = maya.cmds.getAttr("defaultResolution.height")
            print(
                f"No height was specified, defaulting to {self.render_kwargs['height']}",
                flush=True,
            )

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

    def set_image_height(self, data: dict) -> None:
        """
        Sets the image height.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['image_height']
        """
        yresolution = int(data.get("image_height", 0))
        if yresolution:
            self.render_kwargs["height"] = yresolution

    def set_image_width(self, data: dict) -> None:
        """
        Sets the image width.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['image_width']
        """
        xresolution = int(data.get("image_width", 0))
        if xresolution:
            self.render_kwargs["width"] = xresolution
