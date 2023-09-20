# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
This file contains the logic that is used to load/unload our plugin
"""

from __future__ import absolute_import, annotations, print_function

import os
import logging
import types
from typing import List
from importlib import reload

import maya.api.OpenMaya as om  # pylint: disable=import-error
import maya.cmds

import deadline.maya_submitter
from deadline.maya_submitter import mel_commands, shelf  # type: ignore[import, no-redef]

# Tells maya which version of their api to use.
maya_useNewAPI = True
VENDOR = "AWS Thinkbox"
VERSION = "0.6.0"

__log__ = logging.getLogger("Deadline")
_registered_mel_commands: List[str] = []
_first_initialization: bool = True


def reload_modules(mod):
    """
    Recursively reloads all modules in the specified package, in postfix order
    """
    child_mods = [
        m
        for m in mod.__dict__.values()
        if isinstance(m, types.ModuleType)
        and m.__package__
        and m.__package__.startswith(mod.__package__)
    ]

    for child in child_mods:
        reload_modules(mod=child)

    __log__.debug(f"Reloading {mod}")
    reload(mod)


def initializePlugin(plugin):
    """
    Initialize the DeadlineSubmitter plugin.
    """
    global _registered_mel_commands, _first_initialization
    try:
        plugin_obj = om.MFnPlugin(plugin, VENDOR, VERSION)

        if _first_initialization:
            _first_initialization = False
        else:
            # If a user unloaded and then reloaded the plugin, refresh
            # some key module dependencies.
            reload_modules(deadline.job_attachments)
            reload_modules(deadline.client)
            reload_modules(deadline.maya_submitter)

        command_name = "DeadlineCloudSubmitter"
        plugin_obj.registerCommand(command_name, mel_commands.DeadlineCloudSubmitterCmd)
        _registered_mel_commands.append(command_name)

        if os.environ.get("DEADLINE_ENABLE_DEVELOPER_OPTIONS", "").upper() == "TRUE":
            command_name = "DeadlineCloudJobBundleOutputTests"
            plugin_obj.registerCommand(
                command_name, mel_commands.DeadlineCloudJobBundleOutputTestsCmd
            )
            _registered_mel_commands.append(command_name)

        # Build the shelf if we are in UI mode
        if om.MGlobal.mayaState() in [om.MGlobal.kInteractive, om.MGlobal.kBaseUIMode]:
            shelf.build_shelf()

    except Exception as e:
        maya.cmds.confirmDialog(
            title="Deadline Cloud For Maya Plugin Failed To Load",
            message=(
                "Encountered the following exception while loading the Deadline Cloud Submitter:\n"
                f"{str(e)}"
            ),
            button="OK",
            defaultButton="OK",
        )
        raise


def uninitializePlugin(plugin):
    """
    Uninitialze the plugin by deregistering all commands.
    """
    plugin_obj = om.MFnPlugin(plugin)

    __log__ = deadline.maya_submitter.logger()

    for command_name in _registered_mel_commands:
        try:
            plugin_obj.deregisterCommand(command_name)
        except Exception:
            __log__.error(f"Failed to deregister command: {command_name}\n")
            raise
    _registered_mel_commands.clear()
