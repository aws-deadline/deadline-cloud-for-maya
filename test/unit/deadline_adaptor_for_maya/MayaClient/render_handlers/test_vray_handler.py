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
