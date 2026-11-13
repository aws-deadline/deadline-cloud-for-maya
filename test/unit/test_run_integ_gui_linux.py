# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Exercise Linux GUI runner isolation and failure propagation without Maya."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

SCRIPT_PATH = Path(__file__).parents[2] / "pipeline" / "run-integ-gui-linux.py"


@pytest.fixture
def runner(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("run_integ_gui_linux", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module.sys, "platform", "linux")
    monkeypatch.setattr(module.shutil, "which", lambda name: f"/usr/bin/{name}")
    (tmp_path / "plugin_env").mkdir()
    (tmp_path / "plugin_env" / "Maya.env").touch()
    maya = tmp_path / "Maya with spaces" / "bin" / "maya"
    maya.parent.mkdir(parents=True)
    maya.touch()
    maya.chmod(0o755)
    monkeypatch.setenv("MAYA_EXECUTABLE", str(maya))
    return module


def test_desktop_environment_drops_stale_bus_addresses(runner):
    env = runner.test_environment(
        {
            "DBUS_SESSION_BUS_ADDRESS": "old-session",
            "AT_SPI_BUS_ADDRESS": "old-accessibility",
            "SESSION_MANAGER": "old-desktop",
            "ADSKFLEX_LICENSE_FILE": "27002@localhost",
            "HOME": "/real/profile",
            "QT_QPA_PLATFORM": "offscreen",
            "NO_AT_BRIDGE": "1",
            "PYTEST_ADDOPTS": "-n auto",
        },
        Path("/usr/autodesk/maya2027/bin/maya"),
    )
    assert "DBUS_SESSION_BUS_ADDRESS" not in env
    assert "AT_SPI_BUS_ADDRESS" not in env
    assert "SESSION_MANAGER" not in env
    assert "PYTEST_ADDOPTS" not in env
    assert env["QT_QPA_PLATFORM"] == "xcb"
    assert env["QT_ACCESSIBILITY"] == env["QT_LINUX_ACCESSIBILITY_ALWAYS_ON"] == "1"
    assert env["NO_AT_BRIDGE"] == "0"
    assert env["ATSPI_DBUS_IMPLEMENTATION"] == "dbus-daemon"
    assert env["LIBGL_ALWAYS_SOFTWARE"] == "1"
    assert env["ADSKFLEX_LICENSE_FILE"] == "27002@localhost"
    assert env["HOME"] == "/real/profile"


def test_runs_pytest_in_isolated_desktop_and_propagates_failure(runner, monkeypatch):
    run = Mock(return_value=Mock(returncode=5))
    monkeypatch.setattr(runner.subprocess, "run", run)

    assert runner.main(["--", "-k", "frame_range", "--basetemp", "/tmp/gui artifacts"]) == 5

    command = run.call_args.args[0]
    assert command[:4] == ["dbus-run-session", "--", "xvfb-run", "--auto-servernum"]
    assert command[5:8] == [sys.executable, "-m", "pytest"]
    assert command[8:12] == ["-o", "addopts=", "-p", "no:cacheprovider"]
    assert command[12:] == [
        "test/integ_gui",
        "-vv",
        "-k",
        "frame_range",
        "--basetemp",
        "/tmp/gui artifacts",
    ]
    assert run.call_args.kwargs["cwd"] == runner.REPO_ROOT
    assert "Maya with spaces" in run.call_args.kwargs["env"]["MAYA_EXECUTABLE"]
    assert run.call_args.kwargs["check"] is False


@pytest.mark.parametrize("failure", ["maya", "submitter", "desktop"])
def test_preflight_failure_never_starts_tests(runner, monkeypatch, failure):
    run = Mock()
    monkeypatch.setattr(runner.subprocess, "run", run)
    if failure == "maya":
        monkeypatch.setenv("MAYA_EXECUTABLE", "/missing/maya")
    elif failure == "submitter":
        (runner.REPO_ROOT / "plugin_env" / "Maya.env").unlink()
    else:
        monkeypatch.setattr(runner.shutil, "which", lambda name: None)

    with pytest.raises(SystemExit) as error:
        runner.main([])
    assert error.value.code == 2
    run.assert_not_called()


def test_requires_explicit_maya_to_prevent_skipped_gui_tests(runner, monkeypatch):
    monkeypatch.delenv("MAYA_EXECUTABLE")
    with pytest.raises(SystemExit) as error:
        runner.main([])
    assert error.value.code == 2
