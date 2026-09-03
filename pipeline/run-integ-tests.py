# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Run integration tests with correct environment for each platform.

Sets Maya's bin on PATH and renderer environment variables so the adaptor's
subprocess can find mayapy and renderer plugins.
"""

import os
import platform
import subprocess
import sys


def main():
    maya_version = os.environ.get("MAYA_VERSION", "2025")
    # Linux's mayapy dispatcher reads this, so export the resolved value.
    os.environ["MAYA_VERSION"] = maya_version
    system = platform.system()

    # Linux only: the adaptor daemon is a subprocess, so it inherits these rather
    # than pytest's faulthandler. Without them a SIGSEGV discards the unflushed
    # stdout. On Windows they make the Maya client dump the ERROR_NO_TOKEN
    # exceptions it otherwise handles, which breaks session cleanup.
    if system != "Windows":
        os.environ["PYTHONUNBUFFERED"] = "1"
        os.environ["PYTHONFAULTHANDLER"] = "1"

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

    # Linux resolves mayapy through the MAYA_VERSION dispatcher written by
    # setup-runner.py, and runs the adaptor under mayapy via these dispatchers, which
    # must precede the hatch env's console scripts. See _write_adaptor_dispatchers.
    if system != "Windows":
        os.environ["PATH"] = "/usr/local/maya-adaptor-bin:" + os.environ.get("PATH", "")

    # EXPERIMENT, revert or keep with evidence before merge: Maya 2027's hardware
    # renderer (mayaHardware2) renders, then aborts in PNG postprocessing on the
    # headless Linux runner -- libpng receives garbage IHDR dimensions and corrupts
    # the heap (SIGABRT). 2025/2026 pass on identical infrastructure, and 2027
    # renders the same scene pixel-correct on a workstation, so the suspect is how
    # 2027 acquires its offscreen VP2 GL device. Pin the device via Autodesk's
    # documented MAYA_VP2_DEVICE_OVERRIDE to test that theory.
    # Linux values: VirtualDeviceGLCore (core profile) or VirtualDeviceGL (legacy).
    # VirtualDeviceGLCore failed identically to the default (same libpng abort), so
    # try the legacy device next.
    if system == "Linux" and maya_version == "2027":
        os.environ.setdefault("MAYA_VP2_DEVICE_OVERRIDE", "VirtualDeviceGL")
        print(
            f"MAYA_VP2_DEVICE_OVERRIDE={os.environ['MAYA_VP2_DEVICE_OVERRIDE']} (2027 VP2 experiment)",
            flush=True,
        )

    # TEMPORARY, revert before merge: xdist relays worker output and only prints it once
    # a test finishes, so a test that never finishes prints nothing. Run in-process with
    # capture disabled to stream the Maya 2027 adaptor hang as it happens.
    # TEMPORARY: render the minimal scene directly per image format to locate the
    # 2027 VP2/libpng abort. Runs before pytest; its own crash must not stop the run.
    if system == "Linux" and maya_version == "2027":
        diag = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagnose_vp2.py")
        if os.path.isfile(diag):
            print("=== vp2 artifact diagnostic ===", flush=True)
            subprocess.run(["mayapy", diag], check=False)
            print("=== end vp2 diagnostic ===", flush=True)

    cmd = [
        "mayapy",
        "-m",
        "pytest",
        "--no-cov",
        "test/integ",
        "-vvv",
        "--numprocesses=0",
        "-s",
        *sys.argv[1:],
    ]
    print(f"Running: {' '.join(cmd)}", flush=True)

    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
