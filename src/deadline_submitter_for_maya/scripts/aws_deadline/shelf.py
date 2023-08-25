# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Functionality used to build the Deadline shelf.
"""
import json
import os
from typing import TYPE_CHECKING, Any, Dict

import pymel.core as pmc  # pylint: disable=import-errorz

if TYPE_CHECKING:
    from pymel.core.uitypes import (
        ShelfTabLayout as pm_ShelfTabLayout,
    )  # pylint: disable=import-error

from . import config

SHELF_FILE_NAME = "shelf.json"


def get_root_tab() -> "pm_ShelfTabLayout":
    """
    Returns the object representing the Root Shelf tab.
    """

    root_name = pmc.melGlobals["gShelfTopLevel"]
    return pmc.ui.ShelfTabLayout(root_name)


def get_shelf_json() -> Dict[str, Any]:
    """
    Returns the shelf json files contents.
    """
    shelf_fname = os.path.join(config.config_dir, SHELF_FILE_NAME)
    with open(shelf_fname, "r", encoding="utf-8") as shelf_file:
        return json.load(shelf_file)


def build_shelf() -> None:
    """
    Builds the Deadline Maya Shelf as defined in the shelf.json configuration file..
    """

    root = get_root_tab()
    selected_name = root.getSelectTab()

    shelf_config = get_shelf_json()
    shelf_name = shelf_config["Shelf"]["shelfID"]
    shelf_version = shelf_config["Shelf"].get("version", 0)

    work_shelf = root.findChild(shelf_name)
    if work_shelf is None:
        pmc.mel.addNewShelfTab(shelf_name)
        work_shelf = root.findChild(shelf_name)

    version_object = work_shelf.findChild("__version")
    if version_object is not None:
        old_ver = int(version_object.getLabel())
        if 0 < old_ver < shelf_version:
            return

    for child in work_shelf.children():
        child.delete()

    # Create an invisible version button
    pmc.shelfButton(
        "__version",
        parent=work_shelf,
        noDefaultPopup=True,
        flat=True,
        h=1,
        w=1,
        label=str(shelf_version),
    )

    _add_btns(work_shelf, shelf_config["Shelf"]["buttons"])

    root.setSelectTab(selected_name)


def _get_not_loaded_dialog_command(command: str) -> str:
    """
    Returns a Python script as a string that runs `command()` if it is a valid Maya
    command or shows a dialog informing the user that the plugin is not loaded otherwise.
    """

    return f"""import maya.cmds as cmds
title = "Plugin Not Loaded"
message = "The Deadline Render Submitter Plugin is not loaded.\\nYou must load it from Windows > Settings/Preferences > Plug-in Manager to continue."
try:
    cmds.{command}()
except AttributeError:
    cmds.confirmDialog(title=title, message=message, button="OK", defaultButton="OK")
"""


def _add_btns(tab: "pm_ShelfTabLayout", btn_desc: Dict[str, Any]) -> None:
    """
    Adds a list of buttons to the given tab
    """

    for ctl, btn in btn_desc.items():
        new_btn = pmc.shelfButton(
            ctl,
            parent=tab,
            noDefaultPopup=True,
            flat=True,
            style="iconOnly",
            h=35,
            w=35,
            label=btn["help"],
            ann=btn["help"],
        )

        if "image" in btn:
            new_btn.setImage1(btn["image"])

        if "command" in btn:
            new_btn.setCommand(_get_not_loaded_dialog_command(btn["command"]))
