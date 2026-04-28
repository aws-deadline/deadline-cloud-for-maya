# Build and Test Workflow

Complete build and test workflow for deadline-cloud-for-maya.

## Step 1: Build the Wheel

Always build a fresh wheel before testing:

```bash
hatch build
```

This creates a wheel in `dist/deadline_cloud_for_maya-*.whl`

## Step 2: Run Linting and Formatting

Before committing, ensure code passes all checks:

```bash
# Format code (black + ruff)
hatch run fmt

# Run linter and type checker
hatch run lint

# Run type checker only (mypy)
hatch run typing
```

## Step 3: Run Unit Tests

Run the full unit test suite:

```bash
hatch run test
```

For faster iteration, run specific tests:

```bash
# Run tests for a specific module
hatch run test test/unit/deadline/maya_adaptor/

# Run a single test file
hatch run test test/unit/deadline/maya_adaptor/MayaClient/test_maya_client.py

# Run tests matching a pattern
hatch run test -k "test_arnold"

# Run against all supported Python versions
hatch run all:test
```

## Step 4: Install Dev Submitter

Create a development installation of the submitter plugin:

```bash
hatch run install
```

This creates a `plugin_env/` directory with the submitter plugin and all dependencies.

## Step 5: Run Maya with Dev Submitter

```bash
# Enter hatch shell (sets MAYA_ENV_DIR to plugin_env/)
hatch shell

# Enable developer options
export DEADLINE_ENABLE_DEVELOPER_OPTIONS=true  # Linux/macOS

# Launch Maya
maya
```

```powershell
# Windows
hatch shell
$env:DEADLINE_ENABLE_DEVELOPER_OPTIONS = "true"
maya
```

Load the plugin: Windows > Settings/Preferences > Plug-in Manager > Enable `DeadlineCloudForMaya.py`

**After code changes:** Re-run `hatch run install`, then uncheck/recheck the plugin in Plug-in Manager.

## Step 6: Run Integration Tests

Integration tests require Maya installed. See `integration-testing.md` for full setup.

### Prerequisites

Add `mayapy` to PATH:

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

### Run Tests

```bash
hatch run integ:test                    # All integration tests
hatch run integ:test_submitters         # Submitter tests only
hatch run integ:test_adaptors_all       # All adaptor tests
hatch run integ:test_adaptors_maya      # Maya renderer only
hatch run integ:test_adaptors_mtoa      # Arnold (MtoA) only
hatch run integ:test_adaptors_vray      # V-Ray only
hatch run integ:test_adaptors_redshift  # Redshift only
```

## Step 7: Run Job Bundle Output Tests

In-application tests that validate generated job bundles:

1. Launch Maya with `DEADLINE_ENABLE_DEVELOPER_OPTIONS=true`
2. Click `TEST` on the AWSDeadline shelf
3. Select the `job_bundle_output_tests/` directory
4. Results saved to `test-job-bundle-results.txt`

## Step 8: Build Adaptor Wheels (Developer Option)

For testing adaptor changes on a live Deadline Cloud farm:

### Prerequisites

Clone sibling repositories:
```bash
cd ~/workspace/maya
git clone https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python.git
git clone https://github.com/aws-deadline/deadline-cloud.git
```

### Build Wheels

```bash
# Build wheels for all dependencies
./scripts/build_wheels.sh

# Wheels are created in wheels/ directory
ls ./wheels
# deadline_cloud_for_maya-*.whl
# deadline-*.whl
# openjd_adaptor_runtime-*.whl
```

### Testing on Farm

1. Launch Maya with `DEADLINE_ENABLE_DEVELOPER_OPTIONS=true`
2. Open the submitter
3. In Job-Specific Settings, enable "Include Adaptor Wheels"
4. Submit the job

**Note:** Copy `wheels/` to `plugin_env/wheels/` after each `hatch run install`.

## Step 9: Build Installer

```bash
hatch build
hatch run installer:build-installer --local-dev --platform <PLATFORM>
```

Test the installer:
```bash
hatch run test-installer
```

## Step 10: Check Logs

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

For adaptor logs during integration tests, check the test output directory.

## Common Issues

### Wrong Python Version
Ensure mayapy is being used for integration tests:
```bash
mayapy --version
# Should show Python 3.10.x or 3.11.x depending on Maya version
```

### Wheel Not Found
Build the wheel first: `hatch build`

### Maya Not Found
Add Maya to PATH or set `MAYAPY_EXECUTABLE` environment variable

### Plugin Not Loading
1. Run `hatch run install` to create/update plugin_env/
2. Launch Maya from within `hatch shell`
3. Reload plugin in Plug-in Manager

### Hatch Environment Issues
```bash
hatch env prune  # Delete all hatch environments and start fresh
```
