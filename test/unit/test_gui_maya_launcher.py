# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Verify diagnostics for failures before GUI Maya's startup command runs."""

import ast
import json
from types import SimpleNamespace
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


@pytest.mark.parametrize("platform", ["linux", "win32"])
def test_accessibility_matches_linux_launcher_children(monkeypatch, platform):
    parent, child, unrelated, exited = [Mock(pid=pid) for pid in (100, 101, 200, 300)]
    xa11y = SimpleNamespace(App=SimpleNamespace(list=lambda: [parent, child, unrelated, exited]))
    monkeypatch.setitem(launcher.sys.modules, "xa11y", xa11y)
    monkeypatch.setattr(launcher.sys, "platform", platform)

    def process_group(pid):
        if pid == 300:
            raise ProcessLookupError
        return 100 if pid == 101 else 200

    monkeypatch.setattr(launcher.os, "getpgid", process_group, raising=False)
    assert launcher._maya_apps(100) == ([parent, child] if platform == "linux" else [parent])


def test_linux_startup_command_survives_vendor_shell_quoting(monkeypatch, tmp_path):
    opener = tmp_path / "Maya user's tests" / "_opener.py"
    monkeypatch.setattr(launcher, "OPENER", opener)
    monkeypatch.setattr(launcher.sys, "platform", "linux")
    process = Mock(returncode=7)
    process.poll.return_value = 7
    start = Mock(return_value=process)
    monkeypatch.setattr(launcher.subprocess, "Popen", start)
    monkeypatch.setattr(launcher, "screenshot", Mock())
    env = {launcher.ENV_STATUS_FILE: str(tmp_path / "opener_status.txt")}

    with pytest.raises(RuntimeError, match="Maya exited early"):
        launcher.launch_maya_with_submitter(tmp_path / "maya", env, tmp_path)

    command = start.call_args.args[0][-1]
    # The vendor wraps this whole command in single quotes, then evaluates it.
    assert "'" not in command
    python_code = json.loads(command.removeprefix("python(").removesuffix(")"))
    tree = ast.parse(python_code)
    strings = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant)]
    assert strings.count(opener.as_posix()) == 2
    assert "exec" in strings
