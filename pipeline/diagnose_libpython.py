#!/usr/bin/env python3
"""TEMPORARY diagnostic for the Maya 2027 adaptor SIGSEGV.

Round 1 established that the host interpreter (Python 3.13.15) links Maya
2027's bundled libpython3.13.so.1.0 (Autodesk build 3.13.9-dirty) because
Autodesk's own mayapy script puts Maya's lib directories on LD_LIBRARY_PATH,
and every child inherits it. A bare print() survives that; `MayaAdaptor
--help` segfaults, so the fault needs a native import to trigger.

This round answers two questions:
  A. Which import kills the host interpreter under the inherited environment?
  B. Which candidate fix works --
       B1. scrub Maya's lib entries from LD_LIBRARY_PATH, or
       B2. run the adaptor under mayapy instead of the host interpreter.

Delete this file and its call in run-integ-tests.py once resolved.
"""

import os
import shutil
import subprocess
import sys


def show(label: str, value: object) -> None:
    print(f"[diag] {label}: {value}", flush=True)


def run(argv: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, check=False, env=env)


def describe(label: str, result: subprocess.CompletedProcess) -> None:
    detail = (result.stderr or result.stdout).strip().splitlines()
    tail = detail[-1][:200] if detail else ""
    suffix = f"  ({tail})" if tail else ""
    show(label, f"rc={result.returncode}{suffix}")


def scrubbed_env(maya_location: str) -> dict:
    """Inherited environment with Maya's lib directories removed from the loader path."""
    entries = os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep)
    kept = [
        e for e in entries if e and "mayaIO" not in e and maya_location not in os.path.realpath(e)
    ]
    env = dict(os.environ)
    if kept:
        env["LD_LIBRARY_PATH"] = os.pathsep.join(kept)
    else:
        env.pop("LD_LIBRARY_PATH", None)
    return env


def main() -> None:
    maya_location = os.environ.get("MAYA_LOCATION", "")
    host = shutil.which("python") or shutil.which("python3")
    adaptor = shutil.which("MayaAdaptor")
    show("host python", host)
    show("MayaAdaptor", adaptor)
    show("mayapy (this process)", sys.executable)

    # --- A. Find the import that faults, under the inherited environment. ---
    if host:
        for module in (
            "encodings",  # trivial, pure python
            "yaml",
            "pydantic_core",
            "openjd.adaptor_runtime",
            "deadline.maya_adaptor",
        ):
            describe(
                f"A: host python -c 'import {module}'",
                run([host, "-c", f"import {module}; print('ok')"]),
            )

    # --- B1. Does scrubbing Maya's lib from LD_LIBRARY_PATH fix the adaptor? ---
    if adaptor and maya_location:
        env = scrubbed_env(maya_location)
        show("B1: scrubbed LD_LIBRARY_PATH", env.get("LD_LIBRARY_PATH", "(unset)"))
        describe("B1: MayaAdaptor --help (scrubbed)", run([adaptor, "--help"], env=env))
        if host:
            describe(
                "B1: host python -c 'import deadline.maya_adaptor' (scrubbed)",
                run([host, "-c", "import deadline.maya_adaptor; print('ok')"], env=env),
            )

    # --- B2. Does running the adaptor under mayapy work? ---
    mayapy = shutil.which("mayapy") or sys.executable
    describe(
        "B2: mayapy -m deadline.maya_adaptor.MayaAdaptor --help",
        run([mayapy, "-m", "deadline.maya_adaptor.MayaAdaptor", "--help"]),
    )
    describe(
        "B2: mayapy -c 'import deadline.maya_adaptor'",
        run([mayapy, "-c", "import deadline.maya_adaptor; print('ok')"]),
    )

    # Baseline for comparison.
    if adaptor:
        describe("baseline: MayaAdaptor --help (inherited)", run([adaptor, "--help"]))


if __name__ == "__main__":
    main()
