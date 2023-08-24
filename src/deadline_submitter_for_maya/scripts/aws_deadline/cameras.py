# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Functionality for interacting with Cameras in a Maya scene.
"""
from enum import IntEnum
from typing import List

import pymel.core as pmc  # pylint: disable=import-error
from pymel.core.nodetypes import Camera as pm_camera  # pylint: disable=import-error


class CameraSelection(IntEnum):
    """
    An enum used to represent how cameras should be handled when submitting jobs.
    """

    SEPARATE = 1
    COMBINED = 2


class Camera:
    """
    Represents a single camera in the active scene
    """

    def __init__(self, cam: pm_camera) -> None:
        self._cam: pm_camera = cam

    @classmethod
    def get_all_cameras(cls) -> List["Camera"]:
        """
        Returns a list of all camera objects within the scene
        """
        return [Camera(cam) for cam in pmc.ls(cameras=1)]

    @classmethod
    def get_renderable_cameras(cls) -> List["Camera"]:
        """
        Returns a list of all camera objects in the scene that are marked as renderable.
        """
        return [Camera(cam) for cam in pmc.ls(cameras=1) if cam.renderable.get()]

    @classmethod
    def multiple_renderable(cls) -> bool:
        """
        Returns True if there are multiple renderable Cameras in the scene.
        """
        return len(cls.get_renderable_cameras()) > 1

    @property
    def is_renderable(self) -> bool:
        """
        Returns True if this camera is renderable.
        """
        return self._cam.renderable.get()

    @property
    def name(self) -> str:
        """
        Returns the Name of this camera
        """
        parent = self._cam.getParent()
        if parent is not None:
            return parent.name()

        raise AttributeError("Cam is not Configured properly")

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Camera):
            return False
        return self.name == __o.name and self.is_renderable == __o.is_renderable

    def __repr__(self) -> str:
        return f"Camera(name='{self.name}', is_renderable='{self.is_renderable}')"
