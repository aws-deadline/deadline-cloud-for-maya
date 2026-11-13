# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Run Maya submitter GUI tests on an isolated Linux X11 desktop.

Use through ``hatch run integ-gui:test-linux`` so pytest and xa11y are installed
in the interpreter running this script. Requires full GUI Maya, a configured
license, and ``hatch run install --maya-version YEAR``.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DESKTOP_TOOLS = ("dbus-run-session", "dbus-daemon", "xvfb-run", "Xvfb", "xauth")


def test_environment(base: Mapping[str, str], maya_executable: Path) -> dict[str, str]:
    """Enable Qt's AT-SPI bridge on the new desktop and use software OpenGL."""
    env = dict(base)
    # Do not connect the isolated display to the invoking desktop's D-Bus/AT-SPI
    # session. dbus-run-session supplies a fresh address to Maya and pytest.
    for name in (
        "DBUS_SESSION_BUS_ADDRESS",
        "AT_SPI_BUS_ADDRESS",
        "SESSION_MANAGER",
        # GUI tests share a desktop; inherited options must not enable xdist.
        "PYTEST_ADDOPTS",
    ):
        env.pop(name, None)
    env.update(
        MAYA_EXECUTABLE=str(maya_executable),
        QT_ACCESSIBILITY="1",
        QT_LINUX_ACCESSIBILITY_ALWAYS_ON="1",
        NO_AT_BRIDGE="0",
        # dbus-broker needs a systemd user session, which this desktop lacks.
        ATSPI_DBUS_IMPLEMENTATION="dbus-daemon",
        LIBGL_ALWAYS_SOFTWARE="1",
        QT_QPA_PLATFORM="xcb",
    )
    return env


def test_command(pytest_args: Sequence[str]) -> list[str]:
    """Keep Maya and xa11y in the same X11 and D-Bus session, with serial tests."""
    return [
        "dbus-run-session",
        "--",
        "xvfb-run",
        "--auto-servernum",
        "--server-args=-screen 0 1920x1080x24 -nolisten tcp",
        sys.executable,
        "-m",
        "pytest",
        "-o",
        "addopts=",
        "-p",
        "no:cacheprovider",
        "test/integ_gui",
        "-vv",
        *pytest_args,
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--maya-executable",
        default=os.environ.get("MAYA_EXECUTABLE"),
        help="Full GUI Maya executable; defaults to MAYA_EXECUTABLE.",
    )
    parser.add_argument(
        "pytest_args", nargs=argparse.REMAINDER, help="Additional pytest options after --."
    )
    args = parser.parse_args(argv)
    if sys.platform != "linux":
        parser.error("This runner requires Linux.")
    if not args.maya_executable:
        parser.error("Set MAYA_EXECUTABLE or pass --maya-executable for full GUI Maya.")
    maya_executable = Path(args.maya_executable).expanduser().resolve()
    if not maya_executable.is_file() or not os.access(maya_executable, os.X_OK):
        parser.error(f"Maya executable is missing or not executable: {maya_executable}")
    if not (REPO_ROOT / "plugin_env" / "Maya.env").is_file():
        parser.error("Run hatch run install --maya-version YEAR before running GUI tests.")
    missing = [name for name in DESKTOP_TOOLS if shutil.which(name) is None]
    if missing:
        parser.error(f"Install the Linux desktop tools: {', '.join(missing)}")
    pytest_args = args.pytest_args
    if pytest_args[:1] == ["--"]:
        pytest_args = pytest_args[1:]
    # xvfb-run and dbus-run-session tear down their services when pytest exits,
    # including when pytest fails. The Maya fixture stops its process tree.
    return subprocess.run(
        test_command(pytest_args),
        cwd=REPO_ROOT,
        env=test_environment(os.environ, maya_executable),
        check=False,
    ).returncode


if __name__ == "__main__":
    sys.exit(main())
