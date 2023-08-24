# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from typing import Dict, List, Optional
from unittest.mock import Mock, patch

import pymel.core as pm
import pytest

import deadline_adaptor_for_maya.MayaClient.render_handlers.maya_handler_base as maya_handler_module
from deadline_adaptor_for_maya.MayaClient.pymel_additions import (
    DirectoryMapping,
    DirectoryMappingDict,
)
from deadline_adaptor_for_maya.MayaClient.render_handlers import MayaHandlerBase

from .mock_stubs import MockCamera


@pytest.fixture()
def mayahandlerbase():
    return MayaHandlerBase()


class TestMayaHandlerBase:
    @pytest.mark.parametrize("args", [{"frame": 99}])
    @patch.object(pm, "render")
    @patch.object(pm, "SCENE")
    def test_start_render(
        self, mock_scene: Mock, mock_render: Mock, mayahandlerbase: MayaHandlerBase, args: Dict
    ):
        """Tests that starting a render calls the correct pymel functions"""
        # GIVEN
        mayahandlerbase.cameras = ["camera1"]
        mayahandlerbase.render_kwargs = {"yresolution": 1000, "xresolution": 1000}
        # WHEN
        mayahandlerbase.start_render(args)

        # THEN
        mock_scene.defaultRenderGlobals.startFrame.set.assert_called_once_with(args["frame"])
        mock_scene.defaultRenderGlobals.endFrame.set.assert_called_once_with(args["frame"])
        mock_render.assert_called_once_with(
            mayahandlerbase.cameras, **mayahandlerbase.render_kwargs
        )

    @pytest.mark.parametrize("args", [{}])
    @patch.object(pm, "render")
    @patch.object(pm, "SCENE")
    def test_start_render_no_frame(
        self, mock_scene: Mock, mock_render: Mock, mayahandlerbase: MayaHandlerBase, args: Dict
    ):
        # GIVEN
        mayahandlerbase.cameras = ["camera1"]
        mayahandlerbase.render_kwargs = {"yresolution": 1000, "xresolution": 1000}
        # WHEN
        with pytest.raises(RuntimeError) as exc_info:
            mayahandlerbase.start_render(args)

        # THEN
        assert str(exc_info.value) == "MayaClient: start_render called without a frame number."
        mock_render.assert_not_called()

    @pytest.mark.parametrize("cameras", [None, []])
    @pytest.mark.parametrize("args", [{"frame": 99}])
    @patch.object(pm, "render")
    @patch.object(pm, "SCENE")
    @patch.object(pm, "ls")
    def test_start_render_no_camera(
        self,
        mock_ls: Mock,
        mock_scene: Mock,
        mock_render: Mock,
        mayahandlerbase: MayaHandlerBase,
        cameras: Optional[List],
        args: Dict,
        capsys,
    ):
        """Tests that starting a render without a camera calls the correct pymel functions"""
        # GIVEN
        return_cameras = [MockCamera("camera1"), MockCamera("camera2"), MockCamera("camera3")]
        mock_ls.return_value = return_cameras

        mayahandlerbase.cameras = cameras
        mayahandlerbase.render_kwargs = {"yresolution": 1000, "xresolution": 1000}
        # WHEN
        mayahandlerbase.start_render(args)

        # THEN
        stdout = capsys.readouterr().out
        assert "No camera was specified, defaulting to render on all renderable cameras." in stdout
        assert mayahandlerbase.cameras == return_cameras
        assert f"Rendering on cameras: {[c.name for c in return_cameras]}" in stdout
        mock_scene.defaultRenderGlobals.startFrame.set.assert_called_once_with(args["frame"])
        mock_scene.defaultRenderGlobals.endFrame.set.assert_called_once_with(args["frame"])
        mock_render.assert_called_once_with(return_cameras, **mayahandlerbase.render_kwargs)

    @pytest.mark.parametrize("cameras", [None, []])
    @pytest.mark.parametrize("args", [{"frame": 99}])
    @patch.object(pm, "render")
    @patch.object(pm, "SCENE")
    @patch.object(pm, "ls")
    def test_start_render_no_camera_found(
        self,
        mock_ls: Mock,
        mock_scene: Mock,
        mock_render: Mock,
        mayahandlerbase: MayaHandlerBase,
        cameras: Optional[List],
        args: Dict,
        capsys,
    ):
        """Tests that starting a render without a camera raises an error if no camera is found"""
        # GIVEN
        return_cameras = [
            MockCamera("camera1", renderable=False),
            MockCamera("camera2", renderable=False),
        ]
        mock_ls.return_value = return_cameras

        mayahandlerbase.cameras = cameras
        mayahandlerbase.render_kwargs = {"yresolution": 1000, "xresolution": 1000}
        # WHEN
        with pytest.raises(RuntimeError) as exc_info:
            mayahandlerbase.start_render(args)

        # THEN
        stdout = capsys.readouterr().out
        assert "No camera was specified, defaulting to render on all renderable cameras." in stdout
        assert str(exc_info.value) == (
            "No camera was specified, and no renderable camera could be found."
        )
        mock_render.assert_not_called()

    @pytest.mark.parametrize("args", [{"animation": True}, {"animation": False}])
    @patch.object(pm, "SCENE")
    def test_set_animation(self, mock_scene: Mock, mayahandlerbase: MayaHandlerBase, args: Dict):
        """Tests that setting the animation calls the correct pymel functions"""
        # When
        mayahandlerbase.set_animation(args)

        # Then
        mock_scene.defaultRenderGlobals.animation.set.assert_called_once_with(args["animation"])

    set_camera_args = [
        (
            {"camera": "camera3"},
            [MockCamera("camera1"), MockCamera("camera2"), MockCamera("camera3")],
            [MockCamera("camera3")],
        ),
        (
            {"camera": "camera3"},
            [MockCamera("cameraShape1"), MockCamera("cameraShape2"), MockCamera("cameraShape3")],
            [MockCamera("cameraShape3")],
        ),
    ]

    @pytest.mark.parametrize("args, ls_return_value, expected", set_camera_args)
    def test_set_camera(
        self,
        mayahandlerbase: MayaHandlerBase,
        args: Dict,
        ls_return_value: List[MockCamera],
        expected: List[MockCamera],
    ):
        """Tests that setting the camera calls the correct pymel functions"""
        # GIVEN
        pm.ls.return_value = ls_return_value

        # WHEN
        mayahandlerbase.set_camera(args)

        # THEN
        assert mayahandlerbase.cameras == expected

    def test_set_camera_empty_name(self, mayahandlerbase: MayaHandlerBase):
        """Tests that setting a nonexistent camera raises the correct error"""
        # WHEN
        with pytest.raises(RuntimeError) as exc_info:
            mayahandlerbase.set_camera({"camera": ""})

        # THEN
        expected_msg = "MayaClient: set_camera was called without providing a camera name."
        assert str(exc_info.value) == expected_msg

    set_nonexistent_camera_args = [
        (
            {"camera": "camera4"},
            [MockCamera("camera1"), MockCamera("camera2"), MockCamera("camera3")],
        ),
    ]

    @pytest.mark.parametrize("args, ls_return_value", set_nonexistent_camera_args)
    def test_set_nonexistent_camera(
        self,
        mayahandlerbase: MayaHandlerBase,
        args: Dict,
        ls_return_value: List[MockCamera],
    ):
        """Tests that setting a nonexistent camera raises the correct error"""
        # GIVEN
        pm.ls.return_value = ls_return_value

        # WHEN
        with pytest.raises(RuntimeError) as exc_info:
            mayahandlerbase.set_camera(args)

        # THEN
        expected_msg = f"The camera '{args['camera']}' does not exist."
        assert str(exc_info.value) == expected_msg

    set_nonrenderable_camera_args = [
        (
            {"camera": "camera1"},
            [MockCamera("camera1", renderable=False), MockCamera("camera2"), MockCamera("camera3")],
        ),
    ]

    @pytest.mark.parametrize("args, ls_return_value", set_nonrenderable_camera_args)
    def test_set_nonrenderable_camera(
        self,
        mayahandlerbase: MayaHandlerBase,
        args: Dict,
        ls_return_value: List[MockCamera],
    ):
        """Tests that setting a non renderable camera raises the correct error"""
        # GIVEN
        pm.ls.return_value = ls_return_value

        # WHEN
        with pytest.raises(RuntimeError) as exc_info:
            mayahandlerbase.set_camera(args)

        # THEN
        expected_msg = f"The camera '{args['camera']}' is not renderable."
        assert str(exc_info.value) == expected_msg

    @pytest.mark.parametrize("args", [{"image_height": 1500}])
    def test_set_image_height(self, mayahandlerbase: MayaHandlerBase, args: Dict):
        """Tests that setting the image height calls the correct pymel functions"""
        # WHEN
        mayahandlerbase.set_image_height(args)

        # THEN
        assert mayahandlerbase.render_kwargs["yresolution"] == args["image_height"]

    @pytest.mark.parametrize("args", [{"image_width": 1500}])
    def test_set_image_width(self, mayahandlerbase: MayaHandlerBase, args: Dict):
        """Tests that setting the image width calls the correct pymel functions"""
        # WHEN
        mayahandlerbase.set_image_width(args)

        # THEN
        assert mayahandlerbase.render_kwargs["xresolution"] == args["image_width"]

    @pytest.mark.parametrize("args", [{"output_file_path": "this/is/a/path"}])
    @patch.object(pm, "workspace")
    def test_set_output_file_path(
        self, mock_workspace: Mock, mayahandlerbase: MayaHandlerBase, args: Dict
    ):
        """Tests that setting the output file path calls the correct pymel functions"""
        # WHEN
        mayahandlerbase.set_output_file_path(args)

        # THEN
        mock_workspace.fileRules.__setitem__.assert_called_once_with(
            "images", args["output_file_path"]
        )

    @pytest.mark.parametrize("args", [{"output_file_prefix": "<some>/<prefix>"}])
    @patch.object(pm, "SCENE")
    def test_set_output_file_prefix(self, mock_scene, mayahandlerbase: MayaHandlerBase, args: Dict):
        """Tests that setting the output file prefix calls the correct pymel functions"""
        # WHEN
        mayahandlerbase.set_output_file_prefix(args)

        # THEN
        mock_scene.defaultRenderGlobals.imageFilePrefix.set.assert_called_once_with(
            args["output_file_prefix"]
        )

    @pytest.mark.parametrize("args", [{"project_path": "a/project/path"}])
    @patch.object(maya_handler_module._os, "makedirs")
    @patch.object(pm, "workspace")
    def test_set_project_path(
        self,
        mock_workspace: Mock,
        mock_makedirs: Mock,
        mayahandlerbase: MayaHandlerBase,
        args: Dict,
    ):
        """Tests that setting the project path calls the correct pymel functions"""
        # WHEN
        mayahandlerbase.set_project_path(args)

        # THEN
        mock_makedirs.assert_called_once_with(args["project_path"], exist_ok=True)
        mock_workspace.open.assert_called_once_with(args["project_path"])

    set_render_layer_args = [
        (
            {"render_layer": "layer1"},
            ["layer1", "layer2", "layer3"],
        )
    ]

    @pytest.mark.parametrize("args, ls_return_value", set_render_layer_args)
    def test_set_render_layer(
        self, mayahandlerbase: MayaHandlerBase, args: Dict, ls_return_value: List[str]
    ):
        """Tests that setting the render layer calls the correct pymel functions"""
        # GIVEN
        pm.ls.return_value = ls_return_value

        # WHEN
        mayahandlerbase.set_render_layer(args)

        # THEN
        assert mayahandlerbase.render_kwargs["layer"] == args["render_layer"]

    set_nonexistent_render_layer_args = [
        (
            {"render_layer": "layer4"},
            ["layer1", "layer2", "layer3"],
        )
    ]

    @pytest.mark.parametrize("args, ls_return_value", set_nonexistent_render_layer_args)
    def test_set_nonexistent_render_layer(
        self, mayahandlerbase: MayaHandlerBase, args: Dict, ls_return_value: List[str]
    ):
        """Tests that setting a nonexistent render layer calls the correct pymel functions"""

        # GIVEN
        pm.ls.return_value = ls_return_value

        # WHEN
        with pytest.raises(RuntimeError) as exc_info:
            mayahandlerbase.set_render_layer(args)

        # THEN
        assert str(exc_info.value) == (
            f"Error: Render layer '{args['render_layer']}' not found. Available render layers "
            f"are: {ls_return_value}"
        )
        assert "layer" not in mayahandlerbase.render_kwargs

    @pytest.mark.parametrize(
        "args", [{"render_setup_include_lights": True}, {"render_setup_include_lights": False}]
    )
    @patch.object(pm, "optionVar")
    def test_set_render_setup_include_lights(
        self, mock_option_var, mayahandlerbase: MayaHandlerBase, args: Dict
    ):
        """Tests that setting render_setup_include_lights calls the correct pymel functions"""
        # WHEN
        mayahandlerbase.set_render_setup_include_lights(args)

        # THEN
        mock_option_var.__setitem__.assert_called_once_with(
            "renderSetup_includeAllLights", int(args["render_setup_include_lights"])
        )

    @pytest.mark.parametrize("args", [{"scene_file": "a/scene/path.mb"}])
    @patch("os.path.isfile", return_value=True)
    @patch.object(pm, "openFile")
    def test_set_scene_file(
        self, mock_open: Mock, mock_isfile: Mock, mayahandlerbase: MayaHandlerBase, args: Dict
    ):
        """Tests that setting the scene file calls the correct pymel functions"""
        # WHEN
        mayahandlerbase.set_scene_file(args)

        # THEN
        mock_isfile.assert_called_once_with(args["scene_file"])
        mock_open.assert_called_once_with(args["scene_file"], force=True)

    @pytest.mark.parametrize("args", [{"scene_file": "a/scene/path.mb"}])
    @patch("os.path.isfile", return_value=False)
    @patch.object(pm, "openFile")
    def test_set_nonexistent_scene_file(
        self, mock_open: Mock, mock_isfile: Mock, mayahandlerbase: MayaHandlerBase, args: Dict
    ):
        """Tests that setting a nonexistent scene file calls the correct pymel functions"""
        # WHEN
        with pytest.raises(FileNotFoundError) as exc_info:
            mayahandlerbase.set_scene_file(args)

        # THEN
        assert str(exc_info.value) == f"The scene file '{args['scene_file']}' does not exist"
        mock_isfile.assert_called_once_with(args["scene_file"])
        mock_open.assert_not_called()

    @pytest.mark.parametrize("args", [{"path_mapping_rules": {}}])
    @patch.object(DirectoryMapping.mappings, "__setitem__")
    @patch.object(DirectoryMapping, "set_activated")
    def test_set_path_mapping_no_rules(
        self,
        mock_mapping_activated: Mock,
        mock_set_mappings: Mock,
        mayahandlerbase: MayaHandlerBase,
        args: Dict,
    ):
        """Tests that calling set_pathmapping with no rules will not activate pathmapping"""
        # WHEN
        mayahandlerbase.set_path_mapping(args)

        # THEN
        mock_mapping_activated.assert_not_called()
        mock_set_mappings.assert_not_called()

    @pytest.mark.parametrize(
        "args",
        [
            {"path_mapping_rules": {"test": "val"}},
            {"path_mapping_rules": {"test": "val", "source": "dest"}},
        ],
    )
    @patch.object(DirectoryMappingDict, "__setitem__")
    @patch.object(DirectoryMapping, "set_activated")
    def test_set_path_mapping_with_rules(
        self,
        mock_mapping_activated: Mock,
        mock_set_mappings: Mock,
        mayahandlerbase: MayaHandlerBase,
        args: Dict,
    ):
        """
        Test that when pathmapping is set that pathmaping is activated in Maya,
        and that pathmapping rules are configured.
        """
        # WHEN
        mayahandlerbase.set_path_mapping(args)

        # THEN
        mock_mapping_activated.assert_called_once_with(True)
        assert mock_set_mappings.call_count == len(args["path_mapping_rules"])
