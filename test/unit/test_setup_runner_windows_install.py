# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Unit tests for how pipeline/setup-runner.py waits for Maya's Windows installer."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Optional

import pytest

SCRIPT_PATH = Path(__file__).parents[2] / "pipeline" / "setup-runner.py"


@pytest.fixture(scope="module")
def setup_runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("setup_runner", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeSetup:
    """Setup.exe, exiting with 0 once the clock reaches exit_at (never if None)."""

    def __init__(self, clock: "FakeClock", exit_at: Optional[float]) -> None:
        self.clock = clock
        self.exit_at = exit_at

    def poll(self) -> Optional[int]:
        if self.exit_at is not None and self.clock.now >= self.exit_at:
            return 0
        return None


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def _proc(name: str, path: str) -> dict:
    return {"Name": name, "ProcessId": 1, "ParentProcessId": 0, "ExecutablePath": path}


def _wait(setup_runner, tmp_path, clock, setup, *, msi_busy_until=0.0, processes=None):
    setup_dir = tmp_path / "maya_setup"
    setup_dir.mkdir(exist_ok=True)
    return setup_runner._wait_for_maya_setup(
        setup,
        setup_dir,
        tmp_path / "mayapy.exe",
        list_processes=lambda: processes(clock.now, setup_dir) if processes else [],
        msi_busy=lambda: clock.now < msi_busy_until,
        clock=clock,
        sleep=clock.sleep,
    )


def test_done_when_setup_exits_and_msi_is_idle(setup_runner, tmp_path):
    clock = FakeClock()
    (tmp_path / "mayapy.exe").touch()

    # A long-lived Autodesk app outside the package is what hung Start-Process -Wait.
    def processes(now, setup_dir):
        return [_proc("AdskAccessUIHost.exe", r"C:\Program Files\Autodesk\Access\UI.exe")]

    done = _wait(
        setup_runner,
        tmp_path,
        clock,
        FakeSetup(clock, exit_at=600),
        msi_busy_until=550,
        processes=processes,
    )

    assert done
    assert 600 <= clock.now < 600 + setup_runner.MAYA_SETUP_POLL


def test_waits_for_msi_after_setup_exits(setup_runner, tmp_path):
    clock = FakeClock()
    (tmp_path / "mayapy.exe").touch()

    done = _wait(setup_runner, tmp_path, clock, FakeSetup(clock, exit_at=60), msi_busy_until=900)

    assert done
    assert clock.now >= 900


def test_waits_for_processes_left_running_from_the_package(setup_runner, tmp_path):
    clock = FakeClock()
    (tmp_path / "mayapy.exe").touch()

    def processes(now, setup_dir):
        if now < 1200:
            return [_proc("Installer.exe", str(setup_dir / "extracted" / "Installer.exe"))]
        return []

    done = _wait(setup_runner, tmp_path, clock, FakeSetup(clock, exit_at=60), processes=processes)

    assert done
    # Settles 5 minutes after Windows Installer went idle, before the package process exits.
    assert clock.now == pytest.approx(
        setup_runner.MAYA_SETUP_SETTLE, abs=setup_runner.MAYA_SETUP_POLL
    )


def test_continues_once_installed_and_msi_settles_while_setup_lingers(setup_runner, tmp_path):
    clock = FakeClock()
    (tmp_path / "mayapy.exe").touch()

    done = _wait(setup_runner, tmp_path, clock, FakeSetup(clock, exit_at=None), msi_busy_until=900)

    assert done
    assert clock.now == pytest.approx(
        900 + setup_runner.MAYA_SETUP_SETTLE, abs=setup_runner.MAYA_SETUP_POLL
    )


def test_does_not_settle_before_mayapy_is_installed(setup_runner, tmp_path):
    clock = FakeClock()

    done = _wait(setup_runner, tmp_path, clock, FakeSetup(clock, exit_at=None))

    assert not done
    assert clock.now >= setup_runner.MAYA_SETUP_TIMEOUT
