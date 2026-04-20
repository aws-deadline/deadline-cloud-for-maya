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

This power automates the complete development environment setup for working on the deadline-cloud-for-maya project. It handles everything from reading documentation to building packages, installing dependencies, and configuring environment variables.

## Setup Steps Performed

1. **Documentation Review** - Reads README.md and DEVELOPMENT.md to understand project requirements
2. **Hatch Installation** - Installs and configures Hatch build tool
3. **Package Build** - Builds wheel and source distributions
4. **Maya Detection** - Verifies Maya installation (2024-2026)
5. **Dev Submitter Installation** - Runs `hatch run install` to create plugin_env/
6. **Dependencies Installation** - Installs deadline, openjd-adaptor-runtime
7. **Wheel Installation** - Installs the built wheel for adaptor
8. **OpenJD CLI Installation** - Installs openjd-cli for running integration tests
9. **Test Packages Installation** - Installs pytest, coverage, and test dependencies into Maya's Python
10. **Environment Configuration** - Sets up MAYAPY_EXECUTABLE, PATH, and MAYA_ENV_DIR

## Prerequisites

- Python 3.9 or higher installed on system
- Maya 2024-2026 installed with a valid license
- Linux, macOS, or Windows operating system

### Developer Licensing

Developer licenses are automatically available on the workstation. Set these environment variables before launching Maya or running tests:

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

## Usage

The power will prompt you for:
- **Maya Version** (e.g., 2024, 2025, 2026)
- **Maya Installation Path** (if not in standard location)

If Maya is not found, the setup will provide instructions for installation.

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
- Maya prefs: `~/maya/{version}/`

### Windows
- Maya: `C:\Program Files\Autodesk\Maya{version}\bin\`
- mayapy: `C:\Program Files\Autodesk\Maya{version}\bin\mayapy.exe`
- Maya prefs: `%USERPROFILE%\Documents\maya\{version}\`

## Output Files

The power creates several reference documents:
- `HATCH_SETUP.md` - Hatch usage guide
- `configure_maya_env.sh` or `.ps1` - Environment configuration script
- `verify_maya_paths.sh` or `.ps1` - Path verification script
- `INSTALLATION_SUMMARY.md` - Complete installation summary
- `OPENJD_SETUP_COMPLETE.md` - OpenJD usage guide

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
