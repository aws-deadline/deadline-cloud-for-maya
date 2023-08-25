# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import pytest

from deadline_adaptor_for_maya.MayaClient.render_handlers import MayaHandlerBase
from deadline_adaptor_for_maya.MayaClient.render_handlers.get_render_handler import (
    get_render_handler,
    renderers,
)


class TestGetRenderHandler:
    DEFAULT_RENDER_HANDLER_KEY = "mayaSoftware"
    DEFAULT_RENDER_HANDLER_CLASS = MayaHandlerBase
    default_renderer_params = ["", "renderer that doesn't exist"]

    @pytest.mark.parametrize("renderer", default_renderer_params)
    def test_default_render_handler(self, renderer: str):
        """Tests that the default render handler is the mayaSoftware render handler"""
        # GIVEN
        expected_key = self.DEFAULT_RENDER_HANDLER_KEY
        expected_class = self.DEFAULT_RENDER_HANDLER_CLASS

        # WHEN
        handler = get_render_handler(renderer)

        # THEN
        assert isinstance(handler, expected_class)
        assert renderers[expected_key] == expected_class
