#!/usr/bin/env python3
"""TEMPORARY diagnostic for the Maya 2027 adaptor SIGSEGV.

Run under mayapy so it inherits exactly the environment the adaptor subprocess
gets (notably LD_LIBRARY_PATH, which the /usr/local/bin/mayapy wrapper sets).

Hypothesis: Maya 2027 bundles Python 3.13 and the build host's Python is also
3.13, so they share the libpython3.13.so.1.0 soname. The wrapper puts Maya's
lib directory first on LD_LIBRARY_PATH, every child inherits it, and the host
interpreter that runs the MayaAdaptor console script loads Maya's libpython
instead of its own and crashes before producing any output.

Delete this file and its call in run-integ-tests.py once resolved.
"""

import glob
import os
import platform
import shutil
import subprocess
import sys


def show(label: str, value: object) -> None:
    print(f"[diag] {label}: {value}", flush=True)


def main() -> None:
    show("sys.executable", sys.executable)
    show("sys.version", sys.version.replace("\n", " "))
    show("platform", platform.system())
    show("MAYA_LOCATION", os.environ.get("MAYA_LOCATION"))
    show("LD_LIBRARY_PATH", os.environ.get("LD_LIBRARY_PATH"))

    maya_location = os.environ.get("MAYA_LOCATION", "")
    if maya_location:
        libs = sorted(glob.glob(os.path.join(maya_location, "lib", "libpython*")))
        show("maya bundled libpython", libs or "none found")

    for name in ("MayaAdaptor", "maya-openjd", "mayapy", "python", "python3"):
        show(f"which {name}", shutil.which(name))

    adaptor = shutil.which("MayaAdaptor")
    if adaptor:
        try:
            with open(adaptor, "rb") as handle:
                show("MayaAdaptor shebang", handle.readline().decode("utf-8", "replace").strip())
        except OSError as exc:
            show("MayaAdaptor shebang", f"unreadable: {exc}")

    host = shutil.which("python") or shutil.which("python3")
    if not host:
        show("VERDICT", "no host python on PATH; cannot test the collision")
        return

    real_host = os.path.realpath(host)
    show("host python realpath", real_host)

    if platform.system() == "Linux":
        result = subprocess.run(["ldd", real_host], capture_output=True, text=True, check=False)
        matches = [line.strip() for line in result.stdout.splitlines() if "libpython" in line]
        show("host python ldd libpython", matches or "no libpython entries")

    probe = [host, "-c", "print('host interpreter started ok')"]

    # 1. Inherited environment. Expect returncode -11 if the hypothesis holds.
    inherited = subprocess.run(probe, capture_output=True, text=True, check=False)
    show("host python returncode (inherited env)", inherited.returncode)
    show("host python stdout", inherited.stdout.strip())
    show("host python stderr", inherited.stderr.strip()[:400])

    # 2. Same probe with Maya's lib directory removed from LD_LIBRARY_PATH.
    #    If this succeeds where the above crashed, the fix is confirmed too.
    ld_path = os.environ.get("LD_LIBRARY_PATH", "")
    if ld_path and maya_location:
        cleaned = os.pathsep.join(
            entry
            for entry in ld_path.split(os.pathsep)
            if entry and not entry.startswith(maya_location)
        )
        env = dict(os.environ, LD_LIBRARY_PATH=cleaned)
        without_maya = subprocess.run(probe, capture_output=True, text=True, check=False, env=env)
        show("LD_LIBRARY_PATH without maya", cleaned or "(empty)")
        show("host python returncode (maya lib removed)", without_maya.returncode)

        if inherited.returncode != 0 and without_maya.returncode == 0:
            show("VERDICT", "CONFIRMED: Maya lib on LD_LIBRARY_PATH crashes the host interpreter")
        elif inherited.returncode == 0:
            show("VERDICT", "NOT the cause: host interpreter runs fine under the inherited env")
        else:
            show("VERDICT", "INCONCLUSIVE: host interpreter fails either way")

    # 3. The actual failing command, for completeness.
    if adaptor:
        helped = subprocess.run([adaptor, "--help"], capture_output=True, text=True, check=False)
        show("MayaAdaptor --help returncode", helped.returncode)
        show("MayaAdaptor --help stderr", helped.stderr.strip()[:300])


if __name__ == "__main__":
    main()
