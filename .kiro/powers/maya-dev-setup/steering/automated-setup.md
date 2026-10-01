---
title: Automated Maya Development Setup
description: Step-by-step automated setup workflow for deadline-cloud-for-maya development environment
---

# Automated Maya Development Setup

This guide provides the exact commands to set up a complete Maya development environment for deadline-cloud-for-maya on Linux (RHEL/AL2023).

## Prerequisites Check

Before starting, verify:
- Python 3.9+ is installed
- Maya 2024-2026 is installed (or will be installed)
- You have sudo access for system packages
- You're in the deadline-cloud-for-maya repository root

## Step 1: Fix Workspace Permissions

If the workspace is owned by root, fix permissions:

```bash
sudo chown -R $USER:$USER .
```

## Step 2: Install System Dependencies

### Install pip and virtualenv

```bash
# Bootstrap pip if not available
python3 -m ensurepip --upgrade

# Upgrade pip
python3 -m pip install --upgrade pip

# Install virtualenv (specific version for compatibility)
python3 -m pip install "virtualenv==20.28.1" --force-reinstall
```

### Install Maya System Dependencies

```bash
# Install required libraries for Maya
sudo dnf install -y libvdpau freetype alsa-lib fontconfig harfbuzz \
    libbrotli graphite2 libxkbfile xcb-util-cursor xcb-util-wm \
    xcb-util-keysyms libxkbcommon-x11
```

## Step 3: Install Hatch Build Tool

```bash
# Install hatch
python3 -m pip install --upgrade hatch

# Add hatch to PATH (add to ~/.bashrc for persistence)
export PATH="$HOME/.local/bin:$PATH"

# Verify installation
hatch --version
```

## Step 4: Create Maya Version File

```bash
# Create maya_version.txt with your Maya version
echo "2026" > maya_version.txt
```

## Step 5: Install pipgrip Dependency Resolver

```bash
python3 -m pip install pipgrip
```

## Step 6: Build the Package

```bash
# Build wheel and source distribution
hatch build

# Verify build artifacts
ls -lh dist/
```

## Step 7: Install Dev Submitter Plugin

```bash
# Install the dev submitter for your Maya version
hatch run install --maya-version 2026

# Verify plugin_env was created
ls -la plugin_env/
```

## Step 8: Install Packages into Maya's Python

### Find Maya Python Path

```bash
# Maya 2026 on Linux
MAYAPY="/usr/autodesk/maya2026/bin/mayapy"

# Verify mayapy works
$MAYAPY --version
```

### Install deadline-cloud-for-maya

```bash
# Install in editable mode
$MAYAPY -m pip install -e . --force-reinstall
```

### Install Testing Dependencies

```bash
# Install unit testing dependencies
$MAYAPY -m pip install -r requirements-testing.txt

# Install integration testing dependencies
$MAYAPY -m pip install -r requirements-integ-testing.txt
```

## Step 9: Create Environment Setup Script

Create `setup_maya_dev_env.sh`:

```bash
cat > setup_maya_dev_env.sh << 'EOF'
#!/bin/bash
# Maya Development Environment Setup Script
# Source this file to configure your environment for Maya development

# Maya Configuration
export MAYA_VERSION=2026
export MAYA_LOCATION="/usr/autodesk/maya${MAYA_VERSION}"
export MAYAPY_EXECUTABLE="${MAYA_LOCATION}/bin/mayapy"

# Add Maya binaries to PATH
export PATH="${MAYA_LOCATION}/bin:$PATH"

# Add hatch to PATH
export PATH="$HOME/.local/bin:$PATH"

# Maya module paths for renderer plugins
export MAYA_MODULE_PATH="/usr/autodesk/maya${MAYA_VERSION}/modules:/usr/autodesk/modules/maya/${MAYA_VERSION}:/usr/autodesk/modules/maya"

# Plugin environment directory (set by hatch shell automatically)
export MAYA_ENV_DIR="$(pwd)/plugin_env"

# Enable developer options in the submitter
export DEADLINE_ENABLE_DEVELOPER_OPTIONS=true

# License environment variables (update with your license servers)
export ADSKFLEX_LICENSE_FILE="27002@localhost"
export FLEXLM_TIMEOUT="3000000"
export redshift_LICENSE="5054@localhost"
# export PIXAR_LICENSE_FILE="9010@localhost"  # Uncomment if using RenderMan

# V-Ray EULA
export VRAY_EULA="https://docs.chaos.com/display/VNS/End+User+License+Agreement"

# Arnold error on license failure (false for watermarked renders in tests)
export ArnoldErrorOnLicenseFailure=false

echo "Maya Development Environment Configured!"
echo "  Maya Version: ${MAYA_VERSION}"
echo "  Maya Location: ${MAYA_LOCATION}"
echo "  mayapy: ${MAYAPY_EXECUTABLE}"
echo "  Plugin Environment: ${MAYA_ENV_DIR}"
echo ""
echo "Available commands:"
echo "  hatch build              - Build wheel and sdist packages"
echo "  hatch run test           - Run unit tests"
echo "  hatch run install        - Install dev submitter plugin"
echo "  hatch run lint           - Check code formatting"
echo "  hatch run fmt            - Auto-format code"
echo "  hatch shell              - Enter hatch development shell"
echo "  maya                     - Launch Maya with dev plugin"
echo "  mayapy                   - Run Maya Python interpreter"
echo "  maya-openjd              - Run Maya adaptor CLI"
echo ""
echo "Integration tests:"
echo "  hatch run integ:test                  - Run all integration tests"
echo "  hatch run integ:test_submitters       - Run submitter tests"
echo "  hatch run integ:test_adaptors_all     - Run all adaptor tests"
echo "  hatch run integ:test_adaptors_maya    - Run Maya renderer tests"
echo "  hatch run integ:test_adaptors_redshift - Run Redshift tests"
echo ""
echo "To launch Maya with the dev plugin:"
echo "  hatch shell"
echo "  maya"
EOF

chmod +x setup_maya_dev_env.sh
```

## Step 10: Verify Installation

```bash
# Source the environment
source setup_maya_dev_env.sh

# Verify Maya Python
mayapy --version

# Test Maya standalone initialization
mayapy -c "import maya.standalone; maya.standalone.initialize(); print('Maya OK'); maya.standalone.uninitialize()"

# Verify packages are importable
mayapy -c "import deadline.maya_adaptor; print('✓ adaptor')"
mayapy -c "import deadline.maya_submitter; print('✓ submitter')"
mayapy -c "import pytest; print('✓ pytest')"

# Verify adaptor CLI
maya-openjd version-info

# Run a quick unit test
hatch run test -k "test_" --maxfail=1
```

## Complete Setup Script

For convenience, here's a complete automated setup script:

```bash
#!/bin/bash
set -e

echo "=== Maya Development Environment Setup ==="
echo ""

# Step 1: Fix permissions
echo "Step 1: Fixing workspace permissions..."
sudo chown -R $USER:$USER .

# Step 2: Install system dependencies
echo "Step 2: Installing system dependencies..."
python3 -m ensurepip --upgrade
python3 -m pip install --upgrade pip
python3 -m pip install "virtualenv==20.28.1" --force-reinstall
sudo dnf install -y libvdpau freetype alsa-lib fontconfig harfbuzz \
    libbrotli graphite2 libxkbfile xcb-util-cursor xcb-util-wm \
    xcb-util-keysyms libxkbcommon-x11

# Step 3: Install hatch
echo "Step 3: Installing hatch..."
python3 -m pip install --upgrade hatch
export PATH="$HOME/.local/bin:$PATH"

# Step 4: Create Maya version file
echo "Step 4: Creating Maya version file..."
echo "2026" > maya_version.txt

# Step 5: Install pipgrip
echo "Step 5: Installing pipgrip..."
python3 -m pip install pipgrip

# Step 6: Build package
echo "Step 6: Building package..."
hatch build

# Step 7: Install dev submitter
echo "Step 7: Installing dev submitter plugin..."
hatch run install --maya-version 2026

# Step 8: Install into Maya's Python
echo "Step 8: Installing packages into Maya's Python..."
MAYAPY="/usr/autodesk/maya2026/bin/mayapy"
$MAYAPY -m pip install -e . --force-reinstall
$MAYAPY -m pip install -r requirements-testing.txt
$MAYAPY -m pip install -r requirements-integ-testing.txt

# Step 9: Create environment script
echo "Step 9: Creating environment setup script..."
cat > setup_maya_dev_env.sh << 'EOFSCRIPT'
#!/bin/bash
export MAYA_VERSION=2026
export MAYA_LOCATION="/usr/autodesk/maya${MAYA_VERSION}"
export MAYAPY_EXECUTABLE="${MAYA_LOCATION}/bin/mayapy"
export PATH="${MAYA_LOCATION}/bin:$HOME/.local/bin:$PATH"
export MAYA_MODULE_PATH="/usr/autodesk/maya${MAYA_VERSION}/modules:/usr/autodesk/modules/maya/${MAYA_VERSION}:/usr/autodesk/modules/maya"
export MAYA_ENV_DIR="$(pwd)/plugin_env"
export DEADLINE_ENABLE_DEVELOPER_OPTIONS=true
export ADSKFLEX_LICENSE_FILE="27002@localhost"
export FLEXLM_TIMEOUT="3000000"
export redshift_LICENSE="5054@localhost"
export VRAY_EULA="https://docs.chaos.com/display/VNS/End+User+License+Agreement"
export ArnoldErrorOnLicenseFailure=false
echo "Maya Development Environment Configured!"
EOFSCRIPT
chmod +x setup_maya_dev_env.sh

# Step 10: Verify
echo "Step 10: Verifying installation..."
source setup_maya_dev_env.sh > /dev/null 2>&1
$MAYAPY -c "import deadline.maya_adaptor, deadline.maya_submitter, pytest; print('✓ All packages OK')"

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "To activate the environment, run:"
echo "  source setup_maya_dev_env.sh"
echo ""
echo "To launch Maya with the dev plugin:"
echo "  hatch shell"
echo "  maya"
```

## Post-Setup Configuration

### Update License Servers

Edit `setup_maya_dev_env.sh` and update these variables with your actual license server addresses:

```bash
export ADSKFLEX_LICENSE_FILE="27002@your-license-server"
export redshift_LICENSE="5054@your-license-server"
export PIXAR_LICENSE_FILE="9010@your-license-server"
```

### Add to Shell Profile

For persistent environment setup, add to `~/.bashrc`:

```bash
# Maya Development Environment
if [ -f ~/deadline-cloud-for-maya/setup_maya_dev_env.sh ]; then
    source ~/deadline-cloud-for-maya/setup_maya_dev_env.sh
fi
```

## Common Issues and Solutions

### Issue: "Permission denied" on dist/

**Solution:**
```bash
sudo chown -R $USER:$USER .
```

### Issue: "module 'virtualenv.discovery.builtin' has no attribute 'propose_interpreters'"

**Solution:**
```bash
python3 -m pip install "virtualenv==20.28.1" --force-reinstall
```

### Issue: "libvdpau.so.1: cannot open shared object file"

**Solution:**
```bash
sudo dnf install -y libvdpau
```

### Issue: Plugin not appearing in Maya

**Solution:**
1. Ensure you launched Maya from within `hatch shell`
2. Check `MAYA_ENV_DIR` is set: `echo $MAYA_ENV_DIR`
3. Verify plugin files exist: `ls plugin_env/plug-ins/`

### Issue: Integration tests failing

**Solution:**
1. Ensure `mayapy` is in PATH: `which mayapy`
2. Verify packages: `mayapy -c "import deadline.maya_adaptor"`
3. Check Maya can initialize: `mayapy -c "import maya.standalone; maya.standalone.initialize()"`

## Development Workflow

### After Code Changes

```bash
# Submitter changes
hatch run install --maya-version 2026
# Then reload plugin in Maya's Plug-in Manager

# Adaptor changes
# No reinstall needed, changes are live in editable mode
hatch run integ:test_adaptors_maya

# Always run tests
hatch run fmt
hatch run lint
hatch run test
```

### Running Tests

```bash
# Unit tests
hatch run test

# Integration tests
hatch run integ:test_submitters
hatch run integ:test_adaptors_maya

# Job bundle output tests (in Maya)
# 1. Launch Maya with DEADLINE_ENABLE_DEVELOPER_OPTIONS=true
# 2. Click TEST button on AWSDeadline shelf
# 3. Select job_bundle_output_tests/ directory
```

## Environment Variables Reference

| Variable | Purpose | Default Value |
|----------|---------|---------------|
| `MAYA_VERSION` | Maya version number | 2026 |
| `MAYA_LOCATION` | Maya installation directory | `/usr/autodesk/maya2026` |
| `MAYAPY_EXECUTABLE` | Maya Python interpreter path | `${MAYA_LOCATION}/bin/mayapy` |
| `MAYA_MODULE_PATH` | Module search paths | System module directories |
| `MAYA_ENV_DIR` | Dev plugin location | `$(pwd)/plugin_env` |
| `DEADLINE_ENABLE_DEVELOPER_OPTIONS` | Enable TEST button | `true` |
| `ADSKFLEX_LICENSE_FILE` | Autodesk license server | `27002@localhost` |
| `FLEXLM_TIMEOUT` | License timeout | `3000000` |
| `redshift_LICENSE` | Redshift license server | `5054@localhost` |
| `ArnoldErrorOnLicenseFailure` | Allow watermarked renders | `false` |

## File Structure After Setup

```
deadline-cloud-for-maya/
├── setup_maya_dev_env.sh          # Environment setup script
├── maya_version.txt                # Maya version (2026)
├── dist/                           # Built packages
│   ├── *.whl                       # Wheel package
│   └── *.tar.gz                    # Source distribution
├── plugin_env/                     # Dev plugin installation
│   ├── DeadlineCloudForMaya.mod    # Maya module file
│   ├── Maya.env                    # Maya environment file
│   ├── plug-ins/                   # Plugin files
│   ├── icons/                      # UI icons
│   └── scripts/                    # Python packages and dependencies
├── src/deadline/
│   ├── maya_adaptor/               # Adaptor source code
│   └── maya_submitter/             # Submitter source code
└── test/
    ├── unit/                       # Unit tests
    └── integ/                      # Integration tests
```

## Next Steps

1. **Configure licenses** - Update license servers in `setup_maya_dev_env.sh`
2. **Install renderers** - Install Arnold, V-Ray, or Redshift if needed
3. **Set up AWS** - Configure AWS credentials for Deadline Cloud
4. **Start developing** - See DEVELOPMENT.md for detailed workflows

## Verification Checklist

- [ ] Hatch installed and in PATH
- [ ] Maya 2026 installed
- [ ] mayapy accessible and working
- [ ] Package built successfully (dist/ directory exists)
- [ ] Dev plugin installed (plugin_env/ directory exists)
- [ ] Packages importable in Maya Python
- [ ] maya-openjd CLI working
- [ ] Unit tests pass
- [ ] Environment script created

Run this to verify all:

```bash
source setup_maya_dev_env.sh
hatch --version && \
mayapy --version && \
mayapy -c "import deadline.maya_adaptor, deadline.maya_submitter, pytest; print('✓ All OK')" && \
maya-openjd version-info && \
echo "✅ Setup verified successfully!"
```
