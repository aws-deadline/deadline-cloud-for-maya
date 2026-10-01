---
name: "maya-dev-power"
displayName: "Maya Dev Power"
description: "Development power for deadline-cloud-for-maya - build, lint, test, and run integration tests with Maya, Arnold, V-Ray, and Redshift."
keywords: ["maya", "deadline", "build", "test", "lint", "integration", "arnold", "vray", "redshift", "adaptor"]
author: "AWS Deadline Cloud Team"
---

# Maya Dev Power

Development power for building, testing, and debugging the deadline-cloud-for-maya project.

## Overview

This project is a Python package that provides:
- **Maya Adaptor**: Runs Maya renders on Deadline Cloud workers (`maya-openjd` CLI)
- **Maya Submitter**: Plugin for submitting jobs from Maya to Deadline Cloud

## MCP Tools

This power includes the **Autodesk Product Help MCP** server (`autodesk-product-help`), which provides direct access to Autodesk's official documentation for 110+ products including Maya, Arnold, and MEL.

Use it to:
- Look up Maya Python API (maya.cmds, maya.mel) documentation while developing adaptor or submitter code
- Search for Arnold/V-Ray/Redshift render settings and parameters
- Find official Autodesk troubleshooting guides for Maya issues

The server exposes two tools:
- `get_available_products` - List all supported Autodesk products and their release codes
- `search_help_content` - Search Autodesk documentation by product, release, and query

When searching, use product code `MAYA` for Maya documentation.

## Available Steering Files

- **build-and-test.md** - Complete build and test workflow
- **dev-guide.md** - Development guide and conventions
- **integration-testing.md** - Guide for running and creating integration tests
- **renderer-handlers.md** - Render handler architecture, per-renderer differences, and how to add actions or handlers
- **submitter-guide.md** - Submitter code organization, data classes, UI layout, and how to add settings or renderer-specific features
- **troubleshooting.md** - Common issues and solutions

## Prerequisites

- Python 3.9 or higher
- Maya 2024-2026 installed
- Hatch (Python build tool): `pip install hatch`
- For integration tests: `mayapy` on PATH

## Quick Commands

### Build
```bash
hatch build
```

### Lint & Format
```bash
hatch run fmt      # Format code (black + ruff)
hatch run lint     # Run linter + type checker
hatch run typing   # Type checking only (mypy)
```

### Unit Tests
```bash
hatch run test                              # All tests
hatch run test test/unit/path/to/test.py   # Specific file
hatch run test -k "test_arnold"            # Pattern match
hatch run all:test                         # All Python versions
```

### Install Dev Submitter
```bash
hatch run install    # Creates plugin_env/ with submitter + dependencies
```

### Run Maya with Dev Submitter
```bash
hatch shell
export DEADLINE_ENABLE_DEVELOPER_OPTIONS=true  # Linux/macOS
maya
```

```powershell
# Windows
hatch shell
$env:DEADLINE_ENABLE_DEVELOPER_OPTIONS = "true"
maya
```

### Integration Tests

Add `mayapy` to PATH first:

```bash
# macOS
export PATH="/Applications/Autodesk/maya2025/Maya.app/Contents/MacOS:$PATH"

# Linux
export PATH="/usr/autodesk/maya2025/bin:$PATH"
```

```powershell
# Windows
$env:PATH = "C:\Program Files\Autodesk\Maya2025\bin;$env:PATH"
```

Install dependencies into Maya's Python:
```bash
mayapy -m pip install -e . --force-reinstall
mayapy -m pip install -r requirements-testing.txt
mayapy -m pip install -r requirements-integ-testing.txt
```

Run integration tests:
```bash
hatch run integ:test                    # All integration tests
hatch run integ:test_submitters         # Submitter tests only
hatch run integ:test_adaptors_all       # All adaptor tests
hatch run integ:test_adaptors_maya      # Maya renderer only
hatch run integ:test_adaptors_mtoa      # Arnold (MtoA) only
hatch run integ:test_adaptors_vray      # V-Ray only
hatch run integ:test_adaptors_redshift  # Redshift only
```

### Build Installer
```bash
hatch build
hatch run installer:build-installer --local-dev --platform <PLATFORM>
```

## Test Markers

Integration tests use pytest markers to categorize tests:

| Marker | Description |
|--------|-------------|
| `submitter` | Submitter integration tests |
| `adaptor` | Adaptor integration tests |
| `maya_renderer` | Maya Software renderer tests |
| `mtoa_renderer` | Arnold (MtoA) renderer tests |
| `vray_renderer` | V-Ray renderer tests |
| `redshift_renderer` | Redshift renderer tests |

## Job Bundle Output Tests

In-application tests available via the `TEST` button on the AWSDeadline shelf (requires `DEADLINE_ENABLE_DEVELOPER_OPTIONS=true`):

1. Click `TEST` on the AWSDeadline shelf
2. Select the `job_bundle_output_tests/` directory
3. Results saved to `test-job-bundle-results.txt`

## Checking Logs

```bash
# macOS
tail -n 100 ~/Library/Preferences/Autodesk/maya/*/Maya.log

# Linux
tail -n 100 ~/maya/*/Maya.log
```

```powershell
# Windows
Get-Content "$env:USERPROFILE\Documents\maya\*\Maya.log" -Tail 100
```

## Project Structure

```
src/deadline/
├── maya_adaptor/           # Adaptor (runs on worker)
│   ├── MayaAdaptor/        # Server-side adaptor
│   │   └── schemas/        # JSON schemas for init/run data
│   └── MayaClient/         # Client running inside Maya
│       └── render_handlers/ # Renderer-specific handlers
└── maya_submitter/         # Submitter (runs in Maya)
    └── ui/                 # Qt-based UI components
maya_submitter_plugin/      # Maya plugin files
├── plug-ins/               # DeadlineCloudForMaya.py
└── scripts/                # MEL scripts, shelf
test/
├── unit/                   # Unit tests
└── integ/                  # Integration tests
job_bundle_output_tests/    # In-app bundle validation tests
scripts/                    # Build and utility scripts
```

## Adaptor Usage

After installation, the adaptor is available as a command-line tool:
```bash
maya-openjd --help
maya-openjd run --init-data file://init-data.yaml --run-data file://run-data.yaml
maya-openjd daemon start --init-data file://init-data.yaml --connection-file file://conn.json
maya-openjd daemon run --run-data file://run-data.yaml --connection-file file://conn.json
maya-openjd daemon stop --connection-file file://conn.json
```

Set `MAYAPY_EXECUTABLE` environment variable to specify Maya's Python location if not in PATH.

## Building Adaptor Wheels for Farm Testing

For testing adaptor changes on a live Deadline Cloud farm:

```bash
# Build wheels for all dependencies
./scripts/build_wheels.sh

# Wheels are created in wheels/ directory
ls ./wheels
# deadline_cloud_for_maya-*.whl
# deadline-*.whl
# openjd_adaptor_runtime-*.whl
```

Then in Maya submitter (with `DEADLINE_ENABLE_DEVELOPER_OPTIONS=true`):
1. Enable "Include Adaptor Wheels" in Job-Specific Settings
2. Submit the job - worker will use your modified adaptor
