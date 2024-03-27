# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Creates or updates the AWS Deadline shelf.
"""
import os
from contextlib import contextmanager

import maya.mel  # pylint: disable=import-errorz
import maya.cmds  # pylint: disable=import-errorz

_BUTTON_COMMAND = """import maya.cmds
try:
    maya.cmds.{command}()
except AttributeError:
    maya.cmds.confirmDialog(title="Deadline Cloud Submitter Plugin Not Loaded",
                            message="The Deadline Cloud Submitter Plugin is not loaded.\\n"
                               + "You must enable it from Windows > Settings/Preferences "
                               + "> Plug-in Manager to continue.",
                            button="OK",
                            defaultButton="OK")
"""


def _add_or_update_shelf_button(full_shelf_name: str, button_name: str, label: str, **kwargs):
    # Find the existing buttons with the button label
    existing_buttons = maya.cmds.shelfLayout(full_shelf_name, query=True, childArray=True)
    if existing_buttons:
        existing_buttons = [
            button
            for button in existing_buttons
            if maya.cmds.shelfButton(f"{full_shelf_name}|{button}", query=True, label=True) == label
        ]

    if existing_buttons:
        # If there were any existing buttons, update them
        for button in existing_buttons:
            maya.cmds.shelfButton(button, parent=full_shelf_name, edit=True, label=label, **kwargs)
    else:
        # If there were no buttons, create one
        maya.cmds.shelfButton(button_name, parent=full_shelf_name, label=label, **kwargs)


@contextmanager
def _saved_shelf_selection():
    """
    Preserves the current Maya shelf selection and returns the name of the top shelf level.
    """
    # Save the currently selected shelf tab
    g_shelf_top_level = maya.mel.eval("$_=$gShelfTopLevel")
    saved_shelf_select_tab = maya.cmds.shelfTabLayout(g_shelf_top_level, query=True, selectTab=True)
    try:
        yield g_shelf_top_level
    finally:
        # Restore the selected shelf tab
        maya.cmds.shelfTabLayout(g_shelf_top_level, edit=True, selectTab=saved_shelf_select_tab)


def build_shelf() -> None:
    """
    Builds the Deadline Maya Shelf.
    """
    shelf_name = "AWSDeadline"

    with _saved_shelf_selection() as g_shelf_top_level:
        # Create the Deadline shelf tab if it doesn't exist
        if not maya.cmds.shelfLayout(shelf_name, parent=g_shelf_top_level, exists=True):
            maya.cmds.shelfLayout(shelf_name, parent=g_shelf_top_level)

        full_shelf_name = f"{g_shelf_top_level}|{shelf_name}"

        deadline_cloud_submitter_name = "DeadlineCloudSubmitter"
        _add_or_update_shelf_button(
            full_shelf_name=full_shelf_name,
            button_name=deadline_cloud_submitter_name,
            noDefaultPopup=True,
            flat=True,
            style="iconOnly",
            h=35,
            w=35,
            label="Submit a render to Deadline Cloud",
            ann="Submit a render to Deadline Cloud",
            command=_BUTTON_COMMAND.format(command=deadline_cloud_submitter_name),
            image1="deadline_render_submitter.svg",
        )
        job_bundle_tests_name = "DeadlineCloudJobBundleOutputTests"
        if os.environ.get("DEADLINE_ENABLE_DEVELOPER_OPTIONS", "").upper() == "TRUE":
            _add_or_update_shelf_button(
                full_shelf_name=full_shelf_name,
                button_name=job_bundle_tests_name,
                noDefaultPopup=True,
                flat=True,
                style="iconOnly",
                h=35,
                w=35,
                label="Run Maya Submitter Job Bundle Output Tests...",
                ann="Run Maya Submitter Job Bundle Output Tests...",
                command=_BUTTON_COMMAND.format(command=job_bundle_tests_name),
                image1="deadline_cloud_job_bundle_tests.svg",
            )
        else:
            # Delete the developer option button if it exists
            if maya.cmds.shelfButton(job_bundle_tests_name, parent=full_shelf_name, exists=True):
                maya.cmds.deleteUI(f"{full_shelf_name}|{job_bundle_tests_name}", control=True)
