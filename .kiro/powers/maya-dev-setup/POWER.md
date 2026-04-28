---
name: maya-dev-setup
version: 1.0.0
displayName: Maya Dev Setup
description: Automated development environment setup for deadline-cloud-for-maya - builds packages, installs dependencies, and configures environment variables
keywords:
  - maya
  - deadline
  - setup
  - build
  - install
  - environment
  - development
  - hatch
  - openjd
author: AWS Deadline Cloud
---

# Maya Dev Setup Power

Automated development environment setup for deadline-cloud-for-maya project.

## What This Power Does

This power automates the complete development environment setup for working on the deadline-cloud-for-maya project. It handles everything from installing Maya and renderers to building packages, installing dependencies, and configuring environment variables.

## Setup Steps Performed

1. **Documentation Review** - Reads README.md and DEVELOPMENT.md to understand project requirements
2. **Maya Installation** - If Maya is not found, installs from S3 archive using CLI commands (RPM extraction on Linux, installer on Windows/macOS)
3. **Renderer Installation** - Installs Arnold (MtoA), V-Ray, and/or Redshift from S3 archives, creates `.mod` module files
4. **Hatch Installation** - Installs and configures Hatch build tool
5. **Package Build** - Builds wheel and source distributions
6. **Dev Submitter Installation** - Runs `hatch run install` to create plugin_env/
7. **Dependencies Installation** - Installs deadline, openjd-adaptor-runtime
8. **Wheel Installation** - Installs the built wheel for adaptor
9. **OpenJD CLI Installation** - Installs openjd-cli for running integration tests
10. **Test Packages Installation** - Installs pytest, coverage, and test dependencies into Maya's Python
11. **Environment Configuration** - Sets up MAYAPY_EXECUTABLE, PATH, MAYA_MODULE_PATH, and MAYA_ENV_DIR

## Prerequisites

- Python 3.9 or higher installed on system
- Linux (RHEL/AL2023), macOS, or Windows operating system
- For CLI installation: Maya and renderer installer archives accessible from S3 or local disk
- For manual installation: Maya 2024-2026 already installed with a valid license

### Developer Licensing

Set these environment variables before launching Maya or running tests:

```bash
# Linux/macOS
export ADSKFLEX_LICENSE_FILE=27002@localhost        # Autodesk (Maya)
export FLEXLM_TIMEOUT=3000000                       # Avoid timeout errors
export redshift_LICENSE=5054@localhost               # Redshift (case sensitive!)
export PIXAR_LICENSE_FILE=9010@localhost             # RenderMan (if needed)
```

```powershell
# Windows
$env:ADSKFLEX_LICENSE_FILE = "27002@localhost"       # Autodesk (Maya)
$env:FLEXLM_TIMEOUT = "3000000"                      # Avoid timeout errors
$env:redshift_LICENSE = "5054@localhost"              # Redshift (case sensitive!)
$env:PIXAR_LICENSE_FILE = "9010@localhost"            # RenderMan (if needed)
```

**Note:** V-Ray uses ChaosGroup OLS licensing on port 30304. Arnold (MtoA) is included with the Autodesk Maya license. The integration tests set `ArnoldErrorOnLicenseFailure=false` so Arnold renders with a watermark if unlicensed — tests still pass.

#### License Ports Reference

| Vendor | Product | Port | Env Var |
|--------|---------|------|---------|
| Autodesk | Maya | 27002 | `ADSKFLEX_LICENSE_FILE` |
| ChaosGroup | V-Ray | 30304 | OLS (GUI config) |
| Maxon/Redshift | Redshift | 5054 | `redshift_LICENSE` |
| Pixar | RenderMan | 9010 | `PIXAR_LICENSE_FILE` |

See the full port list at the [License Ports wiki](https://w.amazon.com/bin/view/EC2/Thinkbox/ServicesTeam/Projects/DeveloperLicencing/LicensePorts).

## CLI Installer Installation (from S3 Archives)

If Maya and renderer installers are hosted on S3, install them directly on the workstation using CLI commands. The commands below are derived from the [deadline-cloud-samples conda build scripts](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/conda_recipes), which document the exact extraction and configuration steps for each application.

**Note:** Linux commands assume RHEL/AL2023 (`dnf`). For Ubuntu/Debian, substitute `apt-get` for package installation. macOS install commands use standard macOS patterns but are not sourced from the conda recipes (which only cover Linux and Windows). Windows Maya installation is GUI-based — there is no true silent CLI installer.

### Source Archives

Download these from your Autodesk/vendor accounts or internal S3 bucket:

| Application | Linux Archive | Windows |
|-------------|--------------|---------|
| Maya 2025 | `Autodesk_Maya_2025_Linux_64bit.tgz` | Self-extracting `.sfx.exe` from Autodesk |
| Arnold (MtoA) | Bundled inside Maya installer (`Packages/package.zip`) | Bundled inside Maya installer (`Arnold/` dir) |
| V-Ray 2025 | `vray_adv_71000_maya2025_rhel8` (self-extracting) | GUI installer from Chaos |
| Redshift 2025 | `redshift_2025.4.2_1782753868_linux_x64.run` | GUI installer from Maxon |

Archive filenames are version-specific examples. Adjust for your target version.

### Installing Maya — Linux

Source: [`maya-2025/recipe/build.sh`](https://github.com/aws-deadline/deadline-cloud-samples/blob/mainline/conda_recipes/maya-2025/recipe/build.sh)

```bash
MAYA_VERSION=2025

# Extract the installer archive
mkdir -p /tmp/maya_installer
tar xzf Autodesk_Maya_${MAYA_VERSION}_Linux_64bit.tgz -C /tmp/maya_installer

# Extract the Maya RPM
cd /
sudo rpm2cpio /tmp/maya_installer/Packages/Maya${MAYA_VERSION}_64-${MAYA_VERSION}.*.x86_64.rpm | sudo cpio -idm

# Create the maya symlink
sudo ln -s "/usr/autodesk/maya${MAYA_VERSION}/bin/maya${MAYA_VERSION}" "/usr/autodesk/maya${MAYA_VERSION}/bin/maya"

# Install system dependencies Maya needs
sudo dnf install -y freetype alsa-lib fontconfig harfbuzz libbrotli graphite2 \
    libxkbfile xcb-util-cursor xcb-util-wm xcb-util-keysyms libxkbcommon-x11

# Remove examples (optional, saves space)
sudo rm -rf "/usr/autodesk/maya${MAYA_VERSION}/Examples"

# Verify
/usr/autodesk/maya${MAYA_VERSION}/bin/mayapy --help
/usr/autodesk/maya${MAYA_VERSION}/bin/maya -batch -command 'print "Hello from Maya"; quit -exitCode 0 -force'
```

### Installing Maya — macOS

```bash
# Mount and install the DMG (adjust volume name for your version)
hdiutil attach Autodesk_Maya_2025_macOS.dmg
sudo installer -pkg "/Volumes/Install Maya 2025/Install Maya 2025.pkg" -target /

# Verify
/Applications/Autodesk/maya2025/Maya.app/Contents/MacOS/mayapy --help
```

### Installing Maya — Windows

Source: [`maya-2025/recipe/build_win.sh`](https://github.com/aws-deadline/deadline-cloud-samples/blob/mainline/conda_recipes/maya-2025/recipe/build_win.sh)

```powershell
# Run the self-extracting installer (launches Maya installer UI — no silent CLI available)
.\Autodesk_Maya_2025_Windows_64bit_dlm_001_002.sfx.exe

# After installation, install pywin32 (required by maya-openjd adaptor on Windows)
& "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install pywin32

# Verify
& "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" --help
& "C:\Program Files\Autodesk\Maya2025\bin\maya.exe" -batch -command 'print "Hello from Maya"; quit -exitCode 0 -force'
```

### Installing Arnold (MtoA) — Linux

Source: [`maya-mtoa-2025/recipe/build.sh`](https://github.com/aws-deadline/deadline-cloud-samples/blob/mainline/conda_recipes/maya-mtoa-2025/recipe/build.sh)

Arnold is bundled inside the Maya installer archive:

```bash
MAYA_VERSION=2025
MTOA_ROOT="/usr/autodesk/arnold/maya${MAYA_VERSION}"

# Extract MtoA from the Maya installer's package.zip
sudo mkdir -p "${MTOA_ROOT}"
cd "${MTOA_ROOT}"
sudo unzip /tmp/maya_installer/Packages/package.zip

# Create the mtoa.mod file so Maya loads the plugin
sudo mkdir -p "/usr/autodesk/modules/maya/${MAYA_VERSION}"
sudo tee "/usr/autodesk/modules/maya/${MAYA_VERSION}/mtoa.mod" > /dev/null <<EOF
+ mtoa any ${MTOA_ROOT}
PATH +:= bin
MAYA_CUSTOM_TEMPLATE_PATH +:= scripts/mtoa/ui/templates
MAYA_SCRIPT_PATH +:= scripts/mtoa/mel
MAYA_RENDER_DESC_PATH += ${MTOA_ROOT}
MAYA_PXR_PLUGINPATH_NAME += ${MTOA_ROOT}/usd
EOF

# Symlink Arnold CLI tools into Maya's bin
for BINARY in kick maketx noice oslc oslinfo; do
    sudo chmod u+x "${MTOA_ROOT}/bin/${BINARY}"
    sudo ln -s "${MTOA_ROOT}/bin/${BINARY}" "/usr/autodesk/maya${MAYA_VERSION}/bin/${BINARY}"
done

# Verify
mayapy -c 'import maya.standalone; maya.standalone.initialize(); import mtoa; print("Arnold OK"); maya.standalone.uninitialize()'
```

### Installing Arnold (MtoA) — Windows

Source: [`maya-mtoa-2025/recipe/build_win.sh`](https://github.com/aws-deadline/deadline-cloud-samples/blob/mainline/conda_recipes/maya-mtoa-2025/recipe/build_win.sh)

Arnold is bundled in the Maya Windows installation under the `Arnold/` directory:

```powershell
$MAYA_VERSION = "2025"
$MTOA_ROOT = "C:\Program Files\Autodesk\Arnold\maya${MAYA_VERSION}"

# Create the module file so Maya loads the plugin
$ModulePath = "C:\Program Files\Autodesk\modules\maya\${MAYA_VERSION}"
New-Item -ItemType Directory -Force -Path $ModulePath

@"
+ mtoa any $MTOA_ROOT
PATH +:= bin
MAYA_CUSTOM_TEMPLATE_PATH +:= scripts/mtoa/ui/templates
MAYA_SCRIPT_PATH +:= scripts/mtoa/mel
MAYA_RENDER_DESC_PATH += $MTOA_ROOT
MAYA_PXR_PLUGINPATH_NAME += $MTOA_ROOT/usd
"@ | Out-File -FilePath "$ModulePath\mtoa.mod" -Encoding ASCII
```

### Installing V-Ray — Linux

Source: [`maya-vray-2025/recipe/build.sh`](https://github.com/aws-deadline/deadline-cloud-samples/blob/mainline/conda_recipes/maya-vray-2025/recipe/build.sh)

```bash
MAYA_VERSION=2025
VRAY_ROOT="/opt/chaos/maya-vray-${MAYA_VERSION}"

# Run the V-Ray self-extracting installer
chmod u+x vray_adv_71000_maya${MAYA_VERSION}_rhel8
sudo mkdir -p "${VRAY_ROOT}"
cd "${VRAY_ROOT}"
sudo /path/to/vray_adv_71000_maya${MAYA_VERSION}_rhel8 -unpackInstall .

# Install system dependencies V-Ray needs
sudo dnf install -y xcb-util-image xcb-util-renderutil xcb-util-cursor \
    xcb-util-wm xcb-util-keysyms libxkbcommon-x11 xcb-util

# Create the VRayForMaya module file
sudo mkdir -p "/usr/autodesk/modules/maya/${MAYA_VERSION}"
sudo cp "${VRAY_ROOT}/maya_root/modules/VRayForMaya.module" \
    "/usr/autodesk/modules/maya/${MAYA_VERSION}/"

# Update the module file path to point to the actual install location
sudo sed -i "s|+ VRayForMaya${MAYA_VERSION}rhel8 0.9 ../../maya_vray|+ VRayForMaya${MAYA_VERSION}rhel8 0.9 ${VRAY_ROOT}/maya_vray|" \
    "/usr/autodesk/modules/maya/${MAYA_VERSION}/VRayForMaya.module"

# Set the V-Ray EULA environment variable
export VRAY_EULA="https://docs.chaos.com/display/VNS/End+User+License+Agreement"

# Verify
mayapy -c 'import maya.standalone; maya.standalone.initialize(); import maya.cmds; maya.cmds.loadPlugin("vrayformaya"); print("V-Ray OK"); maya.standalone.uninitialize()'
```

### Installing V-Ray — Windows / macOS

Download and run the V-Ray for Maya installer from the [Chaos website](https://www.chaos.com/vray/maya). It provides a standard GUI installer.

### Installing Redshift — Linux

Source: [`maya-redshift-2025/recipe/build.sh`](https://github.com/aws-deadline/deadline-cloud-samples/blob/mainline/conda_recipes/maya-redshift-2025/recipe/build.sh)

```bash
MAYA_VERSION=2025
REDSHIFT_VERSION="2025.4.2"
REDSHIFT_ROOT="/usr/maxon/redshift_${REDSHIFT_VERSION}"

# Extract the Redshift self-extracting installer
chmod u+x redshift_${REDSHIFT_VERSION}*_linux_x64.run
mkdir -p /tmp/redshift_unpack
./redshift_${REDSHIFT_VERSION}*_linux_x64.run --target /tmp/redshift_unpack --noexec

# Skip the superuser check and run setup
cd /tmp/redshift_unpack
sed -i 's/\[ "$(id -u)" != "0" \]/false/' setup.sh
sudo ./setup.sh --installpath "${REDSHIFT_ROOT}"

# Remove unneeded DCC plugins (keep only Maya)
sudo rm -rf "${REDSHIFT_ROOT}/redshift4blender" "${REDSHIFT_ROOT}/redshift4c4d" \
    "${REDSHIFT_ROOT}/redshift4houdini" "${REDSHIFT_ROOT}/redshift4katana" \
    "${REDSHIFT_ROOT}/redshift4solaris"

# Create the redshift4maya.mod file
sudo mkdir -p "/usr/autodesk/modules/maya/${MAYA_VERSION}"
sudo tee "/usr/autodesk/modules/maya/${MAYA_VERSION}/redshift4maya.mod" > /dev/null <<EOF
+ redshift4maya any ${REDSHIFT_ROOT}/redshift4maya
scripts: common/scripts
icons: common/icons
plug-ins: ${MAYA_VERSION}
REDSHIFT_COREDATAPATH = ${REDSHIFT_ROOT}
MAYA_CUSTOM_TEMPLATE_PATH +:= common/scripts/NETemplates
MAYA_RENDER_DESC_PATH +:= common/rendererDesc
REDSHIFT_MAYAEXTENSIONSPATH +:= ${MAYA_VERSION}/extensions
REDSHIFT_PROCEDURALSPATH += "\$REDSHIFT_COREDATAPATH/procedurals/usd/USD_24.08"
REDSHIFT_PROCEDURALSPATH += "\$REDSHIFT_COREDATAPATH/procedurals/alembic"
EOF

# Verify
mayapy -c 'import maya.standalone; maya.standalone.initialize(); import maya.cmds; maya.cmds.loadPlugin("redshift4maya"); print("Redshift OK"); maya.standalone.uninitialize()'
```

### Installing Redshift — Windows / macOS

Download and run the Redshift installer from the [Maxon website](https://www.maxon.net/en/redshift). It provides a standard GUI installer.

### Environment Variables After Installation

Set these in your shell profile after installing Maya and renderers:

```bash
# Linux
export MAYA_VERSION=2025
export MAYA_LOCATION="/usr/autodesk/maya${MAYA_VERSION}"
export PATH="${MAYA_LOCATION}/bin:$PATH"
export MAYA_MODULE_PATH="/usr/autodesk/maya${MAYA_VERSION}/modules:/usr/autodesk/modules/maya/${MAYA_VERSION}:/usr/autodesk/modules/maya"
```

```bash
# macOS
export MAYA_VERSION=2025
export MAYA_LOCATION="/Applications/Autodesk/maya${MAYA_VERSION}"
export PATH="${MAYA_LOCATION}/Maya.app/Contents/MacOS:$PATH"
```

```powershell
# Windows
$env:MAYA_VERSION = "2025"
$env:MAYA_LOCATION = "C:\Program Files\Autodesk\Maya2025"
$env:PATH = "$env:MAYA_LOCATION\bin;$env:PATH"
$env:MAYA_MODULE_PATH = "C:\Program Files\Autodesk\Maya2025\modules;C:\Program Files\Autodesk\modules\maya\2025;C:\Program Files\Autodesk\modules\maya"
```

### Verifying the Full Stack

```bash
# Maya
mayapy -c 'import maya.standalone; maya.standalone.initialize(); print("Maya OK"); maya.standalone.uninitialize()'

# Arnold
mayapy -c 'import maya.standalone; maya.standalone.initialize(); import mtoa; print("Arnold OK"); maya.standalone.uninitialize()'

# V-Ray
mayapy -c 'import maya.standalone; maya.standalone.initialize(); import maya.cmds; maya.cmds.loadPlugin("vrayformaya"); print("V-Ray OK"); maya.standalone.uninitialize()'

# Redshift
mayapy -c 'import maya.standalone; maya.standalone.initialize(); import maya.cmds; maya.cmds.loadPlugin("redshift4maya"); print("Redshift OK"); maya.standalone.uninitialize()'

# Maya batch render
maya -batch -command 'print "Hello from Maya"; quit -exitCode 0 -force'
```

## Usage

The power will prompt you for:
- **Maya Version** (e.g., 2024, 2025, 2026)
- **Maya Installation Path** (if not in standard location)
- **Renderers to install** (Arnold, V-Ray, Redshift)
- **S3 bucket or local path** for installer archives

If Maya is already installed, the power skips to step 4 (Hatch Installation).

## What Gets Installed

### System Python Packages
- `hatch` - Build tool and environment manager

### Maya Python Packages (via mayapy -m pip)
- `deadline-cloud-for-maya` - The package itself (editable install)
- `deadline` - AWS Deadline Cloud client library
- `openjd-adaptor-runtime` - OpenJD adaptor runtime
- `openjd-cli` - OpenJD command-line interface
- `pytest` - Test framework
- `pytest-cov` - Coverage plugin for pytest
- `pytest-xdist` - Parallel test execution
- `coverage` - Code coverage measurement
- All required dependencies from requirements-testing.txt and requirements-integ-testing.txt

### Environment Variables
- `MAYAPY_EXECUTABLE` - Points to mayapy executable
- `PATH` - Adds Maya bin directory
- `MAYA_MODULE_PATH` - Module search paths for renderer plugins
- `MAYA_ENV_DIR` - Points to plugin_env/ (set automatically by hatch shell)
- `DEADLINE_ENABLE_DEVELOPER_OPTIONS` - Enables developer features in submitter

## Platform-Specific Paths

### macOS
- Maya: `/Applications/Autodesk/maya{version}/Maya.app/Contents/MacOS/`
- mayapy: `/Applications/Autodesk/maya{version}/Maya.app/Contents/MacOS/mayapy`
- Maya Python bin: `/Applications/Autodesk/maya{version}/Maya.app/Contents/Frameworks/Python.framework/Versions/Current/bin/`
- Maya prefs: `~/Library/Preferences/Autodesk/maya/{version}/`

### Linux
- Maya: `/usr/autodesk/maya{version}/bin/`
- mayapy: `/usr/autodesk/maya{version}/bin/mayapy`
- Module paths: `/usr/autodesk/maya{version}/modules`, `/usr/autodesk/modules/maya/{version}`
- Maya prefs: `~/maya/{version}/`

### Windows
- Maya: `C:\Program Files\Autodesk\Maya{version}\bin\`
- mayapy: `C:\Program Files\Autodesk\Maya{version}\bin\mayapy.exe`
- Module paths: `C:\Program Files\Autodesk\Maya{version}\modules`, `C:\Program Files\Autodesk\modules\maya\{version}`
- Maya prefs: `%USERPROFILE%\Documents\maya\{version}\`

## After Setup

Once setup is complete, you can:

### Run Unit Tests
```bash
hatch run test
```

### Run Integration Tests
```bash
hatch run integ:test
```

### Build Package
```bash
hatch build
```

### Format and Lint Code
```bash
hatch run fmt
hatch run lint
```

### Run Maya with Dev Submitter
```bash
hatch shell
export DEADLINE_ENABLE_DEVELOPER_OPTIONS=true
maya
```

### Run Job Bundle Output Tests
1. Launch Maya with developer options enabled
2. Click `TEST` on the AWSDeadline shelf
3. Select `job_bundle_output_tests/` directory

## Troubleshooting

### Hatch Not Found
If hatch is not found after installation, restart your terminal or add to PATH:
```bash
# Linux/macOS
export PATH="$HOME/.local/bin:$PATH"

# Windows (PowerShell)
$env:PATH = "$env:USERPROFILE\AppData\Roaming\Python\Python311\Scripts;$env:PATH"
```

### Maya Python Issues
Verify the correct mayapy is being used:
```bash
# macOS
/Applications/Autodesk/maya2025/Maya.app/Contents/MacOS/mayapy --version

# Linux
/usr/autodesk/maya2025/bin/mayapy --version

# Windows
& "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" --version
```

### Plugin Not Appearing
1. Ensure `hatch run install` completed successfully
2. Launch Maya from within `hatch shell`
3. Check Plug-in Manager: Windows > Settings/Preferences > Plug-in Manager
4. Search for "DeadlineCloudForMaya"

### Integration Tests Failing
Check Maya logs and ensure mayapy is on PATH:
```bash
# macOS
export PATH="/Applications/Autodesk/maya2025/Maya.app/Contents/MacOS:$PATH"
which mayapy

# Linux
export PATH="/usr/autodesk/maya2025/bin:$PATH"
which mayapy
```

```powershell
# Windows
$env:PATH = "C:\Program Files\Autodesk\Maya2025\bin;$env:PATH"
Get-Command mayapy
```

### Hatch Environment Issues
If hatch environments are corrupted or stale:
```bash
hatch env prune
```

## Notes

- Setup works on Linux, macOS, and Windows
- The `hatch shell` environment automatically sets `MAYA_ENV_DIR` to `plugin_env/`
- The adaptor requires `maya` or `mayapy` to be in PATH or `MAYAPY_EXECUTABLE` set
- Integration tests require `mayapy` on PATH and renderer plugins installed
- Set `DEADLINE_ENABLE_DEVELOPER_OPTIONS=true` to access developer features (TEST button, Include Adaptor Wheels)
- Maya 2024-2026 are supported; plugin support varies by renderer (Arnold 2024-2026, V-Ray/Redshift 2025-2026)
- Windows Maya adaptor requires `pywin32` installed in Maya's Python (`mayapy -m pip install pywin32`)
- V-Ray and Redshift Linux install commands are from the conda recipes; Windows/macOS use GUI installers
- macOS install commands use standard macOS patterns but are not sourced from the conda recipes

## Reference

Installation commands derived from the conda build scripts in [deadline-cloud-samples/conda_recipes](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/conda_recipes):
- [`maya-2025/recipe/build.sh`](https://github.com/aws-deadline/deadline-cloud-samples/blob/mainline/conda_recipes/maya-2025/recipe/build.sh) — Linux Maya RPM extraction and setup
- [`maya-2025/recipe/build_win.sh`](https://github.com/aws-deadline/deadline-cloud-samples/blob/mainline/conda_recipes/maya-2025/recipe/build_win.sh) — Windows Maya setup
- [`maya-mtoa-2025/recipe/build.sh`](https://github.com/aws-deadline/deadline-cloud-samples/blob/mainline/conda_recipes/maya-mtoa-2025/recipe/build.sh) — Arnold module file and CLI symlinks
- [`maya-mtoa-2025/recipe/build_win.sh`](https://github.com/aws-deadline/deadline-cloud-samples/blob/mainline/conda_recipes/maya-mtoa-2025/recipe/build_win.sh) — Windows Arnold module file
- [`maya-vray-2025/recipe/build.sh`](https://github.com/aws-deadline/deadline-cloud-samples/blob/mainline/conda_recipes/maya-vray-2025/recipe/build.sh) — V-Ray extraction and module setup
- [`maya-redshift-2025/recipe/build.sh`](https://github.com/aws-deadline/deadline-cloud-samples/blob/mainline/conda_recipes/maya-redshift-2025/recipe/build.sh) — Redshift extraction and module setup
