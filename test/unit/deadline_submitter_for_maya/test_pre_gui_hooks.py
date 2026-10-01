# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for the Maya submitter's pre-GUI hook integration.

``show_maya_render_submitter`` calls deadline-cloud's ``run_pre_gui_hooks`` (env-only, since
Maya has no on-disk bundle) and then maps the merged output with deadline-cloud's generic
``apply_pre_gui_output``. The full submitter needs a running Maya, so it is exercised in the
integration suite; here we verify the DCC-owned pieces headless:

* ``apply_pre_gui_output`` routes hook output correctly against Maya's own
  ``RenderSubmitterUISettings`` — which has no ``.parameters`` list, so every hook parameter must
  land in the shared parameter values. This guards against a regression where
  ``RenderSubmitterUISettings`` gains a ``parameters`` attribute that would misroute hook params.
* ``_pre_gui_hook_confirm_callback`` honours the ``settings.auto_accept`` setting.
* Declining the hook confirmation (``DeadlineOperationCanceled``) aborts the open silently
  rather than surfacing a spurious error dialog.

The maya / qtpy modules are stubbed by the package ``__init__`` so imports resolve.
"""

import sys
from typing import Optional
from unittest.mock import MagicMock, patch

from deadline.client.exceptions import DeadlineOperationCanceled
from deadline.client.ui.pre_gui_hooks import apply_pre_gui_output
from deadline.maya_submitter.data_classes import RenderSubmitterUISettings
from deadline.maya_submitter import maya_render_submitter


def _settings() -> RenderSubmitterUISettings:
    s = RenderSubmitterUISettings()
    s.name = "Original"
    s.description = ""
    return s


def test_name_and_description_applied_to_settings():
    """A hook's name/description overwrite the settings fields (Maya has no .parameters list,
    so these land directly on the dataclass)."""
    settings = _settings()
    shared = {"RezPackages": "mayaIO-2024 deadline_cloud_for_maya"}

    apply_pre_gui_output({"name": "PREGUI RAN", "description": "from pipeline"}, settings, shared)

    assert settings.name == "PREGUI RAN"
    assert settings.description == "from pipeline"


def test_hook_parameters_routed_to_shared_values():
    """RenderSubmitterUISettings has no .parameters list, so every hook parameter (queue params,
    deadline: properties) is routed into the shared values the dialog is seeded with, overriding
    the Maya-computed defaults on key collision."""
    settings = _settings()
    shared = {"RezPackages": "mayaIO-2024 deadline_cloud_for_maya", "CondaPackages": "maya=2024.*"}

    apply_pre_gui_output(
        {
            "parameters": {
                "deadline:priority": 88,
                "RezPackages": "mayaIO-2024 custom_pkg",  # overrides the default
            }
        },
        settings,
        shared,
    )

    assert shared["deadline:priority"] == 88
    assert shared["RezPackages"] == "mayaIO-2024 custom_pkg"
    assert shared["CondaPackages"] == "maya=2024.*"  # untouched keys preserved


def test_empty_output_is_a_noop():
    """No pre-GUI hook output leaves the settings and shared values unchanged."""
    settings = _settings()
    shared = {"RezPackages": "pkg"}

    apply_pre_gui_output({}, settings, shared)

    assert settings.name == "Original"
    assert settings.description == ""
    assert shared == {"RezPackages": "pkg"}


def test_partial_output_only_touches_present_keys():
    """Only the keys present in the output are applied; others keep their prior values."""
    settings = _settings()
    settings.description = "keep me"
    shared: dict = {}

    apply_pre_gui_output({"name": "NewName"}, settings, shared)

    assert settings.name == "NewName"
    assert settings.description == "keep me"  # not overwritten
    assert shared == {}  # no parameters in output


def test_falsy_output_is_a_noop():
    """The submitter passes ``pre_gui_output or {}`` into apply_pre_gui_output, so the values
    run_pre_gui_hooks can actually produce for the no-hooks path — ``{}`` today, or ``None`` if
    the contract ever changed — must both be safe no-ops that leave settings/shared untouched."""
    falsy_values: list[Optional[dict]] = [{}, None]
    for falsy in falsy_values:
        settings = _settings()
        shared = {"RezPackages": "mayaIO-2024 deadline_cloud_for_maya"}

        # Mirror the submitter call site: `pre_gui_output or {}`.
        apply_pre_gui_output(falsy or {}, settings, shared)

        assert settings.name == "Original"
        assert settings.description == ""
        assert shared == {"RezPackages": "mayaIO-2024 deadline_cloud_for_maya"}


@patch.object(maya_render_submitter, "get_setting", return_value="true")
def test_confirm_callback_none_when_auto_accept_enabled(mock_get_setting):
    """With settings.auto_accept enabled, hooks run without a confirmation prompt."""
    assert maya_render_submitter._pre_gui_hook_confirm_callback(parent=None) is None
    mock_get_setting.assert_called_once_with("settings.auto_accept")


# Patch ``QMessageBox`` on the exact object the import reads. ``qt_hook_confirmation`` does
# ``from qtpy.QtWidgets import QMessageBox``, which resolves through ``sys.modules["qtpy.QtWidgets"]``
# — the standalone mock the package ``__init__`` installs there. A string ``patch("qtpy.QtWidgets.
# QMessageBox")`` instead resolves the dotted path through the *parent* ``qtpy`` mock's auto-created
# ``QtWidgets`` child, which is a different object on Python 3.9/3.10, so the patch never reaches the
# QMessageBox the code sees and ``question`` is never called.
@patch.object(sys.modules["qtpy.QtWidgets"], "QMessageBox")
@patch.object(maya_render_submitter, "get_setting", return_value="false")
def test_confirmation_dialog_fires_when_auto_accept_disabled(mock_get_setting, mock_msgbox):
    """With settings.auto_accept disabled, invoking the returned callback actually shows the
    confirmation dialog (QMessageBox.question), parented to the passed-in window.

    This exercises the real ``qt_hook_confirmation`` callback rather than mocking it out, so it
    verifies the prompt fires — not merely that a non-None callback was selected. ``run_pre_gui_hooks``
    invokes ``confirm_callback(sources)`` with the hook sources; an empty list is enough to reach
    the dialog. The user's answer is mapped from the QMessageBox reply.
    """
    mock_msgbox.question.return_value = mock_msgbox.Yes

    callback = maya_render_submitter._pre_gui_hook_confirm_callback(parent="mainwin")
    assert callback is not None

    result = callback([])  # no hook sources needed to reach the dialog

    assert mock_msgbox.question.call_count == 1
    # The dialog is parented to the window passed into the submitter.
    assert mock_msgbox.question.call_args[0][0] == "mainwin"
    # "Yes" reply → proceed.
    assert result is True


# ``run_pre_gui_hooks`` is imported lazily from ``deadline.client.ui.pre_gui_hooks`` inside
# ``show_maya_render_submitter``, so it must be patched on that source module (not on
# ``maya_render_submitter``). The Maya-heavy setup that runs before the hook call is mocked out so
# the test can reach the hook call headlessly; ``time`` is mocked so the progress-dialog sleeps are
# instant.
@patch("deadline.maya_submitter.maya_render_submitter.time")
@patch("deadline.client.ui.pre_gui_hooks.run_pre_gui_hooks")
@patch.object(maya_render_submitter, "SubmitJobToDeadlineDialog")
@patch.object(maya_render_submitter, "_pre_gui_hook_confirm_callback", return_value=None)
@patch.object(maya_render_submitter, "get_deadline_cloud_library_telemetry_client")
@patch.object(maya_render_submitter, "AssetIntrospector")
@patch.object(maya_render_submitter, "_populate_selectable_cameras")
@patch.object(maya_render_submitter, "_get_render_layer_data", return_value=[])
@patch.object(maya_render_submitter, "_set_render_setting")
def test_declining_hook_confirmation_aborts_without_error(
    mock_set_render_setting,
    mock_get_render_layer_data,
    mock_populate_cameras,
    mock_introspector,
    mock_telemetry,
    mock_confirm_cb,
    mock_dialog,
    mock_run_hooks,
    mock_time,
):
    """Declining the hook prompt (DeadlineOperationCanceled) returns None and never builds the
    dialog, so the outer gui_error_handler cannot surface a spurious error dialog."""
    mock_set_render_setting.return_value = _settings()
    mock_introspector.return_value.parse_scene_assets.return_value = []
    # The user clicks "No" on the confirmation prompt.
    mock_run_hooks.side_effect = DeadlineOperationCanceled("user declined")

    result = maya_render_submitter.show_maya_render_submitter(parent=MagicMock())

    assert result is None
    mock_run_hooks.assert_called_once()
    mock_dialog.assert_not_called()  # dialog must not be built on cancellation
