# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Page object for the Maya submitter dialog, driven through the accessibility tree.

Builds on the shared Deadline submitter controls in deadline-cloud-test-fixtures,
adding the Maya Scene Settings tab (``ui/components/scene_settings_tab.py``).

Selector notes:

* The dialog is a ``Qt.Tool`` window parented to Maya's main window. On Windows a
  Qt dialog can show up as its own accessibility app with the same process ID, so
  the window is looked up across every app owned by Maya's process.
* The frame-range edit has an explicit accessible name, so providers that include
  hidden tab pages or return fields in a different order still target it reliably.
"""

from __future__ import annotations

import sys
import time

import xa11y
from deadline_test_fixtures.xa11y import SharedSubmitterDialog, dismiss_bundle_saved_popup
from deadline_test_fixtures.xa11y.controls import (
    TAB_JOB_SPECIFIC,
    set_checkbox,
    switch_to_tab,
)

from ._launcher import _maya_apps

# The shared dialog's title; Maya passes no submitter info, so there's no version suffix.
DIALOG_TITLE_PREFIXES = ("Submit to AWS Deadline Cloud", "Deadline Cloud Maya Submitter")
WIDGET_TIMEOUT = 60.0
DIALOG_TIMEOUT = 120.0

CHECKBOX_OVERRIDE_FRAME_RANGE = "Override Frame Range"


def _window_selector() -> str:
    return ", ".join(
        f"{role}[name^='{prefix}']"
        for prefix in DIALOG_TITLE_PREFIXES
        for role in ("window", "dialog")
    )


class MayaSubmitterDialog(SharedSubmitterDialog):
    """The submitter dialog of a running GUI Maya."""

    def __init__(self, app: xa11y.App, window: xa11y.Locator, pid: int) -> None:
        super().__init__(window, app_root=app)
        self.app = app
        self.window = window
        self.pid = pid

    @classmethod
    def wait_for(cls, pid: int, timeout: float = DIALOG_TIMEOUT) -> MayaSubmitterDialog:
        selector = _window_selector()
        deadline = time.monotonic() + timeout
        seen: list[tuple[str, int]] = []
        while time.monotonic() < deadline:
            try:
                apps = _maya_apps(pid)
                seen = [(app.name, app.pid) for app in apps]
                for app in apps:
                    window = app.locator(selector)
                    if window.exists():
                        return cls(app, window, app.pid)
            except Exception:  # noqa: BLE001, S110
                # Accessibility providers can be briefly unavailable while Maya
                # creates windows.
                pass
            time.sleep(0.5)
        raise TimeoutError(f"No submitter dialog for PID {pid} within {timeout:.0f}s; apps={seen}")

    def wait_settled(self, timeout: float = WIDGET_TIMEOUT) -> None:
        """Wait until the dialog has loaded the farm's queue environments."""
        loading = self.window.descendant(
            "static_text[name^='Loading Queue Environments'], "
            "static_text[name^='Reloading Queue Environments']"
        )
        loading.wait_hidden(timeout=timeout)
        submit = self.button("Submit")
        submit.wait_visible(timeout=timeout)
        submit.wait_enabled(timeout=timeout)

    def override_frame_range(self, frames: str) -> None:
        switch_to_tab(self.window, TAB_JOB_SPECIFIC)
        set_checkbox(self.window, CHECKBOX_OVERRIDE_FRAME_RANGE, True)
        field = self.window.descendant("text_field[name='Frame Range']")
        field.wait_enabled(timeout=WIDGET_TIMEOUT)
        field.set_value(frames)

    def export_bundle(self) -> None:
        """Save the job bundle locally and dismiss the confirmation."""
        self.save_bundle_locally()
        if sys.platform == "linux":
            # Qt exposes QMessageBox as an AT-SPI alert on Linux. The shared
            # helper currently searches dialog/window/sheet roles only.
            confirmation = self.app.locator("alert[name='Save bundle as']")
            confirmation.descendant("static_text[name^='Bundle saved to:']").wait_visible(
                timeout=WIDGET_TIMEOUT
            )
            confirmation.descendant("button[name='OK']").wait_enabled(
                timeout=WIDGET_TIMEOUT
            ).press()
            confirmation.wait_hidden(timeout=WIDGET_TIMEOUT)
        elif not dismiss_bundle_saved_popup(self.pid, timeout=WIDGET_TIMEOUT):
            raise AssertionError("The 'Bundle saved to' confirmation never appeared")

    def submit(self) -> None:
        submit = self.button("Submit")
        submit.wait_enabled(timeout=WIDGET_TIMEOUT)
        submit.press()
