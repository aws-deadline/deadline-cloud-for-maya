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

_MAYA_PROCESS_MARKERS = ("mayapy", "maya_client.py", "maya.bin", "maya.exe")

# Fallback for processes whose command line cannot be read: executable names that
# can hold a license. Compared lowercased, exact match.
_MAYA_PROCESS_NAMES = frozenset(
    {"mayapy", "mayapy.bin", "mayapy.exe", "maya", "maya.bin", "maya.exe"}
)


def _log(message):
    """Log a cleanup message.

    flush=True keeps ordering against the pytest subprocess, which writes to the
    same descriptor; unflushed output appears after all test output.
    """
    print(f"[license-cleanup] {message}", flush=True)


def find_orphaned_maya_processes(psutil, protected_pids):
    """Return [(process, description)] for Maya processes not in protected_pids.

    Matches on the command line, falling back to the executable name when the
    command line cannot be read, which psutil reports as None. The fallback
    matters because an unreadable process could be the orphan we are looking for,
    and the name stays readable when the command line does not.

    Kept separate from termination so matching can be tested without killing
    processes.
    """
    orphans = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        if proc.pid in protected_pids:
            continue
        cmdline_parts = proc.info.get("cmdline")
        if cmdline_parts is None:
            name = proc.info.get("name") or ""
            if name.lower() in _MAYA_PROCESS_NAMES:
                orphans.append((proc, f"name={name} (command line unreadable)"))
            continue
        cmdline = " ".join(cmdline_parts)
        if any(marker in cmdline for marker in _MAYA_PROCESS_MARKERS):
            orphans.append((proc, cmdline))
    return orphans


def release_orphaned_maya_licenses(phase):
    """Terminate leftover Maya processes, releasing their Autodesk licenses.

    CodeBuild reserved-capacity hosts are reused between builds. A Maya that
    dies without releasing its license -- e.g. when maya.standalone.initialize()
    raises and the test fixture's uninitialize() teardown never runs -- holds the
    checkout open indefinitely, and once enough accumulate later checkouts are
    refused. Maya reports that refusal as a misleading MAYA_APP_DIR disk-space
    error.

    Runs pre-test (recover from earlier builds) and post-test (don't poison the
    next). CodeBuild only, so it cannot kill a Maya a developer opened.
    """
    if not os.environ.get("CODEBUILD_BUILD_ID"):
        _log(f"{phase}: not running in CodeBuild; skipping orphan cleanup")
        return

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
    for proc, description in orphans:
        _log(f"  pid={proc.pid} {description[:160]}")
        try:
            proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            _log(f"  pid={proc.pid} terminate failed: {exc}")

    _, still_alive = psutil.wait_procs([proc for proc, _ in orphans], timeout=15)
    for proc in still_alive:
        # terminate() is SIGTERM on POSIX but an alias for kill() on Windows, so
        # this escalation only ever fires on POSIX.
        _log(f"  pid={proc.pid} did not exit within 15s; killing")
        try:
            proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            _log(f"  pid={proc.pid} kill failed: {exc}")


def _cleanup(phase):
    """Run a sweep, ensuring a cleanup failure cannot change the build result."""
    try:
        release_orphaned_maya_licenses(phase)
    except Exception as exc:  # noqa: BLE001
        _log(f"{phase}: cleanup failed: {exc}")


def main():
    _cleanup("pre-test")

    maya_version = os.environ.get("MAYA_VERSION", "2025")
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

    # Linux uses wrapper script at /usr/local/bin/mayapy that handles all env setup

    try:
        result = subprocess.run(
            ["mayapy", "-m", "pytest", "--no-cov", "test/integ", "-vvv", "--numprocesses=1"]
        )
    finally:
        _cleanup("post-test")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
