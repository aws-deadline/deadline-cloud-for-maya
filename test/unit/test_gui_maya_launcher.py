# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Verify diagnostics for failures before GUI Maya's startup command runs."""

from unittest.mock import Mock

import pytest

from test.integ_gui import _launcher as launcher


def test_early_startup_failure_reports_process_stderr(monkeypatch, tmp_path):
    process = Mock(returncode=7)
    process.poll.return_value = 7

    def start(*args, **kwargs):
        assert kwargs["stderr"] == launcher.subprocess.STDOUT
        assert kwargs["start_new_session"] is True
        kwargs["stdout"].write(b"Could not load the Qt platform plugin xcb\n")
        kwargs["stdout"].flush()
        return process

    monkeypatch.setattr(launcher.sys, "platform", "linux")
    monkeypatch.setattr(launcher.subprocess, "Popen", start)
    capture = Mock()
    monkeypatch.setattr(launcher, "screenshot", capture)
    env = {launcher.ENV_STATUS_FILE: str(tmp_path / "opener_status.txt")}

    with pytest.raises(RuntimeError, match="Could not load the Qt platform plugin xcb"):
        launcher.launch_maya_with_submitter(tmp_path / "maya", env, tmp_path)

    capture.assert_called_once_with(tmp_path / "startup_failure.png")
    assert (tmp_path / "maya_process.log").read_text().endswith("plugin xcb\n")


def test_log_tail_includes_both_maya_and_process_output(tmp_path):
    (tmp_path / "maya.log").write_text("Maya startup\n")
    (tmp_path / "maya_process.log").write_text("X11 connection error\n")
    session = launcher.MayaSession(process=Mock(), work_dir=tmp_path, opener_status="")

    diagnostic = session.tail_log()

    assert "Maya startup" in diagnostic
    assert "X11 connection error" in diagnostic
