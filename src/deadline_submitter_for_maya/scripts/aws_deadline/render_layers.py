# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Functionality for interacting with Maya's Render Layers
"""
from contextlib import contextmanager
from enum import IntEnum
from typing import List

import maya.app.renderSetup.model.renderSetupPreferences as renderSetupPrefs  # type: ignore
import pymel.core as pmc  # type: ignore
from pymel.core.nodetypes import RenderLayer as pm_RenderLayer  # type: ignore


class LayerSelection(IntEnum):
    """Enum used for determining how to retrieve render layers"""

    ALL = 1
    CURRENT = 2


class RenderLayer:
    """
    A class representing a Render Layer within the Maya scene
    """

    DEFAULT_LAYER_NAME = "defaultRenderLayer"
    DEFAULT_LAYER_DISPLAY_NAME = "masterLayer"

    def __init__(self, layer: pm_RenderLayer):
        self._layer = layer

    @classmethod
    def get_all_layers(
        cls,
    ) -> List["RenderLayer"]:
        """
        Returns a list of all RenderLayers
        """
        return [
            cls(rl)
            for rl in pm_RenderLayer.listAllRenderLayers()
            if not (rl.isFromReferencedFile() and cls.DEFAULT_LAYER_NAME in rl.name())
        ]

    @classmethod
    def get_current_layer(cls) -> "RenderLayer":
        """
        Returns a Render layer object of the current layer
        """
        return cls(pm_RenderLayer.currentLayer())

    @classmethod
    def scene_contains_multiple(cls) -> bool:
        """
        Determines whether or not the scene contains multiple render layers.
        """
        return len(cls.get_all_layers()) > 1

    @staticmethod
    def contains_all_lights() -> bool:
        """
        Returns whether a Render Layer should contain all lights in the scene automatically
        (machine level setting)
        """
        try:
            return renderSetupPrefs.IncludeAllLightsSetting.isEnabled()
        except AttributeError:
            return True

    @property
    def name(self) -> str:
        """
        Returns the Name of the render layer
        """
        return self._layer.name()

    @property
    def renderable(self) -> bool:
        """
        Returns True if the layer is currently marked as renderable.
        """
        return self._layer.renderable.get()

    @property
    def referenced(self) -> bool:
        """Returns whether this layer is from a referenced scene"""
        return self._layer.isFromReferencedFile()

    @property
    def is_default(self) -> bool:
        """Returns True if this is the 'default' render layer that is in each scene"""
        return self._layer.name() == self.DEFAULT_LAYER_NAME

    @property
    def display_name(self) -> str:
        """
        Returns the external name of the render layer.
        """
        if self.name == self.DEFAULT_LAYER_NAME:
            return self.DEFAULT_LAYER_DISPLAY_NAME

        try:
            return pmc.mel.renderLayerDisplayName(self._layer.name())
        except AttributeError:
            return self._layer.name()

    @contextmanager
    def activate(self):
        """
        Switch the currently active Render layer to this render layer.
        """

        prev = pm_RenderLayer.currentLayer()
        self._layer.setCurrent()

        yield

        prev.setCurrent()

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, RenderLayer):
            return False
        return (
            self.name == __o.name
            and self.renderable == __o.renderable
            and self.referenced == __o.referenced
            and self.is_default == __o.is_default
            and self.display_name == __o.display_name
        )

    def __repr__(self) -> str:
        return (
            f"RenderLayer(name='{self.name}', renderable='{self.renderable}, "
            f"referenced={self.referenced}, is_default={self.is_default}, "
            f"display_name={self.display_name}')"
        )
