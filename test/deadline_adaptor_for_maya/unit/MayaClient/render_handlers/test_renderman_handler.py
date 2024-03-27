# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

from typing import Any

import pytest

import maya.cmds
from unittest.mock import patch
from deadline.maya_adaptor.MayaClient.render_handlers.renderman_handler import RenderManHandler


class TestRenderManHandler:
    @pytest.mark.parametrize("args", [{"image_height": 1500}])
    @patch("deadline.maya_adaptor.MayaClient.render_handlers.renderman_handler.maya.cmds")
    def test_set_image_height(self, mock_cmds, args: dict[str, Any]) -> None:
        """Tests that setting the image height sets the maya render height"""
        # GIVEN
        handler = RenderManHandler()

        # WHEN
        handler.set_image_height(args)

        # THEN
        assert mock_cmds.mock_calls
        mock_cmds.setAttr.assert_called_with("defaultResolution.height", args["image_height"])

    @pytest.mark.parametrize("args", [{"image_width": 1500}])
    @patch("deadline.maya_adaptor.MayaClient.render_handlers.renderman_handler.maya.cmds")
    def test_set_image_width(self, mock_cmds, args: dict[str, Any]) -> None:
        """Tests that setting the image width set the maya render width"""
        # GIVEN
        handler = RenderManHandler()

        # WHEN
        handler.set_image_width(args)

        # THEN
        mock_cmds.setAttr.assert_called_with("defaultResolution.width", args["image_width"])

    @patch.object(maya.cmds, "pluginInfo")
    def test_no_renderman(self, plguinInfo) -> None:
        """Tests that the handler detects missing RenderMan for Maya installation"""
        # GIVEN
        handler = RenderManHandler()
        plguinInfo.return_value = False

        # WHEN/THEN
        with pytest.raises(RuntimeError) as exc_info:
            handler.start_render({})
            assert (
                str(exc_info.value)
                == "MayaClient: The RenderMan for Maya plugin was not loaded. Please verify that it is installed."
            )
