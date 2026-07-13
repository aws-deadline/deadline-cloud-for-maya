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

The maya / qtpy modules are stubbed by the package ``__init__`` so imports resolve.
"""

from unittest.mock import patch

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


@patch.object(maya_render_submitter, "get_setting", return_value="true")
def test_confirm_callback_none_when_auto_accept_enabled(mock_get_setting):
    """With settings.auto_accept enabled, hooks run without a confirmation prompt."""
    assert maya_render_submitter._pre_gui_hook_confirm_callback(parent=None) is None
    mock_get_setting.assert_called_once_with("settings.auto_accept")


@patch("deadline.client.ui.pre_gui_hooks.qt_hook_confirmation")
@patch.object(maya_render_submitter, "get_setting", return_value="false")
def test_confirm_callback_prompts_when_auto_accept_disabled(mock_get_setting, mock_qt_confirm):
    """With settings.auto_accept disabled, the standard Qt confirmation callback is used."""
    sentinel = object()
    mock_qt_confirm.return_value = sentinel

    result = maya_render_submitter._pre_gui_hook_confirm_callback(parent="mainwin")

    assert result is sentinel
    mock_qt_confirm.assert_called_once_with("mainwin")
