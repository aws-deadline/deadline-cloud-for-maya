# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Run integration tests with correct environment for each platform.

Releases Autodesk licenses held by Maya processes orphaned by earlier builds,
then sets Maya's bin on PATH and renderer environment variables so the
adaptor's subprocess can find mayapy and renderer plugins.
"""

import os
import platform
import subprocess
import sys

# Command-line fragments identifying a process that can hold an Autodesk
# (FlexLM) license checkout.
_MAYA_PROCESS_MARKERS = ("mayapy", "maya_client.py", "maya.bin", "maya.exe")


def _log(message):
    """Print a cleanup message, flushing immediately.

    This script's stdout is a pipe under CodeBuild and therefore block
    buffered, while the pytest subprocess inherits the same descriptor and
    writes to it directly. Without an explicit flush the parent's output is
    not emitted until interpreter exit, so these messages surface *after* all
    test output and read as though cleanup ran last.
    """
    print(f"[license-cleanup] {message}", flush=True)


def find_orphaned_maya_processes(psutil, protected_pids):
    """Return [(process, cmdline)] for Maya processes not in protected_pids.

    Separated from termination so the matching logic can be exercised without
    signalling anything.
    """
    orphans = []
    for proc in psutil.process_iter(["pid", "cmdline"]):
        if proc.pid in protected_pids:
            continue
        try:
            cmdline = " ".join(proc.info.get("cmdline") or [])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if any(marker in cmdline for marker in _MAYA_PROCESS_MARKERS):
            orphans.append((proc, cmdline))
    return orphans


def release_orphaned_maya_licenses(phase):
    """Terminate Maya processes left behind on this host, releasing their licenses.

    Called twice per suite run: ``pre-test`` so a previous build's leftovers
    cannot starve this one, and ``post-test`` so this build cannot starve the
    next. The two cover different failures -- a build killed before it reaches
    the post-test sweep is caught by the next build's pre-test sweep.

    CI runs on CodeBuild reserved-capacity fleets whose hosts are reused between
    builds. When a Maya process dies without releasing its Autodesk license --
    for example when ``maya.standalone.initialize()`` raises and the test
    fixture's ``uninitialize()`` teardown never runs -- the checkout is never
    returned, and the orphan keeps its license session alive indefinitely. Once
    enough accumulate, later checkouts are refused and Maya reports it as the
    misleading "Error encountered when initializing Maya - Please check for
    sufficient disk space and necessary write permissions of MAYA_APP_DIR."

    No Maya process should be running either before the suite starts or after it
    exits, so anything matched here is an orphan and safe to terminate.

    Restricted to CodeBuild. The reused-host problem does not exist on a
    developer machine, where a running Maya is far more likely to be one the
    developer opened deliberately.
    """
    if not os.environ.get("CODEBUILD_BUILD_ID"):
        _log(f"{phase}: not running in CodeBuild; skipping orphan cleanup")
        return

    try:
        import psutil
    except ImportError:
        _log(f"{phase}: psutil unavailable; skipping orphan cleanup")
        return

    # This runner is plain Python, not mayapy, so it cannot match its own
    # command line. The guard matters only if this is ever called from inside a
    # Maya interpreter, where an unguarded sweep would terminate itself.
    protected_pids = {os.getpid()}

    orphans = find_orphaned_maya_processes(psutil, protected_pids)
    if not orphans:
        _log(f"{phase}: no orphaned Maya processes found")
        return

    _log(f"{phase}: terminating {len(orphans)} orphaned Maya process(es):")
    for proc, cmdline in orphans:
        _log(f"  pid={proc.pid} {cmdline[:160]}")
        try:
            proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            _log(f"  pid={proc.pid} terminate failed: {exc}")

    _, still_alive = psutil.wait_procs([proc for proc, _ in orphans], timeout=15)
    for proc in still_alive:
        _log(f"  pid={proc.pid} ignored SIGTERM; sending SIGKILL")
        try:
            proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            _log(f"  pid={proc.pid} kill failed: {exc}")


def main():
    release_orphaned_maya_licenses("pre-test")

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
        # A cleanup failure must never change the build result.
        try:
            release_orphaned_maya_licenses("post-test")
        except Exception as exc:  # noqa: BLE001
            _log(f"post-test: cleanup failed: {exc}")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
