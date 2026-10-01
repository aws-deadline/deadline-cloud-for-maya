# Integration Testing Guide

How to run integration tests for the Maya adaptor and submitter.

## Prerequisites

1. Maya 2024, 2025, or 2026 installed **with a valid license**
2. `mayapy` on PATH
3. Renderer plugins installed (Arnold/MtoA, V-Ray, Redshift) for renderer-specific tests
4. Test dependencies installed into Maya's Python

### Developer Licensing

Developer licenses are automatically available on the workstation. Set these environment variables before running tests:

```bash
# Linux/macOS
export ADSKFLEX_LICENSE_FILE=27002@localhost        # Autodesk (Maya)
export FLEXLM_TIMEOUT=3000000                       # Avoid timeout errors
export redshift_LICENSE=5054@localhost               # Redshift (case sensitive!)
export PIXAR_LICENSE_FILE=9010@localhost             # RenderMan (if needed)
```

```powershell
# Windows
$env:ADSKFLEX_LICENSE_FILE = "27002@localhost"
$env:FLEXLM_TIMEOUT = "3000000"
$env:redshift_LICENSE = "5054@localhost"
$env:PIXAR_LICENSE_FILE = "9010@localhost"
```

| Vendor | Product | Port | Env Var |
|--------|---------|------|---------|
| Autodesk | Maya | 27002 | `ADSKFLEX_LICENSE_FILE` |
| ChaosGroup | V-Ray | 30304 | OLS (GUI config) |
| Maxon/Redshift | Redshift | 5054 | `redshift_LICENSE` |
| Pixar | RenderMan | 9010 | `PIXAR_LICENSE_FILE` |

**Note:** Arnold (MtoA) is included with the Maya license. The adaptor tests set `ArnoldErrorOnLicenseFailure=false` so Arnold renders with a watermark if unlicensed — tests still pass.

See the full port list at the [License Ports wiki](https://w.amazon.com/bin/view/EC2/Thinkbox/ServicesTeam/Projects/DeveloperLicencing/LicensePorts).

## Setup

### Add mayapy to PATH

```bash
# macOS (Maya 2025)
export PATH="/Applications/Autodesk/maya2025/Maya.app/Contents/MacOS:$PATH"

# Linux (Maya 2025)
export PATH="/usr/autodesk/maya2025/bin:$PATH"
```

```powershell
# Windows (Maya 2025)
$env:PATH = "C:\Program Files\Autodesk\Maya2025\bin;$env:PATH"
```

### Add Maya Python's bin to PATH (for adaptor tests)

```bash
# macOS (Maya 2025)
export PATH="/Applications/Autodesk/maya2025/Maya.app/Contents/Frameworks/Python.framework/Versions/Current/bin/:$PATH"

# Linux (Maya 2025)
export PATH="/usr/autodesk/maya2025/lib/python-3.10/bin:$PATH"
```

### Install Dependencies

```bash
# Install the package into Maya's Python
mayapy -m pip install -e . --force-reinstall

# Install test dependencies
mayapy -m pip install -r requirements-testing.txt
mayapy -m pip install -r requirements-integ-testing.txt
```

## Running Tests (hatch — primary method)

### Run all integration tests
```bash
hatch run integ:test
```

### Run submitter tests only
```bash
hatch run integ:test_submitters
```

### Run all adaptor tests
```bash
hatch run integ:test_adaptors_all
```

### Run renderer-specific adaptor tests
```bash
hatch run integ:test_adaptors_maya       # Maya Software renderer
hatch run integ:test_adaptors_mtoa       # Arnold (MtoA)
hatch run integ:test_adaptors_vray       # V-Ray
hatch run integ:test_adaptors_redshift   # Redshift
```

## Running Tests (mayapy directly)

For more control or debugging:

```bash
# All integration tests
mayapy -m pytest --no-cov test/integ -vvv --numprocesses=1

# Submitter tests only
mayapy -m pytest --no-cov test/integ -vvv --numprocesses=1 -m submitter

# Adaptor tests only
mayapy -m pytest --no-cov test/integ -vvv --numprocesses=1 -m adaptor

# Specific renderer
mayapy -m pytest --no-cov test/integ -vvv --numprocesses=1 -m "adaptor and mtoa_renderer"

# Specific test
mayapy -m pytest --no-cov test/integ/test_maya_adaptors.py::TestAdaptors::test_minimal_scene_adaptor -vvv
```

## How Adaptor Integration Tests Work

Adaptor tests use `openjd run` to execute a full render through the Maya adaptor. The flow is:

1. **pytest** calls `run_adaptor_test()` in `test/integ/helpers/test_runners.py`
2. `run_adaptor_test()` reads the job template YAML and for each step runs:
   ```bash
   mayapy -m openjd run <template.yaml> --step <step_name> --job-param <json_params>
   ```
3. This launches a full **OpenJD session** which starts the Maya adaptor (`maya-openjd`), loads the scene file, configures render settings, and **renders the frame(s)**
4. After rendering, the test compares output images against expected images using `are_images_similar()` with a pixel tolerance

### Example: What happens during `test_minimal_scene_adaptor`

```python
job_params = {
    "MayaSceneFile": str(scene_location),
    "OutputFilePrefix": "rs_<RenderLayer>_<Camera>",
    "Frames": "1-2",
    "ImageWidth": 960,
    "ImageHeight": 540,
    "OutputFilePath": str(output_path),
    "ProjectPath": str(test_file_location / "scene") + "/",
    "RenderSetupIncludeLights": "false",
}
# Runs: mayapy -m openjd run template.yaml --step Render --job-param '{...}'
run_adaptor_test(template_path, job_params)
# Then compares rendered images to expected output
are_images_similar(expected_dir, actual_dir, tolerance=2)
```

### Manual openjd run (for debugging)

You can run the same command manually to debug a specific test bundle:

```bash
mayapy -m openjd run \
  test/integ/test_scripts/minimal_test/expected_job_bundle/template.yaml \
  --step Render \
  --job-param '{"MayaSceneFile": "/path/to/test.ma", "Frames": "1", "ImageWidth": 960, "ImageHeight": 540, "OutputFilePath": "/tmp/output/", "ProjectPath": "/path/to/scene/", "OutputFilePrefix": "test", "RenderSetupIncludeLights": "false"}'
```

You can also validate a template without rendering:

```bash
mayapy -m openjd check test/integ/test_scripts/minimal_test/expected_job_bundle/template.yaml --output json
```

## Test Structure

```
test/integ/
├── test_maya_submitters.py    # Submitter integration tests
├── test_maya_adaptors.py      # Adaptor integration tests (uses openjd run)
├── helpers/
│   ├── test_runners.py        # run_adaptor_test() - calls mayapy -m openjd run
│   └── output_comparison.py   # are_images_similar() - pixel comparison
└── conftest.py                # Pytest fixtures
```

### Test Markers

| Marker | Description |
|--------|-------------|
| `submitter` | Submitter integration tests |
| `adaptor` | Adaptor integration tests (renders frames via openjd run) |
| `maya_renderer` | Maya Software renderer |
| `mtoa_renderer` | Arnold (MtoA) renderer |
| `vray_renderer` | V-Ray renderer |
| `redshift_renderer` | Redshift renderer |

## Job Bundle Output Tests (In-Application)

These tests run inside Maya and validate that the submitter generates correct job bundles:

1. Launch Maya with `DEADLINE_ENABLE_DEVELOPER_OPTIONS=true`:
   ```bash
   hatch shell
   export DEADLINE_ENABLE_DEVELOPER_OPTIONS=true
   maya
   ```
2. Load the DeadlineCloudForMaya plugin
3. Click `TEST` on the AWSDeadline shelf
4. Select the `job_bundle_output_tests/` directory
5. Results are saved to `test-job-bundle-results.txt`

### Job Bundle Output Test Structure

```
job_bundle_output_tests/
├── test_name/
│   ├── expected_job_bundle/
│   │   ├── template.yaml
│   │   ├── parameter_values.yaml
│   │   └── asset_references.yaml
│   └── scene.ma (or scene.mb)
```

## Testing the Adaptor Locally

### Direct Run Mode

Create `init-data.yaml` and `run-data.yaml` files based on the schemas in `src/deadline/maya_adaptor/MayaAdaptor/schemas/`.

```bash
hatch shell

maya-openjd run \
  --init-data file:///path/to/init-data.yaml \
  --run-data file:///path/to/run-data.yaml
```

### Daemon Mode (Sticky Rendering)

```bash
hatch shell

# Start daemon
maya-openjd daemon start \
  --init-data file:///path/to/init-data.yaml \
  --connection-file file://connection-info.json

# Run task (repeat with different run-data for multiple frames)
maya-openjd daemon run \
  --run-data file:///path/to/run-data.yaml \
  --connection-file file://connection-info.json

# Stop daemon
maya-openjd daemon stop \
  --connection-file file://connection-info.json
```

## Testing on a Live Farm

Build adaptor wheels and submit with developer options:

```bash
# Build wheels
./scripts/build_wheels.sh

# Copy to plugin_env (after hatch run install)
cp wheels/* plugin_env/wheels/
```

Then in Maya:
1. Enable `DEADLINE_ENABLE_DEVELOPER_OPTIONS=true`
2. Open submitter
3. Enable "Include Adaptor Wheels" in Job-Specific Settings
4. Submit job

## Debugging Integration Tests

### Enable Verbose Output

```bash
mayapy -m pytest --no-cov test/integ -vvv -s --numprocesses=1
```

### Check Maya Output

Integration tests capture Maya's stdout/stderr. Check test output for errors.

### Inspect Test Output

Use `--basetemp` to specify output location:

```bash
mayapy -m pytest --no-cov test/integ --basetemp=/tmp/maya-test-output -vvv --numprocesses=1
```

## Common Issues

### mayapy Not Found
Add Maya's bin directory to PATH. See Setup section above.

### Renderer Plugin Not Loaded
Ensure the renderer plugin (MtoA, V-Ray, Redshift) is installed and licensed for the Maya version.

### Scene File Not Found
Ensure scene files are in the correct location relative to the test bundle.

### Permission Errors on macOS
Maya on macOS may need additional permissions. Run from terminal rather than Finder.

### Python Version Mismatch
Maya 2024 uses Python 3.10, Maya 2025-2026 uses Python 3.10/3.11. Ensure dependencies are compatible.
