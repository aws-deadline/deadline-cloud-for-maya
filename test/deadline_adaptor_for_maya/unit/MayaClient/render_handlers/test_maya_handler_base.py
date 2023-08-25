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
        assert mayahandlerbase.render_kwargs["yresolution"] == args["image_height"]

    @pytest.mark.parametrize("args", [{"image_width": 1500}])
    def test_set_image_width(self, mayahandlerbase: DefaultMayaHandler, args: dict):
        """Tests that setting the image width calls the correct functions"""
        # WHEN
        mayahandlerbase.set_image_width(args)

        # THEN
        assert mayahandlerbase.render_kwargs["xresolution"] == args["image_width"]

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
