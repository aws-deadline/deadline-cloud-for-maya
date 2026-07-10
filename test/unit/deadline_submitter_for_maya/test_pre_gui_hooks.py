# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for the Maya submitter's pre-GUI hook integration.

``show_maya_render_submitter`` calls deadline-cloud's ``run_pre_gui_hooks`` (env-only, since
Maya has no on-disk bundle) and then maps the merged output with deadline-cloud's generic
``apply_pre_gui_output``. The full submitter needs a running Maya, so it is exercised in the
integration suite; here we verify the DCC-owned contract headless: that ``apply_pre_gui_output``
routes hook output correctly against Maya's own ``RenderSubmitterUISettings`` — which has no
``.parameters`` list, so every hook parameter must land in the shared parameter values. This
guards against a regression where ``RenderSubmitterUISettings`` gains a ``parameters`` attribute
that would silently misroute hook parameters.

``apply_pre_gui_output`` ships in deadline-cloud 0.60.1+; the module is skipped on older releases
so this file collects cleanly regardless of the installed deadline-cloud version. The maya /
qtpy modules are stubbed by the package ``__init__`` so imports resolve.
"""

import pytest

# apply_pre_gui_output ships in deadline-cloud 0.60.1+; skip cleanly on older releases.
pre_gui_hooks = pytest.importorskip("deadline.client.ui.pre_gui_hooks")
apply_pre_gui_output = pre_gui_hooks.apply_pre_gui_output

from deadline.maya_submitter.data_classes import (  # noqa: E402  (after importorskip)
    RenderSubmitterUISettings,
)


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
