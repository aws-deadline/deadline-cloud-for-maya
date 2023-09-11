# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import maya.cmds

"""
Functionality for interacting with Cameras in a Maya scene.
"""

ALL_CAMERAS = "All Cameras"


def get_renderable_camera_names() -> list[str]:
    """
    Returns a list of all camera objects in the scene that are marked as renderable.
    """
    # The ls function returns all of the camera shapes, but the cameras themselves are represented by
    # the transform node which is the parent of the shape.
    camera_shape_names = maya.cmds.ls(cameras=True)
    camera_names = maya.cmds.listRelatives(camera_shape_names, parent=True)

    return [
        camera_name
        for camera_name in camera_names
        if maya.cmds.getAttr(f"{camera_name}.renderable")
    ]


def is_camera_renderable(camera_name) -> bool:
    """
    Returns True if this camera is renderable.
    """
    return maya.cmds.getAttr(f"{camera_name}.renderable")
