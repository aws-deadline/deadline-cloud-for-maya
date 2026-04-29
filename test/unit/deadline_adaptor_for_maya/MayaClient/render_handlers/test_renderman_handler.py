# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

from typing import Any

import pytest

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

    @patch.dict("sys.modules", {"rfm2": None})
    def test_no_renderman(self) -> None:
        """Tests that the handler detects missing RenderMan for Maya installation"""
        # GIVEN
        handler = RenderManHandler()

        # WHEN/THEN
        with pytest.raises(RuntimeError, match="Could not import the rfm2 module"):
            handler.start_render({"frame": 1})

    @patch("deadline.maya_adaptor.MayaClient.render_handlers.renderman_handler.DirectoryMapping")
    @patch("deadline.maya_adaptor.MayaClient.render_handlers.renderman_handler.maya.cmds")
    def test_renderman_texture_pathmapping_remaps_paths(self, mock_cmds, mock_dirmap) -> None:
        """Tests that texture paths on RenderMan nodes are remapped via dirmap"""
        # GIVEN
        handler = RenderManHandler()
        mock_dirmap.get_activated.return_value = True
        mock_cmds.ls.side_effect = lambda type=None: (["udim_tex"] if type == "PxrTexture" else [])
        mock_cmds.getAttr.return_value = "C:\\Users\\artist\\color.<UDIM>.png"
        mock_dirmap.convert.return_value = "/mnt/storage/color.<UDIM>.png"

        # WHEN
        handler.set_renderman_texture_pathmapping({})

        # THEN
        mock_cmds.setAttr.assert_called_with(
            "udim_tex.filename", "/mnt/storage/color.<UDIM>.png", type="string"
        )

    @patch("deadline.maya_adaptor.MayaClient.render_handlers.renderman_handler.DirectoryMapping")
    @patch("deadline.maya_adaptor.MayaClient.render_handlers.renderman_handler.maya.cmds")
    def test_renderman_texture_pathmapping_skips_when_dirmap_inactive(
        self, mock_cmds, mock_dirmap
    ) -> None:
        """Tests that no remapping occurs when dirmap is not active"""
        # GIVEN
        handler = RenderManHandler()
        mock_dirmap.get_activated.return_value = False

        # WHEN
        handler.set_renderman_texture_pathmapping({})

        # THEN
        mock_cmds.ls.assert_not_called()

    @patch("deadline.maya_adaptor.MayaClient.render_handlers.renderman_handler.DirectoryMapping")
    @patch("deadline.maya_adaptor.MayaClient.render_handlers.renderman_handler.maya.cmds")
    def test_renderman_texture_pathmapping_skips_unchanged_paths(
        self, mock_cmds, mock_dirmap
    ) -> None:
        """Tests that setAttr is not called when the path is unchanged"""
        # GIVEN
        handler = RenderManHandler()
        mock_dirmap.get_activated.return_value = True
        mock_cmds.ls.side_effect = lambda type=None: (["tex1"] if type == "PxrTexture" else [])
        mock_cmds.getAttr.return_value = "/already/linux/path.png"
        mock_dirmap.convert.return_value = "/already/linux/path.png"

        # WHEN
        handler.set_renderman_texture_pathmapping({})

        # THEN
        mock_cmds.setAttr.assert_not_called()
