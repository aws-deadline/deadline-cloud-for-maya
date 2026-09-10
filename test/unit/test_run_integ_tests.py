# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Unit tests for the orphan sweep in pipeline/run-integ-tests.py.

Deliberately narrow. The fake psutil below returns what we assume psutil
returns, so these tests check our logic but never that assumption. They cover
only the two judgement calls a future change could silently reverse:

1. A cleanup failure must never fail the build.
2. The marker set must not match processes that merely mention Maya.

Whether killing a process frees its license is license-server behaviour, visible
only in a real integ run.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

RUNNER_PATH = Path(__file__).parents[2] / "pipeline" / "run-integ-tests.py"

MAYAPY = "/opt/Autodesk/mayaio/2026/usr/autodesk/mayaIO2026/bin/mayapy.bin"


@pytest.fixture(scope="module")
def runner():
    """Load the runner by path; its filename has hyphens so it cannot be imported."""
    spec = importlib.util.spec_from_file_location("run_integ_tests", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeProcess:
    def __init__(self, pid: int, cmdline: list[str] | None):
        self.pid = pid
        self.info = {"pid": pid, "cmdline": cmdline}


class FakePsutil:
    """Minimal stand-in for the psutil surface the matcher uses."""

    class NoSuchProcess(Exception):
        pass

    class AccessDenied(Exception):
        pass

    def __init__(self, processes: list[FakeProcess]):
        self._processes = processes

    def process_iter(self, attrs=None):
        return iter(self._processes)


def test_matches_command_lines_observed_on_a_real_host(runner):
    """Both orphan shapes seen in CI, plus a wrapper shell around the interpreter.

    The wrapper matching is deliberate: on Linux mayapy is a shell script, and
    killing it alongside the interpreter is intended. Switching to process-name
    matching would change this, which should be a conscious decision.
    """
    procs = [
        FakeProcess(101, [MAYAPY, "-m", "openjd", "run", "/tmp/codebuild-abc/template.yaml"]),
        FakeProcess(102, [MAYAPY, "/tmp/codebuild-abc/src/.../MayaClient/maya_client.py"]),
        FakeProcess(103, ["/bin/sh", "-c", "mayapy -m pytest test/integ"]),
    ]
    orphans, unreadable = runner.find_orphaned_maya_processes(FakePsutil(procs), set())

    assert [p.pid for p, _ in orphans] == [101, 102, 103]
    assert unreadable == []


def test_does_not_match_processes_that_merely_mention_maya(runner):
    """Guardrail against broadening the markers.

    Every string here appears near this code in practice: the installer handles
    Maya archives, and the suite's own job parameters contain "RenderLayer"
    (`rs_<RenderLayer>_<Camera>`). Adding a loose marker such as "Render" would
    turn these into kill targets.
    """
    procs = [
        FakeProcess(201, ["/bin/tar", "-xzf", "/tmp/Autodesk_MayaIO_2026_Linux_64bit.run"]),
        FakeProcess(202, ["/usr/bin/tail", "-f", "/tmp/RenderLayer.log"]),
        FakeProcess(203, ["/opt/python/bin/python", "./pipeline/setup-runner.py", "--renderers"]),
        FakeProcess(204, ["/usr/libexec/Xorg", ":99"]),
    ]
    orphans, unreadable = runner.find_orphaned_maya_processes(FakePsutil(procs), set())

    assert orphans == []
    assert unreadable == []


def test_unreadable_command_line_is_reported_not_dropped(runner):
    """psutil reports None when a cmdline cannot be read, e.g. another user's process.

    Such a process could be the orphan we are looking for, so it must be
    surfaced rather than silently skipped.
    """
    procs = [FakeProcess(301, None), FakeProcess(302, [MAYAPY, "maya_client.py"])]
    orphans, unreadable = runner.find_orphaned_maya_processes(FakePsutil(procs), set())

    assert [p.pid for p, _ in orphans] == [302]
    assert unreadable == [301]


def test_cleanup_failure_never_fails_the_build(runner, monkeypatch, capsys):
    """The sweep is best-effort; its failure must not propagate to either call site."""

    def explode(phase):
        raise RuntimeError("psutil exploded")

    monkeypatch.setattr(runner, "release_orphaned_maya_licenses", explode)
    runner._cleanup("pre-test")

    assert "pre-test: cleanup failed: psutil exploded" in capsys.readouterr().out
