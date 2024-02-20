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

        # some overrides are currently not implemented

        import rfm2

        rfm2.render.RNDR.set_render_type(rfm2.render.RT_BATCH)
        rfm2.render_with_renderman()
        rfm2.render.RNDR.start()
        rfm2.render.frame(
            f" -s {frame} -e {frame} -layer {self.render_layer} -numThreads 0 -txmake "
        )
        rfm2.render.RNDR.stop()

        print(f"MayaClient: Finished Rendering Frame {frame}\n", flush=True)
