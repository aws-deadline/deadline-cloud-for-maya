# Troubleshooting Guide

Common issues and solutions when developing deadline-cloud-for-maya.

## Build Issues

### Hatch Not Found

**Symptom**: `hatch: command not found`

**Solution**:
```bash
# Install hatch
pip install hatch

# Add to PATH (Linux/macOS)
export PATH="$HOME/.local/bin:$PATH"

# Add to PATH (Windows PowerShell)
$env:PATH = "$env:USERPROFILE\AppData\Roaming\Python\Python311\Scripts;$env:PATH"
```

### Build Fails with Missing Dependencies

**Symptom**: Build fails with import errors

**Solution**:
```bash
# Install development dependencies
pip install --upgrade -r requirements-testing.txt

# Rebuild
hatch build
```

### Version File Not Generated

**Symptom**: `_version.py` not found

**Solution**:
```bash
# Ensure hatch-vcs is installed
pip install hatch-vcs

# Clean and rebuild
rm -rf dist/ build/
hatch build
```

### Hatch Environment Corrupted

**Symptom**: Unexpected import errors or stale code in hatch environments

**Solution**:
```bash
# Delete all hatch environments and start fresh
hatch env prune
```

## Submitter Plugin Issues

### Plugin Not Appearing in Maya

**Symptom**: `DeadlineCloudForMaya.py` not visible in Plug-in Manager

**Solution**:
1. Ensure you ran `hatch run install` to create `plugin_env/`
2. Launch Maya from within `hatch shell` (sets `MAYA_ENV_DIR`)
3. Check Plug-in Manager: Windows > Settings/Preferences > Plug-in Manager
4. Search for "DeadlineCloudForMaya"

### Plugin Fails to Load

**Symptom**: Error when enabling plugin in Maya

**Solution**:
1. Check Maya's Script Editor for errors (Windows > General Editors > Script Editor)
2. Verify `plugin_env/` exists and contains the plugin:
   ```bash
   ls plugin_env/
   ```
3. Re-run `hatch run install`
4. Restart Maya from `hatch shell`

### Code Changes Not Taking Effect

**Symptom**: Modified code doesn't appear in Maya

**Solution**:
1. Re-run `hatch run install` to repackage changes
2. In Maya's Plug-in Manager, uncheck then recheck `DeadlineCloudForMaya.py`
3. If still not working, restart Maya

### Import Errors in Plugin

**Symptom**: `ModuleNotFoundError` when using plugin

**Solution**:
1. Verify `plugin_env/` contains all dependencies
2. Re-run `hatch run install`
3. Ensure Maya is launched from `hatch shell`

## Adaptor Issues

### Maya Executable Not Found

**Symptom**: `maya: command not found` or `MAYAPY_EXECUTABLE not set`

**Solution**:
```bash
# Add Maya to PATH
# macOS
export PATH="/Applications/Autodesk/maya2025/Maya.app/Contents/MacOS:$PATH"

# Linux
export PATH="/usr/autodesk/maya2025/bin:$PATH"

# Or set MAYAPY_EXECUTABLE
export MAYAPY_EXECUTABLE=/path/to/mayapy
```

```powershell
# Windows
$env:PATH = "C:\Program Files\Autodesk\Maya2025\bin;$env:PATH"
# Or
$env:MAYAPY_EXECUTABLE = "C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe"
```

### Adaptor Fails to Start

**Symptom**: `maya-openjd daemon start` fails

**Solution**:
1. Check Maya can run in batch mode:
   ```bash
   mayapy -c "import maya.standalone; maya.standalone.initialize(); print('OK')"
   ```
2. Verify adaptor is installed:
   ```bash
   pip show deadline-cloud-for-maya
   ```
3. Check for port conflicts (adaptor uses socket communication)

### Render Fails with Scene File Error

**Symptom**: Cannot load scene file

**Solution**:
1. Verify scene file path is absolute or properly resolved
2. Check file permissions
3. Ensure scene file is compatible with Maya version
4. Test loading scene manually:
   ```bash
   mayapy -c "import maya.standalone; maya.standalone.initialize(); import maya.cmds as cmds; cmds.file('/path/to/scene.ma', open=True, force=True); print('OK')"
   ```

### Maya Ignores Version Check

**Symptom**: Scene opens but with version warnings

**Solution**:
The adaptor sets `MAYA_IGNORE_VERSION=true` by default. To enable version checking:
```bash
export MAYA_IGNORE_VERSION=false
```

## Integration Test Issues

### Tests Fail to Find mayapy

**Symptom**: Integration tests fail with "mayapy not found"

**Solution**:
```bash
# Add mayapy to PATH before running tests
# macOS
export PATH="/Applications/Autodesk/maya2025/Maya.app/Contents/MacOS:$PATH"

# Verify
which mayapy
mayapy --version
```

### Renderer Plugin Not Available

**Symptom**: Renderer-specific tests skip or fail

**Solution**:
1. Verify the renderer plugin is installed for your Maya version
2. Check plugin loads in Maya:
   ```bash
   mayapy -c "import maya.standalone; maya.standalone.initialize(); import maya.cmds as cmds; cmds.loadPlugin('mtoa'); print('Arnold loaded')"
   ```

### Test Dependencies Missing

**Symptom**: `ModuleNotFoundError` during tests

**Solution**:
```bash
mayapy -m pip install -e . --force-reinstall
mayapy -m pip install -r requirements-testing.txt
mayapy -m pip install -r requirements-integ-testing.txt
```

### macOS Permission Issues

**Symptom**: Tests fail with permission errors on macOS

**Solution**:
1. Run Maya/mayapy from terminal (not Finder)
2. Grant terminal Full Disk Access in System Preferences > Privacy & Security
3. Check Maya license is valid

## Linting and Type Checking Issues

### Ruff/Black Formatting Errors

**Symptom**: `hatch run lint` fails with formatting issues

**Solution**:
```bash
# Auto-fix formatting
hatch run fmt

# Check specific files
hatch run style src/deadline/maya_adaptor/
```

### Mypy Type Errors

**Symptom**: `hatch run typing` fails

**Solution**:
1. Check mypy configuration in `pyproject.toml`
2. Maya stubs may not be available - `ignore_missing_imports = true` is set
3. Use `# type: ignore` for unavoidable errors (sparingly)

## Performance Issues

### Slow Integration Tests

**Solution**:
1. Run specific tests instead of full suite:
   ```bash
   hatch run integ:test_adaptors_maya  # Just Maya renderer
   ```
2. Tests run with `--numprocesses=1` by default (Maya is not thread-safe)

### Slow Maya Startup

**Solution**:
1. Use daemon mode (sticky rendering) - keeps Maya open between tasks
2. Reduce scene complexity for tests
3. Use lower sample counts for test renders

## Debugging Tips

### Enable Debug Logging

```bash
export OPENJD_LOG_LEVEL=DEBUG
maya-openjd daemon start ...
```

### Check Maya Script Editor

In Maya: Windows > General Editors > Script Editor
- Shows Python/MEL errors and warnings
- Toggle "Echo All Commands" for verbose output

### Inspect Scene from Command Line

```bash
mayapy -c "
import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
cmds.file('/path/to/scene.ma', open=True, force=True)
print(f'Renderer: {cmds.getAttr(\"defaultRenderGlobals.currentRenderer\")}')
print(f'Frame range: {cmds.getAttr(\"defaultRenderGlobals.startFrame\")}-{cmds.getAttr(\"defaultRenderGlobals.endFrame\")}')
print(f'Resolution: {cmds.getAttr(\"defaultResolution.width\")}x{cmds.getAttr(\"defaultResolution.height\")}')
cameras = cmds.ls(type='camera')
print(f'Cameras: {cameras}')
"
```

## Getting Help

If you're still stuck:

1. Check the [GitHub Issues](https://github.com/aws-deadline/deadline-cloud-for-maya/issues)
2. Review the [Maya Python Command Reference](https://help.autodesk.com/view/MAYAUL/2026/ENU/?guid=__CommandsPython_index_html)
3. Check [OpenJD documentation](https://github.com/OpenJobDescription/openjd-specifications/wiki)
4. Review [AWS Deadline Cloud documentation](https://docs.aws.amazon.com/deadline-cloud/)
5. Review the [DEVELOPMENT.md](https://github.com/aws-deadline/deadline-cloud-for-maya/blob/mainline/DEVELOPMENT.md) in the repository
