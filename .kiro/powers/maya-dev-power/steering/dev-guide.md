# Dev Guide

## Python Environment

**IMPORTANT**: Use `mayapy` for running integration tests and adaptor code. System Python is used for unit tests via hatch.

### Maya Python Locations

| Platform | Maya 2025 mayapy Path |
|----------|----------------------|
| macOS | `/Applications/Autodesk/maya2025/Maya.app/Contents/MacOS/mayapy` |
| Linux | `/usr/autodesk/maya2025/bin/mayapy` |
| Windows | `C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe` |

For Maya 2024 or 2026, replace `2025` with the appropriate version.

## Build & Install Workflow

### Build

```bash
hatch build
```

This creates wheel and sdist in `dist/`.

### Install Dev Submitter

```bash
hatch run install
```

Creates `plugin_env/` with the submitter plugin and all dependencies. Launch Maya from `hatch shell` to use it.

### Code Quality

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

## Submitter Development

### Workflow

1. `hatch run install` - Build and install plugin
2. `hatch shell` - Enter dev environment
3. `export DEADLINE_ENABLE_DEVELOPER_OPTIONS=true`
4. `maya` - Launch Maya
5. Load plugin in Plug-in Manager
6. Make code changes
7. `hatch run install` - Reinstall
8. Uncheck/recheck plugin in Plug-in Manager

### Key Files

| File | Purpose |
|------|---------|
| `maya_submitter_plugin/plug-ins/DeadlineCloudForMaya.py` | Plugin entry point |
| `src/deadline/maya_submitter/maya_render_submitter.py` | Main submission logic |
| `src/deadline/maya_submitter/render_layers.py` | Render layer handling |
| `src/deadline/maya_submitter/ui/` | Qt-based UI components |

## Adaptor Development

### Running Locally

```bash
hatch shell

# Direct run mode
maya-openjd run \
  --init-data file:///path/to/init-data.yaml \
  --run-data file:///path/to/run-data.yaml

# Daemon mode (sticky rendering)
maya-openjd daemon start \
  --init-data file:///path/to/init-data.yaml \
  --connection-file file://connection-info.json

maya-openjd daemon run \
  --run-data file:///path/to/run-data.yaml \
  --connection-file file://connection-info.json

maya-openjd daemon stop \
  --connection-file file://connection-info.json
```

### Key Files

| File | Purpose |
|------|---------|
| `src/deadline/maya_adaptor/MayaAdaptor/adaptor.py` | Main adaptor class |
| `src/deadline/maya_adaptor/MayaAdaptor/schemas/` | JSON schemas |
| `src/deadline/maya_adaptor/MayaClient/maya_client.py` | Client running in Maya |
| `src/deadline/maya_adaptor/MayaClient/render_handlers/` | Renderer-specific handlers |

### Schema Versioning

When modifying `init_data.schema.json` or `run_data.schema.json`, update `integration_data_interface_version` in `adaptor.py` following semver.

## Integration Tests

See **integration-testing.md** for full details.

```bash
# Prerequisites: mayapy on PATH + dependencies installed
mayapy -m pip install -e . --force-reinstall
mayapy -m pip install -r requirements-testing.txt
mayapy -m pip install -r requirements-integ-testing.txt

# Run tests
hatch run integ:test                    # All
hatch run integ:test_submitters         # Submitter only
hatch run integ:test_adaptors_all       # All adaptors
hatch run integ:test_adaptors_maya      # Maya renderer
hatch run integ:test_adaptors_mtoa      # Arnold
hatch run integ:test_adaptors_vray      # V-Ray
hatch run integ:test_adaptors_redshift  # Redshift
```

## Creating Test Bundles

```
job_bundle_output_tests/my_test/
├── expected_job_bundle/
│   ├── template.yaml
│   ├── parameter_values.yaml
│   └── asset_references.yaml
└── scene.ma (or scene.mb)
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| No wheel found | `hatch build` |
| Hatch not found | `pip install hatch` |
| Import errors | `pip install -r requirements-testing.txt` |
| Plugin not loading | `hatch run install` then relaunch Maya from `hatch shell` |
| mayapy not found | Add Maya bin directory to PATH |
| Hatch env broken | `hatch env prune` |

**Logs:**

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
