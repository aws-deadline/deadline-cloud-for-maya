# Maya submitter GUI tests

These tests drive the real submitter through xa11y against a local mock Deadline
Cloud service. The same six cases run on Windows and Linux: export the cube,
layers, layers without variation, and referenced layers bundles; override the
frame range; and submit a job. They do not submit to a real farm.

## Linux

Install **full GUI Maya**, configure its license, and install the Linux libraries
required by that Maya release. The Maya IO installer used by
`pipeline/setup-runner.py` is intended for the existing render/adaptor tests;
do not use it to provision this GUI suite.

The test desktop needs Xvfb, xauth, D-Bus, AT-SPI, software OpenGL, and Maya's Qt
X11 dependencies. On Ubuntu, the desktop packages include `xvfb xauth dbus-x11
at-spi2-core libgl1-mesa-dri`. On RHEL-compatible systems, use the corresponding
`xorg-x11-server-Xvfb xorg-x11-xauth dbus-x11 at-spi2-core mesa-dri-drivers`
packages. These are desktop prerequisites, not a complete Maya dependency list.
Qt must ship its AT-SPI accessibility bridge.

From the repository root:

```sh
hatch run install --maya-version 2027
export MAYA_EXECUTABLE=/usr/autodesk/maya2027/bin/maya
# Use your configured network license server, if applicable.
export ADSKFLEX_LICENSE_FILE=27002@your-license-server
hatch run integ-gui:test-linux -- --basetemp /tmp/maya-gui-tests -rA
```

`test-linux` starts a separate X11 display and D-Bus session for pytest and Maya,
enables Qt accessibility, and uses software OpenGL. AT-SPI uses `dbus-daemon`
rather than a bus broker that requires a systemd user session. It preserves the user profile
and license environment. It requires an explicit executable and developer
submitter install, so missing prerequisites fail instead of silently skipping
the suite. Extra pytest options go after `--`, for example `-- -k frame_range`.

For an existing accessible Linux desktop, use `hatch run integ-gui:test` instead.
Set `QT_ACCESSIBILITY=1` and `QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1` before launching.

## Windows

The Windows workflow is `.github/workflows/integ_gui_windows.yml`. On a licensed
workstation, install the developer submitter, set `MAYA_EXECUTABLE` if needed,
and run `hatch run integ-gui:test`.

## Diagnostics

Each test gets fresh Maya preferences and a mock client configuration. Its
temporary directory contains `maya.log`, `maya_process.log` (process stdout and
stderr), and `opener_status.txt`. Failures also attempt a desktop screenshot;
startup timeouts include an accessibility tree to help identify licensing or
first-launch prompts. Keep `--basetemp` outside the repository and retain the
directory after a failed run.

The Linux runner can be used on a CI machine with full GUI Maya and a configured
license. Automatic Linux installer provisioning and a Linux CI workflow still
need a verified full Maya installer and a supported runner image.
