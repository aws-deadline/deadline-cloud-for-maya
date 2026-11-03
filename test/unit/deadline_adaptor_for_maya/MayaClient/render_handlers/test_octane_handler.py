# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

from typing import Optional
from unittest.mock import Mock, call, patch

import pytest

from deadline.maya_adaptor.MayaClient.render_handlers.octane_handler import OctaneHandler


class TestOctaneHandler:
    @pytest.mark.parametrize("resolution", [None, 1500])
    @pytest.mark.parametrize("layer", [None, "rs_beauty"])
    @patch("deadline.maya_adaptor.MayaClient.render_handlers.octane_handler.maya.cmds")
    def test_start_render(
        self, mock_cmds: Mock, resolution: Optional[int], layer: Optional[str]
    ) -> None:
        """
        Tests that the task frame is applied to the render globals' frame range, which octane
        renders instead of its frame argument, and that the optional settings reach octane.
        """
        # GIVEN
        handler = OctaneHandler()
        handler.image_width = resolution
        handler.image_height = resolution
        if layer:
            handler.render_kwargs["layer"] = layer

        # WHEN
        with patch.object(handler, "get_camera_to_render", return_value="camera1"):
            handler.start_render({"frame": 7, "camera": "camera1"})

        # THEN
        mock_cmds.setAttr.assert_has_calls(
            [
                call("defaultRenderGlobals.startFrame", 7),
                call("defaultRenderGlobals.endFrame", 7),
                call("defaultRenderGlobals.animation", 1),
            ]
        )
        expected = {"frame": 7, "ncam": "camera1", "verbose": True}
        if resolution is not None:
            expected.update(width=resolution, height=resolution)
        if layer:
            expected["layer"] = layer
        mock_cmds.octane.assert_called_once_with(**expected)
