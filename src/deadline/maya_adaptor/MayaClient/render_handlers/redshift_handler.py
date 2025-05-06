# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from .default_maya_handler import DefaultMayaHandler

import maya.cmds
import maya.mel
import os


class   RedshiftHandler(DefaultMayaHandler):
    """Render Handler for Redshift"""

    def __init__(self):
        """
        Initializes the Redshift Renderer Handler.
        """
        super().__init__()

    def redshiftOptionsNodeExists(self) -> bool:
        """
        Check if redshiftOptions node exists. If not found, an attempt will be made to create it.

        Returns True if redshiftOptions node was found or created successfully.
        """
        if maya.cmds.objExists("redshiftOptions"):
            return True

        print("MayaClient: redshiftSettings node not found in the scene!", flush=True)
        # Attempt to create the node
        try:
            maya.createNode("RedshiftOptions", name="redshiftOptions")
            return maya.cmds.objExists("redshiftOptions")
        except Exception as e:
            print(f"MayaClient: Failed to create redshiftOptions node: {e}", flush=True)
            return False
        
    def get_animation_frame_range(self) -> tuple:
        """
        Get the start and end frame of the animation in the scene.
        
        Returns:
            tuple: A tuple containing (start_frame, end_frame)
        """
        try:
            start_frame = maya.cmds.playbackOptions(query=True, minTime=True)
            end_frame = maya.cmds.playbackOptions(query=True, maxTime=True)
            return start_frame, end_frame
        except Exception as e:
            print(f"MayaClient: Error getting animation frame range: {e}", flush=True)
            # Return default values if there's an error
            return 1, 1
        
    def is_animation_scene(self) -> bool:
        """
        Check if the current scene is an animation.
        
        Returns:
            bool: True if the scene is an animation, False otherwise
        """
        try:
            # Method 1: Check animation attribute if it exists
            if maya.cmds.objExists("defaultRenderGlobals.animation"):
                return bool(maya.cmds.getAttr("defaultRenderGlobals.animation"))
                
            # Method 2: Check for animation curves
            anim_curves = maya.cmds.ls(type=["animCurve", "animCurveTL", "animCurveTA", "animCurveTT", "animCurveTU"])
            if anim_curves:
                return True
                
            # Method 3: Check if timeline range is more than 1 frame
            start_frame, end_frame = self.get_animation_frame_range()
            if end_frame > start_frame:
                return True
                
            return False
        except Exception as e:
            print(f"MayaClient: Error checking if scene is animation: {e}", flush=True)
            return False
    
    def start_render(self, data: dict) -> None:
        """
        Starts a render.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['frame']

        Raises:
            RuntimeError: If no camera was specified or no renderable camera was found,
        """
        if not maya.cmds.pluginInfo("redshift4maya", query=True, loaded=True):
            raise RuntimeError(
                "MayaClient: The Redshift for Maya plugin was not loaded. Please verify that Redshift is installed."
            )
        maya.cmds.setAttr("defaultRenderGlobals.currentRenderer", "redshift", type="string")

        # Get the frame number from data
        frame = data.get("frame")
        if frame is None:
            raise RuntimeError("MayaClient: start_render called without a frame number.")
        
        # Set the current frame in Maya
        maya.cmds.currentTime(frame)
        
        # Get camera to render
        self.camera_name = self.get_camera_to_render(data)
        if self.camera_name is None:
            raise RuntimeError("MayaClient: start_render called without a valid camera.")
        
        print(f"MayaClient: Rendering with Redshift renderer for frame {frame}", flush=True)

        # In order of preference, use the task's output_file_prefix, the step's output_file_prefix, or the scene file setting.
        # Render output prefix
        output_file_prefix = data.get("output_file_prefix", self.output_file_prefix)
        if output_file_prefix:
            maya.cmds.setAttr(
                "defaultRenderGlobals.imageFilePrefix", output_file_prefix, type="string"
            )
        
        # Render dimensions
        if self.image_width is None or self.image_height is None:
            # Get from current render settings
            self.image_width = maya.cmds.getAttr("defaultResolution.width")
            self.image_height = maya.cmds.getAttr("defaultResolution.height")
        # Validate values before rendering      
        if not isinstance(self.image_width, (int, float)) or not isinstance(self.image_height, (int, float)):
            raise ValueError(f"Invalid image dimensions: width={self.image_width}, height={self.image_height}")
        # Only add dimensions if they are valid
        if self.image_width and self.image_height:
            maya.cmds.setAttr("defaultResolution.width", int(self.image_width))
            maya.cmds.setAttr("defaultResolution.height", int(self.image_height))
            print(f"Set image dimensions to {self.image_width}x{self.image_height}", flush=True)
        
        # Render region
        region = [
            data.get(field)
            for field in ("region_min_x", "region_max_x", "region_min_y", "region_max_y")
        ]
        if any(v is not None for v in region):
            raise RuntimeError(
                "MayaClient: A region render was specified, but region rendering support is not implemented for the selected renderer."
            )

        if not self.redshiftOptionsNodeExists():
            raise RuntimeError(
                "MayaClient: start_render called with missing redshiftOptions node in the scene."
            )

        # Use the Python API to render with Redshift
        # This is similar to how the Arnold handler works
        print(f"Rendering frame {frame} with camera {self.camera_name}", flush=True)
        maya.cmds.render(self.camera_name)
        print(f"MayaClient: Finished Rendering Frame {frame}\n", flush=True)

    def set_output_file_prefix(self, data: dict) -> None:
        """
        Sets the output file prefix.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['output_file_prefix']
        """
        prefix = data.get("output_file_prefix")
        if prefix and self.redshiftOptionsNodeExists():
            maya.cmds.setAttr("redshiftOptions.imageFilePrefix", prefix, type="string")

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