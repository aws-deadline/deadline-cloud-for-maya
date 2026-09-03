# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Run integration tests with correct environment for each platform.

Sets Maya's bin on PATH and renderer environment variables so the adaptor's
subprocess can find mayapy and renderer plugins.
"""

import os
import platform
import subprocess
import sys
import tempfile


def install_adaptor_shims() -> str:
    """Route the adaptor entry points through mayapy and return the shim directory.

    The job templates enter their Maya environment with ``command: MayaAdaptor``,
    which openjd resolves from PATH. That finds the hatch environment's console
    script, whose interpreter is a different build of Python 3.13 than the one
    Maya 2027 bundles (3.13.15 vs Autodesk's 3.13.9-dirty). Autodesk's mayapy
    exports Maya's lib directories on LD_LIBRARY_PATH and every child inherits
    them, so that foreign interpreter loads Maya's libpython3.13.so.1.0 and
    segfaults on its first native import -- yaml and pydantic_core both die,
    which kills the adaptor before it logs anything.

    Maya 2025 and 2026 bundle Python 3.11, so there is no matching soname and no
    collision; this only affects 2027.

    Running the adaptor under mayapy removes the mismatch: the adaptor and the
    Maya client it spawns then share one interpreter and one libpython. This
    matches how the adaptor runs on a farm, where the maya-openjd Conda package
    installs into Maya's own prefix.
    """
    shim_dir = os.path.join(tempfile.gettempdir(), "maya-adaptor-shims")
    os.makedirs(shim_dir, exist_ok=True)
    for name in ("MayaAdaptor", "maya-openjd"):
        shim = os.path.join(shim_dir, name)
        with open(shim, "w") as handle:
            handle.write('#!/bin/sh\nexec mayapy -m deadline.maya_adaptor.MayaAdaptor "$@"\n')
        os.chmod(shim, 0o755)
    return shim_dir


def main():
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
    if system == "Linux":
        shim_dir = install_adaptor_shims()
        os.environ["PATH"] = shim_dir + os.pathsep + os.environ.get("PATH", "")
        print(f"Adaptor shims installed at {shim_dir} and prepended to PATH", flush=True)

    # TEMPORARY: run the libpython collision diagnostic under mayapy so it sees
    # the same environment the adaptor subprocess does. Remove with the
    # diagnose_libpython.py file once the 2027 segfault is resolved.
    diagnostic = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagnose_libpython.py")
    if os.path.isfile(diagnostic):
        print("=== libpython collision diagnostic ===", flush=True)
        subprocess.run(["mayapy", diagnostic], check=False)
        print("=== end diagnostic ===", flush=True)

    sys.exit(
        subprocess.run(
            ["mayapy", "-m", "pytest", "--no-cov", "test/integ", "-vvv", "--numprocesses=1"]
        ).returncode
    )


if __name__ == "__main__":
    main()
