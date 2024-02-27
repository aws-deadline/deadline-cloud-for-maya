# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from .default_maya_handler import DefaultMayaHandler

import maya.cmds


class RenderManHandler(DefaultMayaHandler):
    """Render Handler for RenderMan"""

    def __init__(self):
        """
        Initializes the RenderMan Renderer Handler
        """
        super().__init__()
        self.render_layer = "defaultRenderLayer"

    def set_render_layer(self, data: dict) -> None:
        """
        Sets the render layer.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['render_layer']

        Raises:
            RuntimeError: If the render layer cannot be found
        """
        rl = self.get_render_layer_to_render(data)
        if rl:
            self.render_layer = rl

    def set_image_height(self, data: dict) -> None:
        """
        Sets the image height.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['image_height']
        """
        yresolution = int(data.get("image_height", 0))
        maya.cmds.setAttr("defaultResolution.height", yresolution)

    def set_image_width(self, data: dict) -> None:
        """
        Sets the image width.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['image_width']
        """
        xresolution = int(data.get("image_width", 0))
        maya.cmds.setAttr("defaultResolution.width", xresolution)

    def start_render(self, data: dict) -> None:
        """
        Starts a render.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['frame']

        Raises:
            RuntimeError: If Renderman for Maya was not loaded
        """

        if not maya.cmds.pluginInfo("RenderManForMaya.py", query=True, loaded=True):
            raise RuntimeError(
                "MayaClient: The RenderMan for Maya plugin was not loaded. Please verify that it is installed."
            )

        frame = data.get("frame")
        if frame is None:
            raise RuntimeError("MayaClient: start_render called without a frame number.")
        self.render_kwargs["seq"] = frame

        # Note that some overrides are currently not implemented (camera, resolution, etc...)

        import rfm2

        rfm2.render.RNDR.set_render_type(rfm2.render.RT_BATCH)
        rfm2.render_with_renderman()
        rfm2.render.RNDR.start()
        rfm2.render.frame(
            f" -s {frame} -e {frame} -layer {self.render_layer} -numThreads 0 -txmake "
        )
        rfm2.render.RNDR.stop()

        print(f"MayaClient: Finished Rendering Frame {frame}\n", flush=True)
