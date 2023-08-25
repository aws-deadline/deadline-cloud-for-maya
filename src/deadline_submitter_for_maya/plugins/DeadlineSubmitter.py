# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
This file contains the logic that is used to load/unload our plugin
"""

from __future__ import absolute_import, annotations, print_function

import inspect
import logging
import os
import types
from importlib import reload

import maya.api.OpenMaya as om  # pylint: disable=import-error
from pymel.core import confirmDialog

if hasattr(om, "Anything"):
    # Testing context (om is a MagicMock)
    from ..scripts import aws_deadline
    from ..scripts.aws_deadline import commands, shelf
else:
    # In Maya
    import aws_deadline  # type: ignore[import, no-redef]
    from aws_deadline import commands, shelf  # type: ignore[import, no-redef]

# Tells maya which version of their api to use.
maya_useNewAPI = True
VENDOR = "AWS Thinkbox"
VERSION = "0.6.0"

__log__ = logging.getLogger("Deadline")


def root_directory():
    """
    Returns the path to the base directory from which this plugin is run.
    """
    try:
        this_file_path = __file__
    except NameError:
        # inside an interpreter, we can use the stack to find the file
        # path.
        this_file_path = os.path.abspath(inspect.stack()[0][1])
    return os.path.dirname(os.path.dirname(this_file_path))


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
    try:
        plugin_obj = om.MFnPlugin(plugin, VENDOR, VERSION)

        reload_modules(aws_deadline)
        __log__ = aws_deadline.logger()

        __log__.debug("Registering Commands")
        for command in commands.get_commands():
            try:
                __log__.debug("Attempting to register command: {}".format(command.name))
                plugin_obj.registerCommand(command.name, command.cmdCreator)
            except Exception:
                __log__.error("Failed to register command: %s\n" % command.name)
                raise

        # Build the shelf if we are in UI mode
        if om.MGlobal.mayaState() in [om.MGlobal.kInteractive, om.MGlobal.kBaseUIMode]:
            __log__.debug("Building Shelf")
            shelf.build_shelf()

        __log__.debug("Finished Initialization")
    except Exception as e:
        confirmDialog(
            title="Failed To Load Deadline Submitter",
            message=(
                "Encountered the following exception while loading the Deadline Submitter:\n"
                f"{str(e)}"
            ),
            button=["Close"],
        )
        raise


def uninitializePlugin(plugin):
    """
    Uninitialze the plugin by deregistering all commands.
    """
    plugin_obj = om.MFnPlugin(plugin)

    __log__ = aws_deadline.logger()

    for command in commands.get_commands():
        try:
            plugin_obj.deregisterCommand(command.name)
        except Exception:
            __log__.error("Failed to deregister command: %s\n" % command.name)
            raise
