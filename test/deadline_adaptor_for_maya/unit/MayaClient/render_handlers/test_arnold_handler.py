# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

from typing import Any

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
