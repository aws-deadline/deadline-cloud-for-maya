# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import pytest

from deadline.maya_adaptor.MayaClient.filename_utils import resolve_tokens


class TestResolveTokens:
    @pytest.mark.parametrize(
        "pattern, scene_name, render_layer, camera, expected",
        [
            # 1. All tokens
            (
                "<Scene>/<RenderLayer>/<RenderLayer>",
                "myScene",
                "myLayer",
                "cam1",
                "myScene/myLayer/myLayer",
            ),
            # 2. Camera token
            ("<Camera>/<Scene>", "shot01", "", "renderCam", "renderCam/shot01"),
            # 3. Alias %l
            ("<Scene>/%l/%l", "test", "fg", "", "test/fg/fg"),
            # 4. Alias %c
            ("%c_<Scene>", "s", "", "cam", "cam_s"),
            # 5. Alias <Layer>
            ("<Layer>/<Scene>", "shot", "bg", "", "bg/shot"),
            # 6. Alias %s
            ("%s_render", "myFile", "", "", "myFile_render"),
            # 7. Case insensitive
            ("<scene>/<renderlayer>/<camera>", "s", "l", "c", "s/l/c"),
            # 8. No tokens
            ("myRender", "", "", "", "myRender"),
            # 9. Empty string
            ("", "", "", "", ""),
            # 10. None
            (None, "", "", "", None),
            # 11. Unknown token passes through
            ("<Scene>/<RenderPass>/beauty", "s", "", "", "s/<RenderPass>/beauty"),
            # 12. Empty token values
            ("<Scene>/<RenderLayer>", "", "", "", "/"),
        ],
    )
    def test_resolve_tokens(
        self,
        pattern: str,
        scene_name: str,
        render_layer: str,
        camera: str,
        expected: str,
    ) -> None:
        result: str = resolve_tokens(
            pattern, scene_name=scene_name, render_layer=render_layer, camera=camera
        )
        assert result == expected
