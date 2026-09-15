# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Run integration tests with correct environment for each platform.

Sweeps orphaned Maya processes, then sets Maya's bin on PATH and renderer
environment variables so the adaptor's subprocess can find mayapy and renderer
plugins.
"""

import os
import platform
import subprocess
import sys
from types import ModuleType
from typing import Any

# Matched as substrings of the command line. Deliberately not a bare "maya",
# which would match any process merely naming a Maya file.
_MAYA_PROCESS_MARKERS = ("mayapy", "maya.bin", "maya.exe")


def _log(message: str) -> None:
    """Log a cleanup message."""
    # flush=True keeps ordering against the pytest subprocess, which writes to
    # the same descriptor; unflushed output appears after all test output.
    print(f"[license-cleanup] {message}", flush=True)


def find_orphaned_maya_processes(
    psutil: ModuleType, protected_pids: set[int]
) -> list[tuple[Any, str]]:
    """Return [(process, cmdline)] for Maya processes not in protected_pids.

    A process whose command line cannot be read is skipped. psutil reports None
    for a zombie or for a process this build cannot open, and in neither case can
    we confirm it is Maya; killing an unidentified process is worse than leaving
    it.

    psutil is passed in because the caller imports it lazily to keep the sweep
    best effort; that also lets matching be tested without killing processes.
    """
    orphans = []
    for proc in psutil.process_iter(["pid", "cmdline"]):
        if proc.pid in protected_pids:
            continue
        cmdline = " ".join(proc.info.get("cmdline") or [])
        if any(marker in cmdline for marker in _MAYA_PROCESS_MARKERS):
            orphans.append((proc, cmdline))
    return orphans


def release_orphaned_maya_licenses(phase: str) -> None:
    """Terminate leftover Maya processes, releasing their Autodesk licenses.

    CodeBuild reserved-capacity hosts are reused between builds. Every orphan
    observed so far was an adaptor subprocess that outlived a cancelled or
    timed-out run; it holds its checkout open indefinitely, and once enough
    accumulate later checkouts are refused. Maya reports that refusal as a
    misleading MAYA_APP_DIR disk-space error.

    Runs pre-test and post-test. Post-test covers normal completion; a build
    killed by timeout or cancellation dies on SIGTERM without unwinding, so its
    orphans are reclaimed by the next build's pre-test sweep. CodeBuild only, so
    it cannot kill a Maya a developer opened.
    """
    if not os.environ.get("CODEBUILD_BUILD_ID"):
        _log(f"{phase}: not running in CodeBuild; skipping orphan cleanup")
        return

    # The sweep is best effort and must never fail the build. Importing psutil
    # here rather than at module scope keeps a missing dependency recoverable: at
    # module scope the ImportError would be raised before main() and fail outright.
    try:
        import psutil
    except ImportError:
        _log(f"{phase}: psutil unavailable; skipping orphan cleanup")
        return

    # Guards against self-termination if this is ever called from mayapy.
    protected_pids = {os.getpid()}

    orphans = find_orphaned_maya_processes(psutil, protected_pids)
    if not orphans:
        _log(f"{phase}: no orphaned Maya processes found")
        return

    _log(f"{phase}: terminating {len(orphans)} orphaned Maya process(es):")
    terminated = []
    for proc, cmdline in orphans:
        _log(f"  pid={proc.pid} {cmdline[:160]}")
        try:
            proc.terminate()
            terminated.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            _log(f"  pid={proc.pid} terminate failed: {exc}")

    # Only wait on processes actually signalled, so a failed terminate does not
    # cost 15s and get reported as though it had ignored the signal.
    _, still_alive = psutil.wait_procs(terminated, timeout=15)
    for proc in still_alive:
        # terminate() is SIGTERM on POSIX but an alias for kill() on Windows, so
        # this escalation only ever fires on POSIX.
        _log(f"  pid={proc.pid} did not exit within 15s; killing")
        try:
            proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            _log(f"  pid={proc.pid} kill failed: {exc}")


def _cleanup(phase: str) -> None:
    """Run a sweep, ensuring a cleanup failure cannot change the build result."""
    try:
        release_orphaned_maya_licenses(phase)
    except Exception as exc:  # noqa: BLE001
        _log(f"{phase}: cleanup failed: {exc}")


def main():
    _cleanup("pre-test")

    # hatch sets MAYA_VERSION per integ-ci matrix cell. Fail if it is not set:
    # setting a default version would run the whole suite against an unintended Maya.
    maya_version = os.environ.get("MAYA_VERSION")
    if not maya_version:
        sys.exit("MAYA_VERSION is not set; hatch sets it per integ-ci matrix cell.")
    system = platform.system()

    if system == "Windows":
        maya_bin = f"C:\\Program Files\\Autodesk\\Maya{maya_version}\\bin"
        os.environ["PATH"] = maya_bin + ";" + os.environ.get("PATH", "")

        # Redshift plugin paths (not auto-registered like V-Ray/MtoA)
        rs_root = "C:\\Program Files\\Maxon Redshift 2026"
        rs_plugin = f"{rs_root}\\Plugins\\Maya\\{maya_version}\\nt-x86-64"
        rs_scripts = f"{rs_root}\\Plugins\\Maya\\Common\\scripts"
        rs_desc = f"{rs_root}\\Plugins\\Maya\\Common\\rendererDesc"

        os.environ["MAYA_PLUG_IN_PATH"] = rs_plugin + ";" + os.environ.get("MAYA_PLUG_IN_PATH", "")
        os.environ["MAYA_SCRIPT_PATH"] = rs_scripts + ";" + os.environ.get("MAYA_SCRIPT_PATH", "")
        os.environ["MAYA_RENDER_DESC_PATH"] = (
            rs_desc + ";" + os.environ.get("MAYA_RENDER_DESC_PATH", "")
        )
        os.environ["REDSHIFT_COREDATAPATH"] = rs_root
        # Redshift's .mll depends on DLLs in its bin directory
        os.environ["PATH"] = f"{rs_root}\\bin;" + os.environ["PATH"]

        # Renderer licensing (Machine-level env vars don't take effect in current session)
        license_dns = os.environ.get("LICENSE_ENDPOINT_DNS", "")
        if license_dns:
            os.environ.setdefault("VRAY_AUTH_CLIENT_SETTINGS", f"licset://{license_dns}:30304")
            os.environ.setdefault("VRAY_AUTH_CLIENT_FILE_PATH", "/null")
            os.environ.setdefault("redshift_LICENSE", f"7054@{license_dns}")
            os.environ.setdefault("ADSKFLEX_LICENSE_FILE", f"2702@{license_dns};2701@{license_dns}")

    # Linux resolves mayapy through the MAYA_VERSION dispatcher written by setup-runner.py
    try:
        result = subprocess.run(
            ["mayapy", "-m", "pytest", "--no-cov", "test/integ", "-vvv", "--numprocesses=1"]
        )
    finally:
        _cleanup("post-test")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
