# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

import pytest

from deadline.maya_adaptor.MayaClient.render_handlers.redshift_handler import RedshiftHandler


class TestRedshiftHandler:
    def test_init(self) -> None:
        """
        Validates that we add the 'error_on_arnold_license_fail' function to the action dict.
        """
        # WHEN
        handler = RedshiftHandler()

        # THEN
        assert handler.render_kwargs["batch"]
        assert handler.render_kwargs["animation"]
        assert handler.render_kwargs["batch"]

    @pytest.mark.parametrize("args", [{"image_height": 1500}])
    def test_set_image_height(self, args: dict[str, Any]) -> None:
        """Tests that setting the image height sets the right render kwarg"""
        # GIVEN
        handler = RedshiftHandler()

        # WHEN
        handler.set_image_height(args)

        # THEN
        assert handler.image_height == args["image_height"]

    @pytest.mark.parametrize("args", [{"image_width": 1500}])
    def test_set_image_width(self, args: dict[str, Any]) -> None:
        """Tests that setting the image width sets the right render kwarg"""
        # GIVEN
        handler = RedshiftHandler()

        # WHEN
        handler.set_image_width(args)

        # THEN
        assert handler.image_width == args["image_width"]

    def test_start_render_throws_runtime_error_when_camera_not_set(self) -> None:
        """Tests that a runtime error is raised when there is no camera"""
        # GIVEN
        handler = RedshiftHandler()

        # WHEN
        start_render_data = {"frame": 1}

        # THEN
        with pytest.raises(RuntimeError):
            handler.start_render(start_render_data)

    def test_start_render_throws_runtime_error_when_frama_not_set(self) -> None:
        """Tests that a runtime error is raised when there is no frame"""
        # GIVEN
        handler = RedshiftHandler()

        # WHEN
        start_render_data = {"camera": "persp"}

        # THEN
        with pytest.raises(RuntimeError):
            handler.start_render(start_render_data)

    @patch("deadline.maya_adaptor.MayaClient.render_handlers.redshift_handler.maya.cmds")
    def test_set_render_layer_isolates_the_layer(self, mock_cmds: Mock) -> None:
        """
        Tests that setting the render layer both switches the current render layer and
        isolates it. rsRender takes no layer argument, so the current render layer alone
        does not stop it rendering every renderable layer in the scene.
        """
        # GIVEN
        handler = RedshiftHandler()
        with (
            patch.object(handler, "get_render_layer_to_render", return_value="rs_beauty"),
            patch.object(handler, "isolate_render_layer") as mock_isolate,
        ):
            # WHEN
            handler.set_render_layer({"render_layer": "beauty"})

        # THEN
        mock_cmds.editRenderLayerGlobals.assert_called_once_with(currentRenderLayer="rs_beauty")
        mock_isolate.assert_called_once_with("rs_beauty")
