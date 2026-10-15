# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import maya.cmds

from .default_maya_handler import DefaultMayaHandler


class OctaneHandler(DefaultMayaHandler):
    """
    Render Handler for OctaneRender
    """

    def start_render(self, data: dict) -> None:
        """
        Starts a render with OctaneRender.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['frame']
                Optional keys: ['camera', 'output_file_prefix']

        Raises:
            RuntimeError: If no frame was specified, no renderable camera was found, or a
                region render was requested.
        """
        frame = data.get("frame")
        if frame is None:
            raise RuntimeError("MayaClient: start_render called without a frame number.")

        # octane renders the render globals' frame range rather than its frame argument.
        maya.cmds.setAttr("defaultRenderGlobals.startFrame", frame)
        maya.cmds.setAttr("defaultRenderGlobals.endFrame", frame)
        maya.cmds.setAttr("defaultRenderGlobals.animation", 1)

        camera = self.get_camera_to_render(data)
        print(f"Rendering camera: {camera}", flush=True)

        region = [
            data.get(field)
            for field in ("region_min_x", "region_max_x", "region_min_y", "region_max_y")
        ]
        if any(v is not None for v in region):
            raise RuntimeError(
                "MayaClient: A region render was specified, but region rendering support is not implemented for the selected renderer."
            )

        # In order of preference, use the task's output_file_prefix, the step's output_file_prefix, or the scene file setting.
        output_file_prefix = data.get("output_file_prefix", self.output_file_prefix)
        if output_file_prefix:
            maya.cmds.setAttr(
                "defaultRenderGlobals.imageFilePrefix", output_file_prefix, type="string"
            )

        octane_kwargs = {"frame": frame, "ncam": camera, "verbose": True}
        if self.image_width is not None:
            octane_kwargs["width"] = self.image_width
        if self.image_height is not None:
            octane_kwargs["height"] = self.image_height
        if self.render_kwargs.get("layer"):
            octane_kwargs["layer"] = self.render_kwargs["layer"]

        maya.cmds.octane(**octane_kwargs)
        print(f"MayaClient: Finished Rendering Frame {frame}\n", flush=True)
