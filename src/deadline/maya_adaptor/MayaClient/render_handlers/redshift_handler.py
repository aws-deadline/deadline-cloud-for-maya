# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import maya.cmds

from .default_maya_handler import DefaultMayaHandler


class RedshiftHandler(DefaultMayaHandler):
    """
    Render Handler for Redshift
    """

    def __init__(self):
        """
        Constructor for redshift handler.

        * "render" and "batch" kwargs are required booleans to run the redshift renderer.
        * "animation" kwarg is required for renderer to use defaultRenderGlobals' start and end frame settings.
        """
        super().__init__()
        self.render_kwargs["animation"] = True
        self.render_kwargs["render"] = True
        self.render_kwargs["batch"] = True

    def start_render(self, data: dict) -> None:
        """
        Starts a Redshift render.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['frame', 'camera']

        Raises:
            RuntimeError: If no camera was specified and no renderable camera was found, or no frame was specified.
        """
        self.render_kwargs["camera"] = self.get_camera_to_render(data)

        frame = data.get("frame")
        if frame is None:
            raise RuntimeError("MayaClient: Render without a frame number is invalid.")

        maya.cmds.setAttr("defaultRenderGlobals.startFrame", frame)
        maya.cmds.setAttr("defaultRenderGlobals.endFrame", frame)
        maya.cmds.setAttr("defaultRenderGlobals.animation", 1)

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

        maya.cmds.rsRender(**self.render_kwargs)
        print(f"MayaClient: Finished Rendering Frame {frame}\n", flush=True)

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
