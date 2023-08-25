# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import re
from collections import namedtuple
from typing import Any
from unittest.mock import Mock, call, patch

import maya.api.OpenMaya as om  # pylint: disable=import-error
import pytest

from deadline_submitter_for_maya.plugins import DeadlineSubmitter
from deadline_submitter_for_maya.scripts import aws_deadline

Command = namedtuple("Command", ["name", "cmdCreator"])  # Mock Command Class


def test_root_directory() -> None:
    # GIVEN
    root_dir = os.path.dirname(os.path.dirname(DeadlineSubmitter.__file__))  # type: ignore

    # THEN
    assert DeadlineSubmitter.root_directory() == root_dir


@patch.object(DeadlineSubmitter, "reload")
def test_reload_modules(mock_reload: Mock) -> None:
    # GIVEN a random subset of the aws_deadline modules
    from deadline_submitter_for_maya.scripts.aws_deadline import commands, scene, ui
    from deadline_submitter_for_maya.scripts.aws_deadline.ui import components

    modules = [scene, commands, components, ui, aws_deadline]

    # WHEN
    DeadlineSubmitter.reload_modules(aws_deadline)

    # THEN it should have called reload on at least the ones we stated
    mock_reload.assert_has_calls([call(module) for module in modules], any_order=True)


@patch.object(om.MGlobal, "mayaState")
@patch.object(om, "MFnPlugin")
@patch.object(DeadlineSubmitter, "reload")
@patch.object(aws_deadline.commands, "get_commands")
@patch.object(aws_deadline.shelf, "build_shelf")
def test_initialize_plugin(
    mock_build_shelf: Mock,
    mock_get_commands: Mock,
    mock_reload: Mock,
    mock_MFnPlugin: Mock,
    mock_mayaState: Mock,
) -> None:
    # GIVEN
    plugin = Mock()
    plugin_obj = Mock()
    mock_MFnPlugin.return_value = plugin_obj
    commands_ref = [Command(f"Command{i}", Mock()) for i in range(3)]
    mock_get_commands.return_value = commands_ref
    mock_mayaState.return_value = om.MGlobal.kInteractive

    # WHEN
    DeadlineSubmitter.initializePlugin(plugin)

    # THEN
    class VersionMatcher:
        """Matches any properly formed semantic version string"""

        VERSION_REGEX = re.compile(r"^\d+\.\d+\.\d+$")

        def __eq__(self, other: Any) -> bool:
            return bool(VersionMatcher.VERSION_REGEX.match(other))

    mock_MFnPlugin.assert_called_once_with(plugin, "AWS Thinkbox", VersionMatcher())
    mock_get_commands.assert_called_once()

    calls = [call(cmd.name, cmd.cmdCreator) for cmd in commands_ref]
    plugin_obj.registerCommand.assert_has_calls(calls)

    mock_build_shelf.assert_called_once()


@patch.object(DeadlineSubmitter, "confirmDialog")
@patch.object(
    DeadlineSubmitter,
    "reload",
    side_effect=Exception("something bad happened"),
)
def test_initialize_plugin_exc(mock_reload: Mock, mock_confirm_dialog: Mock) -> None:
    # GIVEN

    # WHEN
    with pytest.raises(Exception) as exc_info:
        DeadlineSubmitter.initializePlugin(Mock())

    # THEN
    assert exc_info.value is mock_reload.side_effect
    mock_confirm_dialog.assert_called_once_with(
        title="Failed To Load Deadline Submitter",
        message=(
            "Encountered the following exception while loading the Deadline Submitter:\n"
            f"{str(exc_info.value)}"
        ),
        button=["Close"],
    )


@patch.object(om, "MFnPlugin")
@patch.object(aws_deadline.commands, "get_commands")
def test_uninitialize_plugin(mock_get_commands: Mock, mock_MFnPlugin: Mock) -> None:
    # GIVEN
    plugin = Mock()
    plugin_obj = Mock()
    mock_MFnPlugin.return_value = plugin_obj
    commands = [Command(f"Command{i}", Mock()) for i in range(3)]
    mock_get_commands.return_value = commands
    # WHEN
    DeadlineSubmitter.uninitializePlugin(plugin)

    # THEN
    mock_MFnPlugin.assert_called_once_with(plugin)
    calls = [call(cmd.name) for cmd in commands]
    plugin_obj.deregisterCommand.assert_has_calls(calls)
