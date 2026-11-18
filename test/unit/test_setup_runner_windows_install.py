# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Unit tests for how pipeline/setup-runner.py waits for Maya's Windows installer."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Callable, Optional

import pytest

SCRIPT_PATH = Path(__file__).parents[2] / "pipeline" / "setup-runner.py"


@pytest.fixture(scope="module")
def setup_runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("setup_runner", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakeSetup:
    """Setup.exe, exiting with 0 once the clock reaches exit_at (never if None)."""

    def __init__(self, clock: FakeClock, exit_at: Optional[float]) -> None:
        self.clock = clock
        self.exit_at = exit_at

    def poll(self) -> Optional[int]:
        if self.exit_at is not None and self.clock.now >= self.exit_at:
            return 0
        return None


def _proc(name: str, path: str) -> dict:
    return {"Name": name, "ProcessId": 1, "ParentProcessId": 0, "ExecutablePath": path}


def _wait(
    setup_runner: ModuleType,
    tmp_path: Path,
    clock: FakeClock,
    setup: FakeSetup,
    *,
    msi_busy: Callable[[float], bool] = lambda now: False,
    processes: Optional[Callable[[float, Path], Optional[list]]] = None,
) -> bool:
    setup_dir = tmp_path / "maya_setup"
    setup_dir.mkdir(exist_ok=True)
    return setup_runner._wait_for_maya_setup(
        setup,
        setup_dir,
        tmp_path / "mayapy.exe",
        list_processes=lambda: processes(clock.now, setup_dir) if processes else [],
        msi_busy=lambda: msi_busy(clock.now),
        clock=clock,
        sleep=clock.sleep,
    )


def _finished_at(setup_runner: ModuleType, clock: FakeClock, expected_start: float) -> None:
    """The wait returned once the install had looked finished for MAYA_SETUP_CONFIRM."""
    confirmed = expected_start + setup_runner.MAYA_SETUP_CONFIRM
    assert confirmed <= clock.now < confirmed + setup_runner.MAYA_SETUP_POLL


def test_done_when_setup_exits_and_msi_is_idle(setup_runner, tmp_path):
    clock = FakeClock()

    # A long-lived Autodesk app outside the package is what hung Start-Process -Wait.
    def processes(now, setup_dir):
        return [_proc("AdskAccessUIHost.exe", r"C:\Program Files\Autodesk\Access\UI.exe")]

    setup = FakeSetup(clock, exit_at=600)
    assert _wait(
        setup_runner, tmp_path, clock, setup, msi_busy=lambda now: now < 550, processes=processes
    )
    _finished_at(setup_runner, clock, 600)


def test_waits_for_msi_after_setup_exits(setup_runner, tmp_path):
    clock = FakeClock()

    assert _wait(
        setup_runner, tmp_path, clock, FakeSetup(clock, exit_at=60), msi_busy=lambda now: now < 900
    )
    _finished_at(setup_runner, clock, 900)


def test_a_brief_gap_between_packages_is_not_the_end(setup_runner, tmp_path):
    clock = FakeClock()

    # Windows Installer is idle for 10s between two packages, then busy until 900s.
    def msi_busy(now):
        return not (300 <= now < 310) and now < 900

    assert _wait(setup_runner, tmp_path, clock, FakeSetup(clock, exit_at=60), msi_busy=msi_busy)
    _finished_at(setup_runner, clock, 900)


def test_waits_for_processes_left_running_from_the_package(setup_runner, tmp_path):
    clock = FakeClock()

    def processes(now, setup_dir):
        if now < 1200:
            return [_proc("Installer.exe", str(setup_dir / "extracted" / "Installer.exe"))]
        return []

    assert _wait(setup_runner, tmp_path, clock, FakeSetup(clock, exit_at=60), processes=processes)
    _finished_at(setup_runner, clock, 1200)


def test_a_failed_process_listing_is_not_an_empty_one(setup_runner, tmp_path):
    clock = FakeClock()

    def processes(now, setup_dir):
        return None if now < 1200 else []

    assert _wait(setup_runner, tmp_path, clock, FakeSetup(clock, exit_at=60), processes=processes)
    _finished_at(setup_runner, clock, 1200)


def test_times_out_while_setup_is_still_running(setup_runner, tmp_path):
    # Installed and idle is not enough while Setup.exe is still running.
    clock = FakeClock()
    (tmp_path / "mayapy.exe").touch()

    assert not _wait(setup_runner, tmp_path, clock, FakeSetup(clock, exit_at=None))
    assert clock.now >= setup_runner.MAYA_SETUP_TIMEOUT


def test_diagnostics_survive_unreadable_logs(setup_runner, tmp_path, monkeypatch, capsys):
    # The installer may still hold or remove its logs; diagnostics must still get to ODIS's.
    local_appdata = tmp_path / "LocalAppData"
    odis = local_appdata / "Autodesk" / "ODIS"
    odis.mkdir(parents=True)
    (odis / "Summary.log").write_text("Installation is cancelled\n")
    (odis / "Install.log").write_text(
        "[InstallManager ERROR] Disk space parameters: {}\nunrelated\n"
    )
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))
    monkeypatch.setenv("TEMP", str(tmp_path / "Temp"))
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path / "ProgramData"))
    monkeypatch.setenv("MAYA_SETUP_DIAGNOSTICS_DIR", str(tmp_path / "diagnostics"))
    monkeypatch.setattr(setup_runner, "_windows_processes", lambda: None)

    def locked(*args, **kwargs):
        raise PermissionError("in use by another process")

    monkeypatch.setattr(setup_runner.shutil, "copy2", locked)
    monkeypatch.setattr(setup_runner, "run", lambda *args, **kwargs: None)

    setup_runner._dump_maya_setup_diagnostics(since=0)

    out = capsys.readouterr().out
    assert "could not copy it: in use by another process" in out
    assert "Installation is cancelled" in out
    assert "Disk space parameters" in out
    assert "unrelated" not in out
