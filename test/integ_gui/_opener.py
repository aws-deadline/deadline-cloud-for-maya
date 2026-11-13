# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Runs inside GUI Maya: open the test scene and the Deadline Cloud submitter.

The launcher starts Maya with ``-command`` executing this file. Once Maya's UI is
idle, it loads the submitter plug-in, opens the scene named by
MAYA_SUBMITTER_UI_SCENE_FILE, and runs the ``DeadlineCloudSubmitter`` command,
which is what the shelf button runs. The result goes to the status file named by
MAYA_SUBMITTER_UI_STATUS_FILE, the only channel back to the test process.

Plain Python with no imports from the test suite: this runs in Maya's interpreter.
"""

import os
import traceback

_STATUS_FILE = os.environ.get("MAYA_SUBMITTER_UI_STATUS_FILE", "")
_SCENE_FILE = os.environ.get("MAYA_SUBMITTER_UI_SCENE_FILE", "")

# The mock service listens on loopback, so botocore must not add the
# "management." host prefix. Older botocore ignores this setting.
_MIN_BOTOCORE = (1, 37, 5)


def _write_status(text):
    # The launcher reads the file as soon as it exists, so it must appear complete.
    if _STATUS_FILE:
        partial = _STATUS_FILE + ".partial"
        with open(partial, "w", encoding="utf8") as status:
            status.write(text)
        os.replace(partial, _STATUS_FILE)


def _open_scene(scene_file):
    """Open the scene with its directory as the project, like the bundle-output tests."""
    import maya.cmds as cmds

    scene_dir = os.path.dirname(scene_file)
    if os.path.exists(os.path.join(scene_dir, "workspace.mel")):
        cmds.workspace(scene_dir, openWorkspace=True)
    else:
        cmds.workspace(scene_dir, newWorkspace=True)
    cmds.workspace(directory=scene_dir)
    # The expected bundles were generated with this machine-level option on.
    cmds.optionVar(intValue=("renderSetup_includeAllLights", 1))
    cmds.file(scene_file, open=True, force=True)
    # Submitting a modified scene prompts to save it first. Start unmodified so
    # Submit goes straight through; that prompt deserves its own test.
    cmds.file(modified=False)


def _open_submitter():
    try:
        import botocore
        import maya.cmds as cmds

        botocore_version = tuple(int(part) for part in botocore.__version__.split(".")[:3])
        if botocore_version < _MIN_BOTOCORE:
            raise RuntimeError(
                f"botocore {botocore.__version__} ignores AWS_DISABLE_HOST_PREFIX_INJECTION; "
                f"need {'.'.join(map(str, _MIN_BOTOCORE))} or newer"
            )

        cmds.loadPlugin("DeadlineCloudForMaya", quiet=True)
        _open_scene(_SCENE_FILE)

        # The update-available dialog would block the submitter. Private API: if it
        # is renamed this raises, which the status file reports.
        from deadline.maya_submitter import update_utils

        update_utils._session_state.update_dismissed = True

        cmds.DeadlineCloudSubmitter()

        from deadline.maya_submitter.mel_commands import DeadlineCloudSubmitterCmd

        if DeadlineCloudSubmitterCmd.dialog is None:
            _write_status("ERROR\nDeadlineCloudSubmitter did not open a dialog\n")
            return
        _write_status(
            "OK\n"
            f"maya_version={cmds.about(version=True)}\n"
            f"botocore_version={botocore.__version__}\n"
        )
    except Exception:
        _write_status("ERROR\n" + traceback.format_exc())


try:
    import maya.utils

    if _STATUS_FILE and _SCENE_FILE:
        maya.utils.executeDeferred(_open_submitter)
except Exception:
    _write_status("ERROR (opener top level)\n" + traceback.format_exc())
