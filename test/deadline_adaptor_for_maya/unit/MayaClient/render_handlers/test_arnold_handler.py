# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from typing import Any, Dict, List, Optional
from unittest.mock import Mock, patch

import pymel.core as pm
import pytest

from deadline_adaptor_for_maya.MayaClient.render_handlers.arnold_handler import ArnoldHandler

from .mock_stubs import MockCamera


class TestArnoldHandler:
    def test_init(self) -> None:
        """
        Validates that we set arnold to render exr files in the constructor, and that we add the
        'error_on_arnold_license_fail' function to the action dict.
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

    error_on_lic_fail_params = [
        {"error_on_arnold_license_fail": False},
        {"error_on_arnold_license_fail": True},
    ]

    @pytest.mark.parametrize("args", error_on_lic_fail_params)
    @patch.object(pm.SCENE.defaultArnoldRenderOptions.abortOnLicenseFail, "set")
    def test_set_error_on_arnold_license_fail(self, mock_set: Mock, args: Dict[str, Any]) -> None:
        # GIVEN
        handler = ArnoldHandler()
        val = args["error_on_arnold_license_fail"]

        # WHEN
        handler.set_error_on_arnold_license_fail(args)

        # THEN
        mock_set.assert_called_once_with(val)

    set_camera_args = [
        (
            {"camera": "camera3"},
            [MockCamera("camera1"), MockCamera("camera2"), MockCamera("camera3")],
            MockCamera("camera3"),
        ),
        (
            {"camera": "camera3"},
            [MockCamera("cameraShape1"), MockCamera("cameraShape2"), MockCamera("cameraShape3")],
            MockCamera("cameraShape3"),
        ),
    ]

    @pytest.mark.parametrize("args, ls_return_value, expected", set_camera_args)
    def test_set_camera(
        self,
        args: Dict[str, Any],
        ls_return_value: List[MockCamera],
        expected: MockCamera,
    ) -> None:
        """Tests that setting the camera calls the correct pymel functions"""
        # GIVEN
        handler = ArnoldHandler()
        pm.ls.return_value = ls_return_value

        # WHEN
        handler.set_camera(args)

        # THEN
        assert handler.render_kwargs["camera"] == expected

    set_render_layer_args = [
        (
            {"render_layer": "layer1"},
            ["layer1", "layer2", "layer3"],
        )
    ]

    @pytest.mark.parametrize("args, ls_return_value", set_render_layer_args)
    def test_set_render_layer(self, args: Dict[str, Any], ls_return_value: List[str]) -> None:
        """Tests that setting the render layer calls the correct pymel functions"""
        # GIVEN
        handler = ArnoldHandler()
        pm.ls.return_value = ls_return_value

        # WHEN
        handler.set_render_layer(args)

        # THEN
        pm.editRenderLayerGlobals.assert_called_once_with(currentRenderLayer=args["render_layer"])

    @pytest.mark.parametrize("args", [{"frame": 99}])
    @patch.object(pm.SCENE.defaultArnoldRenderOptions.log_verbosity, "set")
    @patch.object(pm.SCENE.defaultArnoldRenderOptions.renderType, "set")
    @patch.object(pm, "arnoldRender")
    def test_start_render(
        self,
        mock_render: Mock,
        mock_rendertype_set: Mock,
        mock_verbosity_set: Mock,
        args: Dict[str, Any],
    ) -> None:
        """Tests that starting a render calls the correct pymel functions"""
        # GIVEN
        handler = ArnoldHandler()
        handler.render_kwargs = {"camera": "camera1", "height": 1000, "width": 1000, "batch": True}
        # WHEN
        handler.start_render(args)

        # THEN
        mock_render.assert_called_once_with(**handler.render_kwargs)
        mock_rendertype_set.assert_called_once_with(0)
        mock_verbosity_set.assert_called_once_with(2)

    verbosities = [
        pytest.param(0, 2),
        pytest.param(1, 2),
        pytest.param(2, -1),
        pytest.param(3, -1),
        pytest.param(4, -1),
    ]

    @pytest.mark.parametrize("scene_verbosity, expected_verbosity", verbosities)
    @pytest.mark.parametrize("args", [{"frame": 99}])
    @patch.object(pm, "arnoldRender")
    @patch.object(pm, "SCENE")
    def test_start_render_log_verbosity(
        self,
        mock_scene: Mock,
        mock_render: Mock,
        args: Dict[str, Any],
        scene_verbosity,
        expected_verbosity,
    ) -> None:
        """Tests that verbosity level is not overridden when it is greater than 2"""
        # GIVEN
        handler = ArnoldHandler()
        handler.render_kwargs = {"camera": "camera1", "height": 1000, "width": 1000, "batch": True}
        mock_scene.defaultArnoldRenderOptions.log_verbosity.get.return_value = scene_verbosity
        # WHEN
        handler.start_render(args)

        # THEN
        mock_render.assert_called_once_with(**handler.render_kwargs)
        if expected_verbosity < 0:
            mock_scene.defaultArnoldRenderOptions.log_verbosity.set.assert_not_called()
        else:
            mock_scene.defaultArnoldRenderOptions.log_verbosity.set.assert_called_once_with(
                expected_verbosity
            )

    @pytest.mark.parametrize("args", [{}])
    @patch.object(pm, "render")
    def test_start_render_no_frame(self, mock_render: Mock, args: Dict[str, Any]) -> None:
        # GIVEN
        handler = ArnoldHandler()
        handler.cameras = ["camera1"]
        handler.render_kwargs = {"height": 1000, "width": 1000}
        # WHEN
        with pytest.raises(RuntimeError) as exc_info:
            handler.start_render(args)

        # THEN
        assert str(exc_info.value) == "MayaClient: start_render called without a frame number."
        mock_render.assert_not_called()

    @pytest.mark.parametrize("args", [{"frame": 99}])
    @patch.object(pm, "arnoldRender")
    @patch.object(pm, "ls")
    def test_start_render_no_camera(
        self,
        mock_ls: Mock,
        mock_render: Mock,
        args: Dict[str, Any],
        capsys,
    ) -> None:
        """Tests that starting a render without a camera calls the correct pymel functions"""
        # GIVEN
        handler = ArnoldHandler()
        return_cameras = [
            MockCamera("camera1", renderable=False),
            MockCamera("camera2"),
            MockCamera("camera3"),
        ]
        mock_ls.return_value = return_cameras

        handler.render_kwargs = {"height": 1000, "width": 1000, "batch": True}

        # WHEN
        handler.start_render(args)

        # THEN
        stdout = capsys.readouterr().out
        assert f"No camera was specified, defaulting to render on {return_cameras[1]}." in stdout
        assert handler.render_kwargs["camera"] == return_cameras[1]
        mock_render.assert_called_once_with(**handler.render_kwargs)

    @pytest.mark.parametrize("cameras", [None, []])
    @pytest.mark.parametrize("args", [{"frame": 99}])
    @patch.object(pm, "arnoldRender")
    @patch.object(pm, "ls")
    def test_start_render_no_camera_found(
        self,
        mock_ls: Mock,
        mock_render: Mock,
        cameras: Optional[List],
        args: Dict[str, Any],
    ) -> None:
        """Tests that starting a render without a camera raises an error if no camera is found"""
        # GIVEN
        handler = ArnoldHandler()
        return_cameras = [
            MockCamera("camera1", renderable=False),
            MockCamera("camera2", renderable=False),
        ]
        mock_ls.return_value = return_cameras

        handler.cameras = cameras
        handler.render_kwargs = {"height": 1000, "width": 1000}
        # WHEN
        with pytest.raises(RuntimeError) as exc_info:
            handler.start_render(args)

        # THEN
        assert str(exc_info.value) == (
            "No camera was specified, and no renderable camera could be found."
        )
        mock_render.assert_not_called()

    render_kwarg_params = [
        pytest.param({"camera": "camera1", "width": 1000, "batch": True}, id="Render No Width"),
        pytest.param({"camera": "camera1", "height": 1000, "batch": True}, id="Render No Height"),
        pytest.param({"camera": "camera1", "batch": True}, id="Render No Width or Height"),
    ]

    @pytest.mark.parametrize("render_kwargs", render_kwarg_params)
    @pytest.mark.parametrize("args", [{"frame": 99}])
    @patch.object(pm, "arnoldRender")
    @patch.object(pm, "SCENE")
    @patch.object(pm, "ls")
    def test_start_render_no_width_or_height(
        self,
        mock_ls: Mock,
        mock_scene: Mock,
        mock_render: Mock,
        render_kwargs: Dict[str, Any],
        args: Dict[str, Any],
        capsys,
    ) -> None:
        """
        Tests that starting a render without a width or height results in the default width/height
        being used
        """
        # GIVEN
        DEFAULT_HEIGHT = 62
        DEFAULT_WIDTH = 490

        handler = ArnoldHandler()
        handler.render_kwargs = render_kwargs
        return_cameras = [
            MockCamera("camera1", renderable=False),
            MockCamera("camera2", renderable=False),
        ]
        mock_ls.return_value = return_cameras
        mock_scene.defaultResolution.width.get.return_value = DEFAULT_WIDTH
        mock_scene.defaultResolution.height.get.return_value = DEFAULT_HEIGHT

        # WHEN
        handler.start_render(args)

        # THEN
        if "width" not in render_kwargs:
            assert f"No width was specified, defaulting to {DEFAULT_WIDTH}" in capsys
            mock_scene.defaultResolution.width.get.assert_called_once
            render_kwargs["width"] = DEFAULT_WIDTH  # preparing for render call assertion
        if "height" not in render_kwargs:
            assert f"No height was specified, defaulting to {DEFAULT_HEIGHT}" in capsys
            mock_scene.defaultResolution.height.get.assert_called_once
            render_kwargs["height"] = DEFAULT_HEIGHT  # preparing for render call assertion

        mock_render.assert_called_once_with(**render_kwargs)

    @pytest.mark.parametrize("args", [{"image_height": 1500}])
    def test_set_image_height(self, args: Dict[str, Any]) -> None:
        """Tests that setting the image height sets the right render kwarg"""
        # GIVEN
        handler = ArnoldHandler()

        # WHEN
        handler.set_image_height(args)

        # THEN
        assert handler.render_kwargs["height"] == args["image_height"]

    @pytest.mark.parametrize("args", [{"image_width": 1500}])
    def test_set_image_width(self, args: Dict[str, Any]) -> None:
        """Tests that setting the image width sets the right render kwarg"""
        # GIVEN
        handler = ArnoldHandler()

        # WHEN
        handler.set_image_width(args)

        # THEN
        assert handler.render_kwargs["width"] == args["image_width"]
