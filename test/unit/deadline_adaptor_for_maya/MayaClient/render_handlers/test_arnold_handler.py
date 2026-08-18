# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from deadline.maya_adaptor.MayaClient.render_handlers.arnold_handler import ArnoldHandler


class TestArnoldHandler:
    def test_init(self) -> None:
        """
        Validates that we add the 'error_on_arnold_license_fail' function to the action dict.
        """
        # WHEN
        handler = ArnoldHandler()

        # THEN
        assert "error_on_arnold_license_fail" in handler.action_dict
        assert (
            handler.action_dict["error_on_arnold_license_fail"]
            == handler.set_error_on_arnold_license_fail
        )
        assert handler.render_kwargs["batch"]

    @pytest.mark.parametrize("args", [{"image_height": 1500}])
    def test_set_image_height(self, args: dict[str, Any]) -> None:
        """Tests that setting the image height sets the right render kwarg"""
        # GIVEN
        handler = ArnoldHandler()

        # WHEN
        handler.set_image_height(args)

        # THEN
        assert handler.image_height == args["image_height"]

    @pytest.mark.parametrize("args", [{"image_width": 1500}])
    def test_set_image_width(self, args: dict[str, Any]) -> None:
        """Tests that setting the image width sets the right render kwarg"""
        # GIVEN
        handler = ArnoldHandler()

        # WHEN
        handler.set_image_width(args)

        # THEN
        assert handler.image_width == args["image_width"]

    @patch("deadline.maya_adaptor.MayaClient.render_handlers.arnold_handler.maya.cmds")
    def test_set_render_layer_restricts_batch_render_to_the_layer(self, mock_cmds) -> None:
        """
        Tests that setting the render layer both switches the current render layer AND
        restricts the upcoming arnoldRender batch call to that single layer. arnoldRender
        does not take a 'layer' kwarg, so without the setMayaSoftwareLayers call Arnold
        can render every renderable layer in the scene regardless of which one is "current".
        """
        # GIVEN
        handler = ArnoldHandler()
        with patch.object(
            handler, "get_render_layer_to_render", return_value="layer1"
        ), patch.object(handler, "restrict_batch_render_to_layer") as mock_restrict:
            # WHEN
            handler.set_render_layer({"render_layer": "layer1"})

            # THEN
            mock_cmds.editRenderLayerGlobals.assert_called_once_with(currentRenderLayer="layer1")
            mock_restrict.assert_called_once_with("layer1")
