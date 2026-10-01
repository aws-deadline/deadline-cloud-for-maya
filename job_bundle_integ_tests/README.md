# Maya Integration Tests on Deadline Cloud

Runs the deadline-cloud-for-maya integration tests on a Deadline Cloud Service Managed Fleet with all supported renderer plugins (Arnold, V-Ray, Redshift).

## Prerequisites

- A Deadline Cloud farm with a queue that has the default Conda queue environment.
- The `deadline` CLI installed and configured (`deadline config`).

## Usage

```bash
cd /path/to/deadline-cloud-for-maya
deadline bundle submit job_bundle_integ_tests \
  --name "maya-integ-tests" \
  --parameter "RepoDir=." \
  --parameter "CondaPackages=maya=2026 maya-mtoa=2026.5.5 maya-vray=2026.7 maya-redshift=2026.2" \
  --max-retries-per-task 0
```

## Steps

| Step | Description |
|------|-------------|
| `submitter` | Runs submitter tests (`test_maya_submitters.py`). Validates that the Maya submitter generates correct job bundles. |
| `adaptor` | Runs adaptor tests (`test_maya_adaptors.py`). Validates that the Maya adaptor renders scenes correctly with all supported renderers. |

## How It Works

1. The repo is uploaded as a job attachment via the `RepoDir` input parameter.
2. A shared job environment installs the package and test dependencies into `mayapy`'s Python environment, and symlinks the adaptor entry points (`MayaAdaptor`, `maya-openjd`) onto PATH.
3. `QT_QPA_PLATFORM=offscreen` is set job-wide so PySide6 can initialize without a display server.
4. The submitter step additionally sets `LD_LIBRARY_PATH=$MAYA_LOCATION/lib` to fix PySide6/shiboken6 shared library loading. This is scoped to the submitter step only — setting it job-wide causes adaptor subprocesses to resolve to a broken system Python.
5. `numpy<2` is pinned because Maya 2026 bundles native modules compiled against NumPy 1.x.

## Customization

- To test against a different Maya version, change the `CondaPackages` parameter (e.g., `maya=2025 maya-mtoa=2025.5.4`).
- To run only specific tests, modify the pytest marker filter in the step's run script.
