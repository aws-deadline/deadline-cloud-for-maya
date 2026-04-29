# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from .default_maya_handler import DefaultMayaHandler
from ..dir_map import DirectoryMapping

import maya.cmds

# RenderMan node types that have a "filename" attribute containing texture paths
_RMAN_TEXTURE_NODE_TYPES = [
    "PxrTexture",
    "PxrNormalMap",
    "PxrBump",
    "PxrPtexture",
    "PxrMultiTexture",
]


class RenderManHandler(DefaultMayaHandler):
    """Render Handler for RenderMan"""

    def __init__(self):
        """
        Initializes the RenderMan Renderer Handler
        """
        super().__init__()
        self.render_layer = "defaultRenderLayer"
        self.action_dict["renderman_texture_pathmapping"] = self.set_renderman_texture_pathmapping

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

    def set_renderman_texture_pathmapping(self, data: dict) -> None:
        """
        Applies path mapping to RenderMan texture node attributes.

        RfM's texture manager reads texture paths directly from Maya node
        attributes and bypasses Maya's dirmap. This method manually applies
        dirmap to the filename attributes of RenderMan texture nodes so that
        the paths are correct when the texture manager processes them.

        This follows the same pattern as set_cache_pathmapping in the base
        class, which solves the same problem for cache node attributes.
        """
        if not DirectoryMapping.get_activated():
            return

        # Iterate each RenderMan node type that references texture files.
        # All these node types have a "filename" attribute by definition.
        for node_type in _RMAN_TEXTURE_NODE_TYPES:
            for node in maya.cmds.ls(type=node_type) or []:
                attr: str = f"{node}.filename"
                old_path: str = maya.cmds.getAttr(attr)
                # Apply dirmap to convert the path (e.g. Windows -> Linux)
                new_path: str = DirectoryMapping.convert(old_path)
                if new_path != old_path:
                    maya.cmds.setAttr(attr, new_path, type="string")
                    print(
                        f"RenderMan texture pathmapping: {old_path} -> {new_path}",
                        flush=True,
                    )

    def start_render(self, data: dict) -> None:
        """
        Starts a render.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['frame']

        Raises:
            RuntimeError: If Renderman for Maya was not loaded
        """

        frame = data.get("frame")
        if frame is None:
            raise RuntimeError("MayaClient: start_render called without a frame number.")
        self.render_kwargs["seq"] = frame

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

        # Note that some overrides are currently not implemented (camera, resolution, etc...)

        try:
            import rfm2
        except ImportError:
            raise RuntimeError(
                "MayaClient: Could not import the rfm2 module. "
                "Please verify that RenderMan for Maya is installed and loaded."
            )

        rfm2.render.RNDR.set_render_type(rfm2.render.RT_BATCH)
        rfm2.render_with_renderman()
        rfm2.render.RNDR.start()
        rfm2.render.frame(
            f" -s {frame} -e {frame} -layer {self.render_layer} -numThreads 0 -txmake "
        )
        rfm2.render.RNDR.stop()

        print(f"MayaClient: Finished Rendering Frame {frame}\n", flush=True)
