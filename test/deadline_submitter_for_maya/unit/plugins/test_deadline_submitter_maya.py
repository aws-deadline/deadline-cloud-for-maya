# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import re
from collections import namedtuple
from typing import Any
from unittest.mock import Mock, call, patch

import maya.cmds
import maya.api.OpenMaya as om  # pylint: disable=import-error
import pytest

import deadline
from deadline.maya_submitter import maya_render_submitter
from deadline.maya_submitter import mel_commands
import DeadlineCloudForMaya

Command = namedtuple("Command", ["name", "cmdCreator"])  # Mock Command Class


@patch.object(DeadlineCloudForMaya, "reload")
def test_reload_modules(mock_reload: Mock) -> None:
    # GIVEN a random subset of the deadline.maya_submitter modules
    from deadline.maya_submitter import mel_commands, scene, ui
    from deadline.maya_submitter.ui import components

    modules = [scene, mel_commands, components, ui, maya_render_submitter]

    # WHEN
    DeadlineCloudForMaya.reload_modules(deadline.maya_submitter)

    # THEN it should have called reload on at least the ones we stated
    mock_reload.assert_has_calls([call(module) for module in modules], any_order=True)


@patch.object(om.MGlobal, "mayaState")
@patch.object(om, "MFnPlugin")
@patch.object(DeadlineCloudForMaya, "reload")
@patch.object(deadline.maya_submitter.shelf, "build_shelf")
def test_initialize_and_uninitialize_plugin(
    mock_build_shelf: Mock,
    mock_reload: Mock,
    mock_MFnPlugin: Mock,
    mock_mayaState: Mock,
) -> None:
    # GIVEN
    plugin = Mock()
    plugin_obj = Mock()
    mock_MFnPlugin.return_value = plugin_obj
    mock_mayaState.return_value = om.MGlobal.kInteractive

    # WHEN
    DeadlineCloudForMaya.initializePlugin(plugin)

    # THEN
    class VersionMatcher:
        """Matches any properly formed semantic version string"""

        VERSION_REGEX = re.compile(r"^\d+\.\d+\.\d+$")

        def __eq__(self, other: Any) -> bool:
            return bool(VersionMatcher.VERSION_REGEX.match(other))

    mock_MFnPlugin.assert_called_once_with(plugin, "AWS Thinkbox", VersionMatcher())

    plugin_obj.registerCommand.assert_called_once_with(
        "DeadlineCloudSubmitter", mel_commands.DeadlineCloudSubmitterCmd
    )
    mock_build_shelf.assert_called_once_with()

    # GIVEN
    plugin_obj.reset_mock()
    mock_MFnPlugin.reset_mock()

    # WHEN
    DeadlineCloudForMaya.uninitializePlugin(plugin)

    # THEN
    mock_MFnPlugin.assert_called_once_with(plugin)
    plugin_obj.deregisterCommand.assert_called_once_with("DeadlineCloudSubmitter")


@patch.object(maya.cmds, "confirmDialog")
@patch.object(
    DeadlineCloudForMaya,
    "reload",
    side_effect=Exception("something bad happened"),
)
def test_initialize_plugin_exc(mock_reload: Mock, mock_confirm_dialog: Mock) -> None:
    # GIVEN

    # WHEN
    with pytest.raises(Exception) as exc_info:
        DeadlineCloudForMaya.initializePlugin(Mock())

    # THEN
    assert exc_info.value is mock_reload.side_effect
    mock_confirm_dialog.assert_called_once_with(
        title="Deadline Cloud For Maya Plugin Failed To Load",
        message=(
            "Encountered the following exception while loading the Deadline Cloud Submitter:\n"
            f"{str(exc_info.value)}"
        ),
        button="OK",
        defaultButton="OK",
    )
