# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from deadline.maya_adaptor.MayaClient.dir_map import DirectoryMapping, DirectoryMappingDict
from deadline.maya_adaptor.MayaClient.render_handlers import DefaultMayaHandler


@pytest.fixture()
def mayahandlerbase():
    return DefaultMayaHandler()


class TestDefaultMayaHandler:
    @pytest.mark.parametrize("args", [{"image_height": 1500}])
    def test_set_image_height(self, mayahandlerbase: DefaultMayaHandler, args: dict):
        """Tests that setting the image height calls the correct functions"""
        # WHEN
        mayahandlerbase.set_image_height(args)

        # THEN
        assert mayahandlerbase.image_height == args["image_height"]

    @pytest.mark.parametrize("args", [{"image_width": 1500}])
    def test_set_image_width(self, mayahandlerbase: DefaultMayaHandler, args: dict):
        """Tests that setting the image width calls the correct functions"""
        # WHEN
        mayahandlerbase.set_image_width(args)

        # THEN
        assert mayahandlerbase.image_width == args["image_width"]

    set_render_layer_args = [
        (
            {"render_layer": "layer1"},
            ["layer1", "layer2", "layer3"],
        )
    ]

    @pytest.mark.parametrize("args", [{"path_mapping_rules": {}}])
    @patch.object(DirectoryMapping.mappings, "__setitem__")
    @patch.object(DirectoryMapping, "set_activated")
    def test_set_path_mapping_no_rules(
        self,
        mock_mapping_activated: Mock,
        mock_set_mappings: Mock,
        mayahandlerbase: DefaultMayaHandler,
        args: dict,
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
        mayahandlerbase: DefaultMayaHandler,
        args: dict,
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

    @pytest.mark.parametrize(
        "args,file_exists",
        [
            ({"scene_file": "/path/to/scene.ma"}, True),
        ],
    )
    @patch("os.path.isfile")
    @patch("deadline.maya_adaptor.MayaClient.render_handlers.default_maya_handler.maya.cmds.file")
    @patch(
        "deadline.maya_adaptor.MayaClient.render_handlers.default_maya_handler.maya.cmds.getAttr"
    )
    @patch("deadline.maya_adaptor.MayaClient.render_handlers.default_maya_handler.maya.mel.eval")
    def test_set_scene_file(
        self,
        mock_mel_eval: Mock,
        mock_get_attr: Mock,
        mock_file: Mock,
        mock_isfile: Mock,
        mayahandlerbase: DefaultMayaHandler,
        args: dict,
        file_exists: bool,
    ):
        """
        Test that set_scene_file calls maya.cmds.file with the correct arguments
        and handles pre-render MEL scripts if they exist.
        """
        # GIVEN
        mock_isfile.return_value = file_exists
        mock_get_attr.return_value = "some_mel_script"

        # WHEN
        mayahandlerbase.set_scene_file(args)

        # THEN
        mock_isfile.assert_called_once_with(args["scene_file"])
        mock_file.assert_called_once_with(
            args["scene_file"], open=True, force=True, ignoreVersion=True
        )
        mock_get_attr.assert_called_once_with("defaultRenderGlobals.preMel")
        mock_mel_eval.assert_called_once_with(mock_get_attr.return_value)

    @pytest.mark.parametrize(
        "args,file_exists",
        [
            ({"scene_file": "/path/to/scene.ma"}, True),
        ],
    )
    @patch("os.path.isfile")
    @patch("deadline.maya_adaptor.MayaClient.render_handlers.default_maya_handler.maya.cmds.file")
    @patch(
        "deadline.maya_adaptor.MayaClient.render_handlers.default_maya_handler.maya.cmds.getAttr"
    )
    @patch("deadline.maya_adaptor.MayaClient.render_handlers.default_maya_handler.maya.mel.eval")
    def test_set_scene_file_no_pre_mel(
        self,
        mock_mel_eval: Mock,
        mock_get_attr: Mock,
        mock_file: Mock,
        mock_isfile: Mock,
        mayahandlerbase: DefaultMayaHandler,
        args: dict,
        file_exists: bool,
    ):
        """
        Test that set_scene_file doesn't call maya.mel.eval when there's no pre-render MEL script.
        """
        # GIVEN
        mock_isfile.return_value = file_exists
        mock_get_attr.return_value = ""  # No pre-render MEL script

        # WHEN
        mayahandlerbase.set_scene_file(args)

        # THEN
        mock_isfile.assert_called_once_with(args["scene_file"])
        mock_file.assert_called_once_with(
            args["scene_file"], open=True, force=True, ignoreVersion=True
        )
        mock_get_attr.assert_called_once_with("defaultRenderGlobals.preMel")
        mock_mel_eval.assert_not_called()

    @pytest.mark.parametrize(
        "args",
        [
            ({"scene_file": "/path/to/nonexistent.ma"}),
        ],
    )
    @patch("os.path.isfile")
    def test_set_scene_file_not_found(
        self,
        mock_isfile: Mock,
        mayahandlerbase: DefaultMayaHandler,
        args: dict,
    ):
        """
        Test that set_scene_file raises FileNotFoundError when the scene file doesn't exist.
        """
        # GIVEN
        mock_isfile.return_value = False

        # WHEN/THEN
        with pytest.raises(
            FileNotFoundError, match=f"The scene file '{args['scene_file']}' does not exist"
        ):
            mayahandlerbase.set_scene_file(args)
