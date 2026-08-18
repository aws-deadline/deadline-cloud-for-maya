# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

from typing import Any

import pytest

import maya.cmds
from unittest.mock import patch
from deadline.maya_adaptor.MayaClient.render_handlers.vray_handler import VRayHandler


class TestVrayHandler:
    def test_can_create_vraysettings(self) -> None:
        """
        Validates that we can create the 'vraySettings' node.
        """
        # WHEN
        handler = VRayHandler()

        # THEN
        assert handler.vraySettingsNodeExists()

    @pytest.mark.parametrize("args", [{"image_height": 1500}])
    @patch("deadline.maya_adaptor.MayaClient.render_handlers.vray_handler.maya.cmds")
    def test_set_image_height(self, mock_cmds, args: dict[str, Any]) -> None:
        """Tests that setting the image height sets the right render kwarg"""
        # GIVEN
        handler = VRayHandler()

        # WHEN
        handler.set_image_height(args)

        # THEN
        assert handler.image_height == args["image_height"]

    @pytest.mark.parametrize("args", [{"image_width": 1500}])
    @patch("deadline.maya_adaptor.MayaClient.render_handlers.vray_handler.maya.cmds")
    def test_set_image_width(self, mock_cmds, args: dict[str, Any]) -> None:
        """Tests that setting the image width sets the right render kwarg"""
        # GIVEN
        handler = VRayHandler()

        # WHEN
        handler.set_image_width(args)

        # THEN
        assert handler.image_width == args["image_width"]

    @patch("deadline.maya_adaptor.MayaClient.render_handlers.vray_handler.maya.cmds")
    def test_set_render_layer_restricts_batch_render_to_the_layer(self, mock_cmds) -> None:
        """
        Tests that setting the render layer both switches the current render layer AND
        restricts the upcoming vrend batch call to that single layer. vrend does not take
        a 'layer' kwarg, so without the setMayaSoftwareLayers call V-Ray can render every
        renderable layer in the scene regardless of which one is "current".
        """
        # GIVEN
        handler = VRayHandler()
        with patch.object(
            handler, "get_render_layer_to_render", return_value="layer1"
        ), patch.object(handler, "restrict_batch_render_to_layer") as mock_restrict:
            # WHEN
            handler.set_render_layer({"render_layer": "layer1"})

            # THEN
            mock_cmds.editRenderLayerGlobals.assert_called_once_with(currentRenderLayer="layer1")
            mock_restrict.assert_called_once_with("layer1")

    @patch.object(maya.cmds, "pluginInfo")
    def test_no_vray(self, plguinInfo) -> None:
        """Tests that setting the image width sets the right render kwarg"""
        # GIVEN
        handler = VRayHandler()
        plguinInfo.return_value = False

        # WHEN/THEN
        with pytest.raises(RuntimeError) as exc_info:
            handler.start_render({})
            assert (
                str(exc_info.value)
                == "MayaClient: The VRay for Maya plugin was not loaded. Please verify that VRay is installed."
            )
