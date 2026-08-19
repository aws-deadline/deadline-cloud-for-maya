# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#!/usr/bin/env python3
"""Setup runner for Maya integration tests in CodeBuild.

Supports Linux and Windows for the Maya versions in MAYA_YEAR_TO_CONFIG below.

A Maya version only needs an installer for the platforms it is available on. A
configured version with no installer for the current platform is skipped with a
warning instead of failing the run, so a Maya version can be added to the test
matrix as soon as one platform's installer is available. Requesting a version
that is not in MAYA_YEAR_TO_CONFIG at all is still an error.

Installs the Arnold (MtoA), V-Ray, and Redshift renderers into each Maya
version so the renderer-specific integ tests can run.
Use --renderers to select which renderers to install (default: none).

On Windows, installs the pywin32 support DLLs so child processes (mayapy) can
load win32file. This mirrors the pattern used by deadline-cloud-for-3ds-max.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence, TypedDict

import boto3
from botocore.config import Config

# ---------------------------------------------------------------------------
# Configuration types
# ---------------------------------------------------------------------------


# Maya installer filenames and SHA256 checksums, keyed by platform ("linux" or
# "windows"). A platform key may be omitted when there is no installer for that
# platform yet; the Maya version is then skipped on that platform instead of
# failing the whole setup run.
InstallerPaths = dict[str, str]
MayaChecksums = dict[str, str]


class MayaVersionConfig(TypedDict):
    python: str
    installer: InstallerPaths


class RendererVersionConfig(TypedDict):
    s3_key: str
    checksum: str


class RedshiftPlatformConfig(TypedDict):
    s3_key: str
    checksum: str


# ---------------------------------------------------------------------------
# Maya
# ---------------------------------------------------------------------------

MAYA_YEAR_TO_CONFIG: dict[str, MayaVersionConfig] = {
    "2025": {
        "python": "3.11",
        "installer": {
            "linux": "Autodesk_MayaIO_2025_3_ML_Linux_64bit.run",
            "windows": "Maya2025_Windows.zip",
        },
    },
    "2026": {
        "python": "3.11",
        "installer": {
            "linux": "Autodesk_MayaIO_2026_3_Update_Linux.run",
            "windows": "Maya2026_Windows.zip",
        },
    },
}

MAYA_YEAR_TO_CHECKSUMS: dict[str, MayaChecksums] = {
    "2025": {
        "linux": "a4c46a576aea91e1e52a06355b413f98000b884feb8eb1349a7459990e212395",
        "windows": "0f9ce4abc7febbef07b0ef5ecd2526a45200a9b068a6272f6f2afdd29925a845",
    },
    "2026": {
        "linux": "b17b0700933e8e4329939da38cc52c93ed483a93b02e9fa78031fddae763c8e8",
        "windows": "9c9612f6e4d3f1f6de897a21fde6f9930e2e40bb6ddc3ca9647e2668cdba935c",
    },
}

# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

# Arnold (MtoA) — one installer per Maya version.
MTOA_YEAR_TO_CONFIG: dict[str, RendererVersionConfig] = {
    "2025": {
        "s3_key": "mtoa/5.5/MtoA-5.5.6.1-linux-2025.run",
        "checksum": "7f607c05461efec4ebd9f7d40e0d3e6de3e2dccba51078e1ccfaf598b77af389",
    },
    "2026": {
        "s3_key": "mtoa/5.5/MtoA-5.5.6.1-linux-2026.run",
        "checksum": "d8881e1cece725178d90aaa6d44507ea017ec64d7d23c76b129b9e349d1c9cc6",
    },
}

# V-Ray for Maya — Chaos RHEL8 self-extracting installer per Maya version.
VRAY_YEAR_TO_CONFIG: dict[str, RendererVersionConfig] = {
    "2025": {
        "s3_key": "maya-vray/72002/vray_adv_72002_maya2025_dr2_rhel8",
        "checksum": "cdbeba5ea82120155ecda75da01e359d1dc01f8905a4751d233b40136f9610c6",
    },
    "2026": {
        "s3_key": "maya-vray/72002/vray_adv_72002_maya2026_dr2_rhel8",
        "checksum": "a6e1e65202f6c9b3d4e12e7eb423a780a34dfeac3540658b16f4e20f8009fca6",
    },
}

# Redshift — single installer supports both Maya 2025 and 2026.
REDSHIFT_PLATFORM_CONFIG: dict[str, RedshiftPlatformConfig] = {
    "linux": {
        "s3_key": "redshift/2026/redshift_2026.3.1_2336394021_linux_x64.run",
        "checksum": "a95e48d2f4dd68e923c7f40693823d206d11acb51e145038d5625b748294777c",
    },
}

SUPPORTED_RENDERERS: tuple[str, ...] = ("mtoa", "vray", "redshift")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def run(
    cmd: str | Sequence[str],
    check: bool = True,
    cwd: str | os.PathLike[str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    print(f"Running: {cmd if isinstance(cmd, str) else shlex.join(cmd)}")
    result = subprocess.run(cmd, check=False, cwd=cwd)
    if check and result.returncode != 0:
        sys.exit(result.returncode)
    return result


# Renderer installs (especially V-Ray) can take several minutes on cold fleets.
DEFAULT_CMD_TIMEOUT = 600


def run_with_timeout(
    cmd: str | Sequence[str],
    timeout: int = DEFAULT_CMD_TIMEOUT,
    cwd: str | os.PathLike[str] | None = None,
    label: str = "",
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Run a command with a timeout. Prints stdout/stderr on failure for diagnostics."""
    desc = label or (cmd if isinstance(cmd, str) else shlex.join(cmd))
    print(f"Running (timeout={timeout}s): {desc}")
    run_env = None
    if env:
        run_env = {**os.environ, **env}
    try:
        result = subprocess.run(
            cmd,
            check=False,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            env=run_env,
        )
        # Always print output for visibility
        if result.stdout:
            print(result.stdout.decode("utf-8", errors="replace"))
        if result.stderr:
            print(result.stderr.decode("utf-8", errors="replace"))
        if result.returncode != 0:
            print(f"ERROR: Command failed with exit code {result.returncode}")
            sys.exit(result.returncode)
        return result
    except subprocess.TimeoutExpired as e:
        print(f"TIMEOUT: Command did not complete within {timeout}s: {desc}")
        if e.stdout:
            print(f"stdout so far:\n{e.stdout.decode('utf-8', errors='replace')[-2000:]}")
        if e.stderr:
            print(f"stderr so far:\n{e.stderr.decode('utf-8', errors='replace')[-2000:]}")
        sys.exit(1)


def download_from_s3(s3_path: str, local_path: str | os.PathLike[str]) -> None:
    bucket = os.environ.get("INSTALLER_BUCKET")
    if not bucket:
        raise RuntimeError("INSTALLER_BUCKET environment variable is required")
    expected_bucket_owner = os.environ.get("INSTALLER_BUCKET_EXPECTED_OWNER")
    if not expected_bucket_owner:
        raise RuntimeError("INSTALLER_BUCKET_EXPECTED_OWNER environment variable is required")
    if not (expected_bucket_owner.isdigit() and len(expected_bucket_owner) == 12):
        raise RuntimeError("INSTALLER_BUCKET_EXPECTED_OWNER must be a 12-digit AWS Account ID")

    config = Config(read_timeout=300, connect_timeout=60, retries={"max_attempts": 2})
    s3 = boto3.client("s3", config=config)
    print(f"Downloading s3://{bucket}/{s3_path} to {local_path}")
    s3.download_file(
        bucket,
        s3_path,
        str(local_path),
        ExtraArgs={"ExpectedBucketOwner": expected_bucket_owner},
    )


def verify_checksum(file_path: str | os.PathLike[str], expected_checksum: str) -> bool:
    """Verify SHA256 checksum of downloaded file."""
    if not expected_checksum:
        print(f"WARNING: No checksum configured for {file_path}, skipping verification")
        return True
    print(f"Verifying checksum for {file_path}...")
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    actual = sha256.hexdigest()
    if actual != expected_checksum:
        print("ERROR: Checksum mismatch!")
        print(f"  Expected: {expected_checksum}")
        print(f"  Actual:   {actual}")
        sys.exit(1)
    print("OK Checksum verified")
    return True


PLATFORM_TO_KEY: dict[str, str] = {
    "Linux": "linux",
    "Windows": "windows",
}


def maya_installer_name(version: str, plat_key: str) -> str | None:
    """Return the Maya installer filename for a platform, or None if not configured."""
    config = MAYA_YEAR_TO_CONFIG.get(version)
    if config is None:
        return None
    return config["installer"].get(plat_key)


def maya_checksum(version: str, plat_key: str) -> str:
    """Return the expected Maya installer checksum, or "" when none is configured.

    verify_checksum() warns and continues when given an empty checksum.
    """
    return MAYA_YEAR_TO_CHECKSUMS.get(version, {}).get(plat_key, "")


def validate_versions(maya_versions: Sequence[str]) -> None:
    """Fail fast on requested Maya versions that cannot be installed on any platform.

    An unknown version means the caller and MAYA_YEAR_TO_CONFIG have drifted
    apart (the hatch integ-ci matrix supplies --versions), and a version with an
    empty installer map is an incomplete config entry. Neither can be satisfied
    on any platform, so both are errors rather than skips.
    """
    for version in maya_versions:
        config = MAYA_YEAR_TO_CONFIG.get(version)
        if config is None:
            print(f"ERROR: Unsupported Maya version: {version}")
            print(f"Supported versions: {list(MAYA_YEAR_TO_CONFIG)}")
            sys.exit(1)
        if not config["installer"]:
            print(f"ERROR: Maya {version} has no installer configured for any platform")
            sys.exit(1)


def select_installable_versions(
    maya_versions: Sequence[str], plat_key: str, system: str
) -> list[str]:
    """Filter requested Maya versions down to those installable on this platform.

    A configured version with no installer for this platform is skipped with a
    warning rather than failing the run, so a Maya version can be added to the
    test matrix before installers exist for every platform. Callers are expected
    to have already rejected versions missing from MAYA_YEAR_TO_CONFIG.
    """
    installable: list[str] = []
    for version in maya_versions:
        if maya_installer_name(version, plat_key):
            installable.append(version)
        else:
            print(f"SKIP: No {system} installer configured for Maya {version}")
    return installable


# ---------------------------------------------------------------------------
# Linux
# ---------------------------------------------------------------------------


def _install_maya_linux(version: str) -> Path:
    installer_name = MAYA_YEAR_TO_CONFIG[version]["installer"]["linux"]
    maya_dir = Path(f"/opt/Autodesk/mayaio/{version}")

    # Check if Maya is already installed by looking for the real binary
    existing = subprocess.run(
        ["find", str(maya_dir), "-name", "mayapy", "-type", "f"],
        capture_output=True,
        text=True,
        check=False,
    )
    if existing.stdout.strip():
        print(f"Maya {version} already installed: {existing.stdout.strip().split(chr(10))[0]}")
        return maya_dir

    lock_file = Path(f"/tmp/maya-{version}.lock")
    if lock_file.exists():
        print(f"Waiting for concurrent Maya {version} install...")
        for _ in range(120):
            time.sleep(1)
            check = subprocess.run(
                ["find", str(maya_dir), "-name", "mayapy", "-type", "f"],
                capture_output=True,
                text=True,
                check=False,
            )
            if check.stdout.strip():
                break
        return maya_dir

    lock_file.touch()
    try:
        print(f"Installing Maya {version}...")
        installer_path = Path(f"/tmp/{installer_name}")

        download_from_s3(f"maya/{version}/{installer_name}", installer_path)
        verify_checksum(installer_path, maya_checksum(version, "linux"))

        run(["chmod", "+x", str(installer_path)])
        # Extract to /opt (not /tmp) and clean any stale dir from prior runs
        extract_dir = Path(f"/opt/maya-{version}-extract")
        if extract_dir.exists():
            run(["rm", "-rf", str(extract_dir)], check=False)
        # --noexec: don't run post-extract scripts (they do rm -rf /tmp/*)
        # --phase2: skip EULA prompt
        print("Extracting installer (this may take a moment)...")
        result = subprocess.run(
            [
                str(installer_path),
                "--noexec",
                "--keep",
                "--nox11",
                "--target",
                str(extract_dir),
                "--phase2",
            ],
            check=False,
        )
        print(f"Installer exit code: {result.returncode}")

        # The .run extracts to a directory containing an RPM.
        # Use rpm2cpio to extract it (same approach as BealineCondaRecipe-Maya).
        maya_dir.mkdir(parents=True, exist_ok=True)
        rpms = list(extract_dir.rglob("*.rpm"))
        if not rpms:
            print(f"ERROR: No RPM found in {extract_dir}")
            run(["ls", "-la", str(extract_dir)], check=False)
            sys.exit(1)
        rpm_path = rpms[0].resolve()
        subprocess.run(
            f"rpm2cpio {rpm_path} | cpio -idm",
            shell=True,
            check=True,
            cwd=maya_dir,
        )

        # MayaIO RPM extracts to usr/autodesk/mayaIO<version>/ inside cwd
        # The exact directory name varies by version — find mayapy dynamically.
        result = subprocess.run(
            ["find", str(maya_dir), "-name", "mayapy", "-type", "f"],
            capture_output=True,
            text=True,
            check=False,
        )
        mayapy_exe = None
        if result.stdout.strip():
            mayapy_exe = Path(result.stdout.strip().split("\n")[0])
        # Verify installation
        if mayapy_exe and mayapy_exe.exists():
            print(f"SUCCESS: mayapy found at {mayapy_exe}")
        else:
            print(f"ERROR: mayapy NOT found under {maya_dir}")
            run(
                ["find", str(maya_dir), "-maxdepth", "5", "-type", "f", "-name", "maya*"],
                check=False,
            )
            sys.exit(1)

        installer_path.unlink(missing_ok=True)
        run(["rm", "-rf", str(extract_dir)], check=False)
    finally:
        lock_file.unlink(missing_ok=True)

    return maya_dir


def _install_mtoa_linux(version: str) -> None:
    """Install MtoA (Arnold for Maya) for the given Maya version."""
    if version not in MTOA_YEAR_TO_CONFIG:
        print(f"ERROR: No MtoA config for Maya {version}")
        sys.exit(1)

    mtoa_install_dir = Path(f"/opt/solidangle/mtoa/{version}")
    marker = mtoa_install_dir / ".installed"
    if marker.exists():
        print(f"MtoA for Maya {version} already installed")
        return

    lock_file = Path(f"/tmp/mtoa-{version}.lock")
    if lock_file.exists():
        print(f"Waiting for concurrent MtoA {version} install...")
        for _ in range(120):
            time.sleep(1)
            if Path(f"/opt/solidangle/mtoa/{version}/.installed").exists():
                break
        return

    lock_file.touch()
    try:
        s3_key = MTOA_YEAR_TO_CONFIG[version]["s3_key"]
        installer_name = Path(s3_key).name
        installer_path = Path(f"/tmp/{installer_name}")

        print(f"Installing MtoA for Maya {version}...")
        download_from_s3(s3_key, installer_path)
        verify_checksum(installer_path, MTOA_YEAR_TO_CONFIG[version]["checksum"])

        run(["chmod", "+x", str(installer_path)])
        mtoa_install_dir.mkdir(parents=True, exist_ok=True)
        # MtoA is a Makeself archive. Extract then unzip the package.
        extract_tmp = Path(f"/tmp/mtoa-{version}-extract")
        if extract_tmp.exists():
            run(["rm", "-rf", str(extract_tmp)], check=False)
        run([str(installer_path), "--noexec", "--target", str(extract_tmp)])
        # Unzip the package into the install dir
        pkg_zip = next(extract_tmp.glob("*.zip"), None)
        if pkg_zip:
            run(["unzip", "-qo", str(pkg_zip), "-d", str(mtoa_install_dir)])
        else:
            print(f"ERROR: No .zip found in {extract_tmp}")
            run(["ls", "-la", str(extract_tmp)], check=False)
            sys.exit(1)
        run(["rm", "-rf", str(extract_tmp)], check=False)

        # Verify — installer lays down plugins under $prefix/plug-ins.
        arnold_plugin = mtoa_install_dir / "plug-ins" / "mtoa.so"
        if arnold_plugin.exists():
            print(f"SUCCESS: mtoa.so found at {arnold_plugin}")
        else:
            # Some MtoA versions extract into a versioned subdir — list for visibility.
            print(f"WARNING: mtoa.so not found at {arnold_plugin}, dumping install tree:")
            run(["find", str(mtoa_install_dir), "-maxdepth", "3"], check=False)
            # Still mark installed — plugin layout varies between versions. Tests
            # will fail fast and visibly if the plugin is actually missing.

        installer_path.unlink(missing_ok=True)
    finally:
        lock_file.unlink(missing_ok=True)


def _install_vray_linux(version: str) -> None:
    """Install V-Ray for Maya for the given Maya version."""
    if version not in VRAY_YEAR_TO_CONFIG:
        print(f"ERROR: No V-Ray config for Maya {version}")
        sys.exit(1)

    vray_install_dir = Path(f"/usr/ChaosGroup/V-Ray/Maya{version}-x64")
    marker = vray_install_dir / ".installed"
    if marker.exists():
        print(f"V-Ray for Maya {version} already installed")
        return

    lock_file = Path(f"/tmp/vray-{version}.lock")
    if lock_file.exists():
        print(f"Waiting for concurrent V-Ray {version} install...")
        for _ in range(180):
            time.sleep(1)
            if Path(f"/usr/ChaosGroup/V-Ray/Maya{version}-x64/.installed").exists():
                break
        return

    lock_file.touch()
    try:
        s3_key = VRAY_YEAR_TO_CONFIG[version]["s3_key"]
        installer_name = Path(s3_key).name
        installer_path = Path(f"/tmp/{installer_name}")

        print(f"Installing V-Ray for Maya {version}...")
        download_from_s3(s3_key, installer_path)
        verify_checksum(installer_path, VRAY_YEAR_TO_CONFIG[version]["checksum"])

        run(["chmod", "+x", str(installer_path)])
        # Chaos V-Ray installer uses custom flags for silent install
        vray_install_dir.mkdir(parents=True, exist_ok=True)
        run(
            [
                str(installer_path),
                "-gui=0",
                "-auto",
                "-quiet=1",
                f"-unpackInstall={vray_install_dir}",
            ],
            check=False,
        )

        # Verify — vray binary lands under $prefix/vray/bin.
        vray_bin = vray_install_dir / "vray" / "bin" / "vray"
        if vray_bin.exists():
            print(f"SUCCESS: vray binary found at {vray_bin}")
        else:
            print(f"WARNING: vray binary not found at {vray_bin}, dumping install tree:")
            run(["find", str(vray_install_dir), "-maxdepth", "3"], check=False)
        marker.touch()

        installer_path.unlink(missing_ok=True)
    finally:
        lock_file.unlink(missing_ok=True)


def _install_redshift_linux() -> None:
    """Install Redshift once; it plugs into every Maya version at runtime."""
    redshift_root = Path("/usr/redshift")
    marker = redshift_root / ".installed"
    if marker.exists():
        print("Redshift already installed")
        return

    lock_file = Path("/tmp/redshift.lock")
    if lock_file.exists():
        print("Waiting for concurrent Redshift install...")
        for _ in range(180):
            time.sleep(1)
            if Path("/usr/redshift/.installed").exists():
                break
        return

    lock_file.touch()
    try:
        s3_key = REDSHIFT_PLATFORM_CONFIG["linux"]["s3_key"]
        installer_name = Path(s3_key).name
        installer_path = Path(f"/tmp/{installer_name}")

        print("Installing Redshift...")
        download_from_s3(s3_key, installer_path)
        verify_checksum(installer_path, REDSHIFT_PLATFORM_CONFIG["linux"]["checksum"])

        run(["chmod", "+x", str(installer_path)])
        # Redshift is a Makeself archive. Extract then untar the package.
        redshift_root.mkdir(parents=True, exist_ok=True)
        extract_tmp = Path("/tmp/redshift-extract")
        if extract_tmp.exists():
            run(["rm", "-rf", str(extract_tmp)], check=False)
        run([str(installer_path), "--noexec", "--target", str(extract_tmp)])
        # Extract the tarball into the install dir
        pkg_tar = next(extract_tmp.glob("*.tar.gz"), None)
        if pkg_tar:
            run(["tar", "xzf", str(pkg_tar), "-C", str(redshift_root)])
        else:
            print(f"ERROR: No .tar.gz found in {extract_tmp}")
            run(["ls", "-la", str(extract_tmp)], check=False)
            sys.exit(1)
        run(["rm", "-rf", str(extract_tmp)], check=False)

        # Verify — redshiftCmdLine lands in $prefix/bin.
        redshift_cmd = redshift_root / "bin" / "redshiftCmdLine"
        if redshift_cmd.exists():
            print(f"SUCCESS: redshiftCmdLine found at {redshift_cmd}")
        else:
            print(f"WARNING: redshiftCmdLine not found at {redshift_cmd}, dumping install tree:")
            run(["find", str(redshift_root), "-maxdepth", "3"], check=False)
        marker.touch()

        installer_path.unlink(missing_ok=True)
    finally:
        lock_file.unlink(missing_ok=True)


def _clean_stale_locks(maya_versions: Sequence[str]) -> None:
    """Remove stale lock files from previous failed runs on reserved capacity fleets."""
    for version in maya_versions:
        lock_file = Path(f"/tmp/maya-{version}.lock")
        if lock_file.exists():
            print(f"Removing stale lock file for Maya {version}")
            lock_file.unlink()


def setup_linux(maya_versions: Sequence[str], renderers: Sequence[str]) -> None:
    pkg_mgr = (
        "dnf"
        if subprocess.run(["command", "-v", "dnf"], capture_output=True, check=False).returncode
        == 0
        else "yum"
    )

    # Install dependencies needed by Maya
    run(
        [
            pkg_mgr,
            "install",
            "-y",
            "libGLU",
            "mesa-libGL",
            "mesa-libEGL",
            "libXmu",
            "libXt",
            "libXi",
            "libXext",
            "libX11",
            "libXrender",
            "libXrandr",
            "libXfixes",
            "libXcursor",
            "libXinerama",
            "libxkbcommon",
            "libxkbcommon-x11",
            "fontconfig",
            "xorg-x11-server-Xvfb",
            "libva",
            "libvdpau",
            "pciutils-libs",
            "libglvnd-opengl",
            "libglvnd-egl",
            "alsa-lib",
            "nss",
        ]
    )

    # Start Xvfb if not already running
    if run(["pgrep", "Xvfb"], check=False).returncode != 0:
        subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1024x768x24"])
        run(["sleep", "2"])
        print("\nXvfb started. DISPLAY=:99")

    # Clean stale lock files from previous failed runs (reserved capacity persists)
    _clean_stale_locks(maya_versions)

    # Install Maya first — MtoA/V-Ray/Redshift plug into an existing Maya install.
    for version in maya_versions:
        _install_maya_linux(version)

    # Install the submitter and deps into each Maya version
    for version in maya_versions:
        maya_dir = Path(f"/opt/Autodesk/mayaio/{version}")
        # Find mayapy
        result = subprocess.run(
            ["find", str(maya_dir), "-name", "mayapy", "-type", "f"],
            capture_output=True,
            text=True,
            check=False,
        )
        mayapy_exe = Path(result.stdout.strip().split("\n")[0]) if result.stdout.strip() else None
        if not mayapy_exe or not mayapy_exe.exists():
            print(f"ERROR: Cannot find mayapy for Maya {version}")
            sys.exit(1)

        print(f"Installing submitter for Maya {version}...")
        run_with_timeout(
            ["hatch", "run", "install", "--maya-version", version],
            timeout=DEFAULT_CMD_TIMEOUT,
            label=f"hatch install submitter (Maya {version})",
        )

        # Maya's bundled Python lacks SSL, so we can't use mayapy -m pip.
        # Use system pip with --target to install into Maya's site-packages.
        maya_site_packages = (
            mayapy_exe.parent.parent
            / "lib"
            / f"python{MAYA_YEAR_TO_CONFIG[version]['python']}"
            / "site-packages"
        )
        maya_site_packages.mkdir(parents=True, exist_ok=True)
        python_version = MAYA_YEAR_TO_CONFIG[version]["python"]

        print(f"Installing integ test dependencies for Maya {version}...")
        run_with_timeout(
            [
                "pip",
                "install",
                "--target",
                str(maya_site_packages),
                "--python-version",
                python_version,
                "--only-binary=:all:",
                "-r",
                "requirements-integ-testing.txt",
                "-r",
                "requirements-testing.txt",
            ],
            timeout=DEFAULT_CMD_TIMEOUT,
            label=f"pip install requirements (Maya {version})",
        )

        # Install the package itself
        run_with_timeout(
            [
                "pip",
                "install",
                "--target",
                str(maya_site_packages),
                "--python-version",
                python_version,
                "--only-binary=:all:",
                ".",
            ],
            timeout=DEFAULT_CMD_TIMEOUT,
            label=f"pip install project (Maya {version})",
        )

        # Symlink mayapy to PATH so hatch integ-ci:test can find it.
        # Create a wrapper that sets MAYA_LOCATION and renderer plugin paths.
        mayapy_dir = mayapy_exe.parent.parent  # e.g. /opt/.../usr/autodesk/mayaIO2025

        # Renderer paths
        mtoa_dir = f"/opt/solidangle/mtoa/{version}"
        vray_dir = f"/usr/ChaosGroup/V-Ray/Maya{version}-x64"
        redshift_dir = "/usr/redshift"

        module_paths = ":".join(
            [
                mtoa_dir,  # contains mtoa.mod
                f"{vray_dir}/maya_root/modules",  # contains VRayForMaya.module
            ]
        )
        plugin_paths = f"{redshift_dir}/redshift4maya/{version}"
        script_paths = f"{redshift_dir}/redshift4maya/common/scripts"
        render_desc_paths = f"{redshift_dir}/redshift4maya/common/rendererDesc"

        wrapper = Path("/usr/local/bin/mayapy")
        wrapper.write_text(
            f"#!/bin/sh\n"
            f'export MAYA_LOCATION="{mayapy_dir}"\n'
            f'export LD_LIBRARY_PATH="{mayapy_dir}/lib:${{LD_LIBRARY_PATH:-}}"\n'
            f'export MAYA_MODULE_PATH="{module_paths}:${{MAYA_MODULE_PATH:-}}"\n'
            f'export MAYA_PLUG_IN_PATH="{plugin_paths}:${{MAYA_PLUG_IN_PATH:-}}"\n'
            f'export MAYA_SCRIPT_PATH="{script_paths}:${{MAYA_SCRIPT_PATH:-}}"\n'
            f'export MAYA_RENDER_DESC_PATH="{render_desc_paths}:${{MAYA_RENDER_DESC_PATH:-}}"\n'
            f'export REDSHIFT_COREDATAPATH="{redshift_dir}"\n'
            f'exec "{mayapy_exe}" "$@"\n'
        )
        run(["chmod", "+x", str(wrapper)])

    # Install requested renderers (always per-Maya-version, except Redshift which
    # is shared across versions).
    if "mtoa" in renderers:
        for version in maya_versions:
            _install_mtoa_linux(version)
    if "vray" in renderers:
        for version in maya_versions:
            _install_vray_linux(version)
    if "redshift" in renderers:
        _install_redshift_linux()


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------


def _install_maya_windows(version: str) -> Path:
    installer_name = MAYA_YEAR_TO_CONFIG[version]["installer"]["windows"]
    maya_dir = Path(f"C:/Program Files/Autodesk/Maya{version}")
    maya_marker = maya_dir / ".installed"

    if maya_marker.exists():
        print(f"Maya {version} already installed")
        return maya_dir

    print(f"Installing Maya {version}...")
    setup_dir = Path(f"C:/maya_setup/{version}")
    setup_dir.mkdir(parents=True, exist_ok=True)
    installer_zip = setup_dir / installer_name

    download_from_s3(f"maya/{version}/{installer_name}", installer_zip)
    verify_checksum(installer_zip, maya_checksum(version, "windows"))

    print("Extracting Maya installer...")
    run(
        [
            "powershell",
            "-Command",
            f"Expand-Archive -Path '{installer_zip}' -DestinationPath '{setup_dir}' -Force",
        ]
    )

    # The zip contains _001_002.exe (GUI, hangs headlessly) + _002_002.7z (payload).
    # Extract the .7z directly with 7-Zip, then run Setup.exe -q.
    seven_z = next(setup_dir.rglob("*_002_002.7z"), None)
    if seven_z is None:
        # Fallback: maybe it's a zip that already contains Setup.exe (e.g. Maya 2024)
        setup_exe = next(setup_dir.rglob("Setup.exe"), None)
    else:
        extract_dest = setup_dir / "extracted"
        extract_dest.mkdir(parents=True, exist_ok=True)
        print(f"Extracting 7z payload: {seven_z}")
        run(
            [
                "powershell",
                "-Command",
                f'& "C:\\Program Files\\7-Zip\\7z.exe" x "{seven_z}" "-o{extract_dest}" -y',
            ]
        )
        setup_exe = next(extract_dest.rglob("Setup.exe"), None)

    if setup_exe is None:
        print(f"ERROR: Setup.exe not found under {setup_dir}")
        run(["powershell", "-Command", f"Get-ChildItem -Recurse '{setup_dir}'"], check=False)
        sys.exit(1)

    print(f"Starting Maya installation via {setup_exe}...")
    result = subprocess.run(
        [
            "powershell",
            "-Command",
            f'Start-Process "{setup_exe}" -ArgumentList "-q" -Wait',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    print(f"Installation exit code: {result.returncode}")
    if result.stdout:
        print(f"Installation output: {result.stdout}")
    if result.stderr:
        print(f"Installation errors: {result.stderr}")

    mayapy_exe = maya_dir / "bin" / "mayapy.exe"
    if mayapy_exe.exists():
        print(f"SUCCESS: mayapy.exe found at {mayapy_exe}")
        maya_marker.touch()
    else:
        print(f"ERROR: mayapy.exe NOT found at {mayapy_exe}")
        run(["powershell", "-Command", f"Get-ChildItem -Recurse '{maya_dir}'"], check=False)
        sys.exit(1)

    # Cleanup extracted installer to reclaim disk space.
    run(
        ["powershell", "-Command", f"Remove-Item -Path '{setup_dir}' -Recurse -Force"],
        check=False,
    )

    return maya_dir


def _install_vray_windows(version: str) -> None:
    """Install V-Ray for Maya on Windows."""
    vray_win_config = {
        "2025": "maya-vray/70002/vray_adv_70002_maya2025_x64.exe",
        "2026": "maya-vray/71002/vray_adv_71002_maya2026_x64.exe",
    }
    if version not in vray_win_config:
        print(f"WARNING: No Windows V-Ray config for Maya {version}, skipping")
        return
    # V-Ray installs to Program Files and registers its .module with Maya automatically
    plugin_check = Path(
        f"C:/Program Files/Chaos/V-Ray/Maya {version} for x64/maya_vray/plug-ins/vrayformaya.mll"
    )
    if plugin_check.exists():
        print(f"V-Ray for Maya {version} already installed")
        return
    s3_key = vray_win_config[version]
    installer_path = Path(f"C:/temp/vray_{version}.exe")
    installer_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Installing V-Ray for Maya {version}...")
    download_from_s3(s3_key, installer_path)
    run(
        [
            "powershell",
            "-Command",
            f'Start-Process "{installer_path}" -ArgumentList "-gui=0","-auto","-quiet=1" -Wait -NoNewWindow',
        ]
    )
    installer_path.unlink(missing_ok=True)


def _install_mtoa_windows(version: str) -> None:
    """Install MtoA (Arnold) for Maya on Windows."""
    mtoa_win_config = {
        "2025": "mtoa/5.5/MtoA-5.5.4.2-windows-2025.msi",
        "2026": "mtoa/5.5/MtoA-5.5.4.2-windows-2026.msi",
    }
    if version not in mtoa_win_config:
        print(f"WARNING: No Windows MtoA config for Maya {version}, skipping")
        return
    plugin_check = Path(f"C:/Program Files/Autodesk/Arnold/maya{version}/plug-ins/mtoa.mll")
    if plugin_check.exists():
        print(f"MtoA for Maya {version} already installed")
        return
    s3_key = mtoa_win_config[version]
    installer_path = Path(f"C:/temp/mtoa_{version}.msi")
    installer_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Installing MtoA for Maya {version}...")
    download_from_s3(s3_key, installer_path)
    run(
        [
            "powershell",
            "-Command",
            f'Start-Process "msiexec" -ArgumentList "/i","{installer_path}","/quiet","/norestart" -Wait -NoNewWindow',
        ]
    )
    installer_path.unlink(missing_ok=True)


def _install_redshift_windows() -> None:
    """Install Redshift on Windows with Maya plugin registration."""
    redshift_root = Path("C:/Program Files/Maxon Redshift 2026")
    plugin_check = redshift_root / "Plugins" / "Maya" / "2025" / "nt-x86-64" / "redshift4maya.mll"
    if plugin_check.exists():
        print("Redshift already installed")
        return
    s3_key = "redshift/2026/redshift_2026.6.0_2497872080_win_x64.exe"
    installer_path = Path("C:/temp/redshift_install.exe")
    installer_path.parent.mkdir(parents=True, exist_ok=True)
    print("Installing Redshift...")
    download_from_s3(s3_key, installer_path)
    # InstallBuilder with Maya plugin components enabled
    run(
        [
            "powershell",
            "-Command",
            f'Start-Process "{installer_path}" -ArgumentList "--mode","unattended","--enable-components","MayaGroup,PluginMaya2025,PluginMaya2026" -Wait -NoNewWindow',
        ]
    )
    installer_path.unlink(missing_ok=True)

    # Register Redshift with each Maya version
    for ver in ["2025", "2026"]:
        maya_env_dir = Path(f"C:/Users/Default/Documents/maya/{ver}")
        maya_env_dir.mkdir(parents=True, exist_ok=True)
        maya_env_file = maya_env_dir / "Maya.env"
        if not maya_env_file.exists():
            maya_env_file.touch()
        # Run the registration tool
        reg_tool = redshift_root / "Tools" / "Redshift4MayaEnv.exe"
        if reg_tool.exists():
            run([str(reg_tool), str(maya_env_file), str(redshift_root), ver])
        # Copy renderer descriptor
        renderer_xml = (
            redshift_root / "Plugins" / "Maya" / "Common" / "rendererDesc" / "redshiftRenderer.xml"
        )
        maya_renderer_dir = Path(f"C:/Program Files/Autodesk/Maya{ver}/bin/rendererDesc")
        if renderer_xml.exists() and maya_renderer_dir.exists():
            run(
                [
                    "powershell",
                    "-Command",
                    f'Copy-Item "{renderer_xml}" "{maya_renderer_dir}" -Force',
                ]
            )


def _register_pywin32() -> None:
    """Register pywin32 DLLs so child processes (mayapy) can load win32file.

    Mirrors the pattern used by deadline-cloud-for-3ds-max setup-runner.
    """
    print("Running pywin32 post-install script...")
    env_root = Path(sys.executable).parent.parent
    postinstall = (
        env_root / "Lib" / "site-packages" / "win32" / "scripts" / "pywin32_postinstall.py"
    )
    if postinstall.exists():
        run([sys.executable, str(postinstall), "-install"])
        return

    # Fallback: copy DLLs manually
    print(f"pywin32_postinstall.py not found at {postinstall}, copying DLLs manually...")
    pywin32_system32 = env_root / "Lib" / "site-packages" / "pywin32_system32"
    if not pywin32_system32.exists():
        print("ERROR: pywin32_system32 directory not found")
        sys.exit(1)

    for dll in pywin32_system32.glob("*.dll"):
        dest = Path("C:/Windows/System32") / dll.name
        if not dest.exists():
            print(f"Copying {dll.name} to System32")
            shutil.copy2(str(dll), str(dest))


def setup_windows(maya_versions: Sequence[str], renderers: Sequence[str]) -> None:
    _clean_stale_locks(maya_versions)

    # Remove stale mayapy copies from previous runs that break PATH resolution
    for stale in [Path("C:/Windows/mayapy.exe"), Path("C:/Windows/mayapy.cmd")]:
        if stale.exists():
            stale.unlink(missing_ok=True)

    # Ensure 7-Zip is available (needed to extract Maya .7z installer)
    seven_zip = Path("C:/Program Files/7-Zip/7z.exe")
    if not seven_zip.exists():
        print("Installing 7-Zip...")
        installer_path = Path("C:/temp/7z-install.exe")
        installer_path.parent.mkdir(parents=True, exist_ok=True)
        download_from_s3("tools/7z2408-x64.exe", installer_path)
        verify_checksum(
            installer_path, "67cb9d3452c9dd974b04f4a5fd842dbcba8184f2344ff72e3662d7cdb68b099b"
        )
        run(
            [
                "powershell",
                "-Command",
                f"Start-Process '{installer_path}' -ArgumentList '/S' -Wait",
            ]
        )

    for version in maya_versions:
        _install_maya_windows(version)

    # Install the submitter and deps into each Maya version
    for version in maya_versions:
        maya_dir = Path(f"C:/Program Files/Autodesk/Maya{version}")
        mayapy_exe = maya_dir / "bin" / "mayapy.exe"

        print(f"Installing submitter for Maya {version}...")
        run(["hatch", "run", "install", "--maya-version", version])

        print("Cleanup stale deadline, deadline-job-attachement if any for a clean environment")
        run(
            [
                str(mayapy_exe),
                "-m",
                "pip",
                "uninstall",
                "-y",
                "deadline",
                "deadline-job-attachments",
            ],
            check=False,
        )

        print(f"Installing integ test dependencies for Maya {version}...")
        run(
            [
                str(mayapy_exe),
                "-m",
                "pip",
                "install",
                "-r",
                "requirements-integ-testing.txt",
                "-r",
                "requirements-testing.txt",
            ]
        )

        run([str(mayapy_exe), "-m", "pip", "install", "."])

    # Renderer installers for Windows are not yet in S3. Surface a clear message
    # rather than silently skipping so CI doesn't falsely pass renderer tests.
    # Install renderers on Windows
    if "vray" in renderers:
        for version in maya_versions:
            _install_vray_windows(version)
    if "mtoa" in renderers:
        for version in maya_versions:
            _install_mtoa_windows(version)
    if "redshift" in renderers:
        _install_redshift_windows()

    _register_pywin32()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup Maya test environment")
    parser.add_argument(
        "--versions", nargs="+", required=True, help="Maya versions to install (e.g., 2025 2026)"
    )
    parser.add_argument(
        "--renderers",
        nargs="*",
        default=[],
        choices=SUPPORTED_RENDERERS,
        help=(
            "Third-party renderers to install alongside Maya "
            "(currently supported on Linux only)."
        ),
    )
    args = parser.parse_args()

    maya_versions: list[str] = args.versions
    renderers = list(dict.fromkeys(args.renderers))  # dedupe, preserve order

    system = platform.system()
    if system not in PLATFORM_TO_KEY:
        print(f"ERROR: Unsupported platform: {system}")
        sys.exit(1)
    plat_key = PLATFORM_TO_KEY[system]

    validate_versions(maya_versions)

    maya_versions = select_installable_versions(maya_versions, plat_key, system)
    if not maya_versions:
        print(f"Nothing to set up: no requested Maya version has a {system} installer.")
        sys.exit(0)

    print(
        f"Setting up {system} with Maya {', '.join(maya_versions)}"
        + (f" and renderers {', '.join(renderers)}" if renderers else "")
    )

    if system == "Linux":
        setup_linux(maya_versions, renderers)
    elif system == "Windows":
        setup_windows(maya_versions, renderers)

    print("Setup complete!")
