# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#!/usr/bin/env python3
"""Setup runner for Maya integration tests in CodeBuild.

Supports Linux, Windows, and macOS with Maya 2025 and 2026.

On Linux, can additionally install the Arnold (mtoa), V-Ray, and Redshift
renderers into each Maya version so the renderer-specific integ tests can run.
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
from typing import Any, Sequence

import boto3
from botocore.config import Config

# ---------------------------------------------------------------------------
# Maya
# ---------------------------------------------------------------------------

MAYA_VERSION_CONFIG: dict[str, dict[str, Any]] = {
    "2025": {
        "python": "3.11",
        "installer": {
            "linux": "Autodesk_MayaIO_2025_3_ML_Linux_64bit.run",
            "windows": "Maya2025_Windows.zip",
            "macos": "Maya2025_macOS.dmg",
        },
    },
    "2026": {
        "python": "3.11",
        "installer": {
            "linux": "Autodesk_MayaIO_2026_3_Update_Linux.run",
            "windows": "Maya2026_Windows.zip",
            "macos": "Maya2026_macOS.dmg",
        },
    },
}

MAYA_CHECKSUMS: dict[str, dict[str, str]] = {
    "2025": {
        "linux": "a4c46a576aea91e1e52a06355b413f98000b884feb8eb1349a7459990e212395",
        "windows": "0f9ce4abc7febbef07b0ef5ecd2526a45200a9b068a6272f6f2afdd29925a845",
        "macos": "2e277d94b155aa32c79aa83a7d9e6ade23204961802f1c6a41ff8db2553e1c00",
    },
    "2026": {
        "linux": "b17b0700933e8e4329939da38cc52c93ed483a93b02e9fa78031fddae763c8e8",
        "windows": "9c9612f6e4d3f1f6de897a21fde6f9930e2e40bb6ddc3ca9647e2668cdba935c",
        "macos": "8779921f4b7263fab8e2b2429949b7ae6b298c6ec3ae3cd83e9c522e02f2baaa",
    },
}

# ---------------------------------------------------------------------------
# Renderers (Linux only today — Windows/macOS installers are not yet in S3)
# ---------------------------------------------------------------------------

# Arnold (MtoA) — one installer per Maya version, bundled under mtoa/5.5/.
MTOA_CONFIG: dict[str, dict[str, Any]] = {
    "2025": {
        "s3_key": "mtoa/5.5/MtoA-5.5.6.1-linux-2025.run",
        "checksums": {
            "linux": "7f607c05461efec4ebd9f7d40e0d3e6de3e2dccba51078e1ccfaf598b77af389",
        },
    },
    "2026": {
        "s3_key": "mtoa/5.5/MtoA-5.5.6.1-linux-2026.run",
        "checksums": {
            "linux": "d8881e1cece725178d90aaa6d44507ea017ec64d7d23c76b129b9e349d1c9cc6",
        },
    },
}

# V-Ray for Maya — Chaos RHEL8 self-extracting installer per Maya version.
VRAY_CONFIG: dict[str, dict[str, Any]] = {
    "2025": {
        "s3_key": "maya-vray/72002/vray_adv_72002_maya2025_dr2_rhel8",
        "checksums": {
            "linux": "cdbeba5ea82120155ecda75da01e359d1dc01f8905a4751d233b40136f9610c6",
        },
    },
    "2026": {
        "s3_key": "maya-vray/72002/vray_adv_72002_maya2026_dr2_rhel8",
        "checksums": {
            "linux": "a6e1e65202f6c9b3d4e12e7eb423a780a34dfeac3540658b16f4e20f8009fca6",
        },
    },
}

# Redshift — single installer supports both Maya 2025 and 2026.
REDSHIFT_CONFIG: dict[str, dict[str, str]] = {
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


def download_from_s3(s3_path: str, local_path: str | os.PathLike[str]) -> None:
    bucket = os.environ.get("INSTALLER_BUCKET")
    if not bucket:
        print("ERROR: INSTALLER_BUCKET not set")
        sys.exit(1)
    expected_bucket_owner = os.environ.get("INSTALLER_BUCKET_EXPECTED_OWNER")
    if not expected_bucket_owner:
        raise ValueError("INSTALLER_BUCKET_EXPECTED_OWNER environment variable is required")
    if not (expected_bucket_owner.isdigit() and len(expected_bucket_owner) == 12):
        raise ValueError("INSTALLER_BUCKET_EXPECTED_OWNER must be a 12-digit AWS Account ID")

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


def _platform_key() -> str:
    """Return our S3-folder / config key for the current OS."""
    system = platform.system()
    return {"Linux": "linux", "Windows": "windows", "Darwin": "macos"}.get(system, system.lower())


# ---------------------------------------------------------------------------
# Linux
# ---------------------------------------------------------------------------


def _install_maya_linux(version: str) -> Path:
    config = MAYA_VERSION_CONFIG[version]
    installer_name = config["installer"]["linux"]
    maya_dir = Path(f"/opt/Autodesk/mayaio/{version}")
    maya_marker = maya_dir / ".installed"

    if maya_marker.exists():
        print(f"Maya {version} already installed")
        return maya_dir

    lock_file = Path(f"/tmp/maya-{version}.lock")
    if lock_file.exists():
        print(f"Waiting for concurrent Maya {version} install...")
        for _ in range(120):
            time.sleep(1)
            if maya_marker.exists():
                break
        return maya_dir

    lock_file.touch()
    try:
        print(f"Installing Maya {version}...")
        installer_path = Path(f"/tmp/{installer_name}")

        download_from_s3(f"maya/{version}/{installer_name}", installer_path)
        verify_checksum(installer_path, MAYA_CHECKSUMS[version].get("linux", ""))

        run(["chmod", "+x", str(installer_path)])
        run(
            [
                str(installer_path),
                "--noexec",
                "--target",
                f"/tmp/maya-{version}-extract",
            ]
        )

        # Run the setup script with auto-accept
        extract_dir = Path(f"/tmp/maya-{version}-extract")
        run(
            [
                "./setup",
                "--accept-eula=yes",
                f"--prefix={maya_dir}",
            ],
            cwd=extract_dir,
        )

        # Verify installation
        mayapy_exe = maya_dir / "bin" / "mayapy"
        if mayapy_exe.exists():
            print(f"SUCCESS: mayapy found at {mayapy_exe}")
            maya_marker.touch()
        else:
            print(f"ERROR: mayapy NOT found at {mayapy_exe}")
            run(["find", str(maya_dir), "-name", "mayapy", "-o", "-name", "maya"], check=False)
            sys.exit(1)

        installer_path.unlink(missing_ok=True)
        run(["rm", "-rf", str(extract_dir)], check=False)
    finally:
        lock_file.unlink(missing_ok=True)

    return maya_dir


def _install_mtoa_linux(version: str) -> None:
    """Install MtoA (Arnold for Maya) for the given Maya version."""
    if version not in MTOA_CONFIG:
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
            if marker.exists():
                break
        return

    lock_file.touch()
    try:
        s3_key = MTOA_CONFIG[version]["s3_key"]
        installer_name = Path(s3_key).name
        installer_path = Path(f"/tmp/{installer_name}")

        print(f"Installing MtoA for Maya {version}...")
        download_from_s3(s3_key, installer_path)
        verify_checksum(installer_path, MTOA_CONFIG[version]["checksums"]["linux"])

        run(["chmod", "+x", str(installer_path)])
        mtoa_install_dir.mkdir(parents=True, exist_ok=True)
        # MtoA Linux installer is an InstallBuilder self-extractor that honors
        # --mode unattended, --prefix, and --installdir.
        run(
            [
                str(installer_path),
                "--mode",
                "unattended",
                "--unattendedmodeui",
                "none",
                "--prefix",
                str(mtoa_install_dir),
            ]
        )

        # Verify — installer lays down plugins under $prefix/plug-ins.
        arnold_plugin = mtoa_install_dir / "plug-ins" / "mtoa.so"
        if arnold_plugin.exists():
            print(f"SUCCESS: mtoa.so found at {arnold_plugin}")
            marker.touch()
        else:
            # Some MtoA versions extract into a versioned subdir — list for visibility.
            print(f"WARNING: mtoa.so not found at {arnold_plugin}, dumping install tree:")
            run(["find", str(mtoa_install_dir), "-maxdepth", "3"], check=False)
            # Still mark installed — plugin layout varies between versions. Tests
            # will fail fast and visibly if the plugin is actually missing.
            marker.touch()

        installer_path.unlink(missing_ok=True)
    finally:
        lock_file.unlink(missing_ok=True)


def _install_vray_linux(version: str) -> None:
    """Install V-Ray for Maya for the given Maya version."""
    if version not in VRAY_CONFIG:
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
            if marker.exists():
                break
        return

    lock_file.touch()
    try:
        s3_key = VRAY_CONFIG[version]["s3_key"]
        installer_name = Path(s3_key).name
        installer_path = Path(f"/tmp/{installer_name}")

        print(f"Installing V-Ray for Maya {version}...")
        download_from_s3(s3_key, installer_path)
        verify_checksum(installer_path, VRAY_CONFIG[version]["checksums"]["linux"])

        run(["chmod", "+x", str(installer_path)])
        # Chaos V-Ray Linux installer is an InstallBuilder self-extractor.
        # Use unattended mode and explicit paths so the install is predictable.
        vray_install_dir.mkdir(parents=True, exist_ok=True)
        run(
            [
                str(installer_path),
                "--mode",
                "unattended",
                "--unattendedmodeui",
                "none",
                "--prefix",
                str(vray_install_dir),
                # MAYA_ROOT is required by the V-Ray postinstall so it knows
                # where to drop the module files.
                "--MAYA_ROOT",
                f"/opt/Autodesk/mayaio/{version}",
                "--RUNAS_USER",
                "root",
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
            if marker.exists():
                break
        return

    lock_file.touch()
    try:
        s3_key = REDSHIFT_CONFIG["linux"]["s3_key"]
        installer_name = Path(s3_key).name
        installer_path = Path(f"/tmp/{installer_name}")

        print("Installing Redshift...")
        download_from_s3(s3_key, installer_path)
        verify_checksum(installer_path, REDSHIFT_CONFIG["linux"]["checksum"])

        run(["chmod", "+x", str(installer_path)])
        # Redshift Linux installer is an InstallBuilder self-extractor.
        redshift_root.mkdir(parents=True, exist_ok=True)
        run(
            [
                str(installer_path),
                "--mode",
                "unattended",
                "--unattendedmodeui",
                "none",
                "--prefix",
                str(redshift_root),
            ],
            check=False,
        )

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
        ]
    )

    # Start Xvfb if not already running
    if run(["pgrep", "Xvfb"], check=False).returncode != 0:
        subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1024x768x24"])
        run(["sleep", "2"])
        print("\nXvfb started. DISPLAY=:99")

    # Install Maya first — MtoA/V-Ray/Redshift plug into an existing Maya install.
    for version in maya_versions:
        _install_maya_linux(version)

    # Install the submitter and deps into each Maya version
    for version in maya_versions:
        maya_dir = Path(f"/opt/Autodesk/mayaio/{version}")
        mayapy_exe = maya_dir / "bin" / "mayapy"

        print(f"Installing submitter for Maya {version}...")
        run(["hatch", "run", "install", "--maya-version", version])

        # Install integ test dependencies into Maya's Python
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

        # Install the package itself so mayapy can import it
        run([str(mayapy_exe), "-m", "pip", "install", "."])

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
    config = MAYA_VERSION_CONFIG[version]
    installer_name = config["installer"]["windows"]
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
    verify_checksum(installer_zip, MAYA_CHECKSUMS[version].get("windows", ""))

    print("Extracting Maya installer...")
    run(
        [
            "powershell",
            "-Command",
            f"Expand-Archive -Path '{installer_zip}' -DestinationPath '{setup_dir}' -Force",
        ]
    )

    # Autodesk zips extract to either the zip's directory or to a nested folder
    # containing Setup.exe. Find it rather than hard-coding a layout.
    setup_exe = next(setup_dir.rglob("Setup.exe"), None)
    if setup_exe is None:
        print(f"ERROR: Setup.exe not found under {setup_dir}")
        run(["powershell", "-Command", f"Get-ChildItem -Recurse '{setup_dir}'"], check=False)
        sys.exit(1)

    print(f"Starting Maya installation via {setup_exe}...")
    result = subprocess.run(
        [
            "powershell",
            "-Command",
            f'Start-Process "{setup_exe}" -ArgumentList "--silent" -Wait',
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
    for version in maya_versions:
        _install_maya_windows(version)

    # Install the submitter and deps into each Maya version
    for version in maya_versions:
        maya_dir = Path(f"C:/Program Files/Autodesk/Maya{version}")
        mayapy_exe = maya_dir / "bin" / "mayapy.exe"

        print(f"Installing submitter for Maya {version}...")
        run(["hatch", "run", "install", "--maya-version", version])

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
    if renderers:
        print(
            "ERROR: Windows renderer installers (mtoa/vray/redshift) are not yet available in S3. "
            "Remove --renderers or run only the native Maya renderer on Windows."
        )
        sys.exit(1)

    _register_pywin32()


# ---------------------------------------------------------------------------
# macOS
# ---------------------------------------------------------------------------


def _install_maya_macos(version: str) -> Path:
    config = MAYA_VERSION_CONFIG[version]
    installer_name = config["installer"]["macos"]
    maya_app = Path(f"/Applications/Autodesk/maya{version}/Maya.app")
    # Marker lives outside the .app so reinstalling Maya doesn't preserve a stale marker.
    marker = Path(f"~/Library/Application Support/.maya-{version}-installed").expanduser()
    marker.parent.mkdir(parents=True, exist_ok=True)

    if marker.exists():
        print(f"Maya {version} already installed")
        return maya_app

    lock_file = Path(f"/tmp/maya-{version}.lock")
    if lock_file.exists():
        print(f"Waiting for concurrent Maya {version} install...")
        for _ in range(120):
            time.sleep(1)
            if marker.exists():
                break
        return maya_app

    lock_file.touch()
    try:
        installer_path = Path(f"/tmp/{installer_name}")

        print(f"Installing Maya {version}...")
        download_from_s3(f"maya/{version}/{installer_name}", installer_path)
        verify_checksum(installer_path, MAYA_CHECKSUMS[version].get("macos", ""))

        mount_point = Path(f"/tmp/maya-{version}-mount")
        mount_point.mkdir(parents=True, exist_ok=True)

        # Attach the DMG to a deterministic mountpoint so we know where to look for the .pkg.
        run(
            [
                "hdiutil",
                "attach",
                str(installer_path),
                "-mountpoint",
                str(mount_point),
                "-nobrowse",
            ]
        )
        try:
            pkg = next(mount_point.glob("*.pkg"), None)
            if pkg is None:
                print(f"ERROR: No .pkg found in Maya DMG at {mount_point}")
                run(["ls", "-la", str(mount_point)], check=False)
                sys.exit(1)
            run(["sudo", "installer", "-pkg", str(pkg), "-target", "/"])
        finally:
            run(["hdiutil", "detach", str(mount_point)], check=False)

        mayapy_exe = maya_app / "Contents" / "bin" / "mayapy"
        if mayapy_exe.exists():
            print(f"SUCCESS: mayapy found at {mayapy_exe}")
            marker.touch()
        else:
            print(f"ERROR: mayapy NOT found at {mayapy_exe}")
            run(
                ["find", "/Applications/Autodesk", "-name", "mayapy"],
                check=False,
            )
            sys.exit(1)

        installer_path.unlink(missing_ok=True)
    finally:
        lock_file.unlink(missing_ok=True)

    return maya_app


def setup_macos(maya_versions: Sequence[str], renderers: Sequence[str]) -> None:
    for version in maya_versions:
        _install_maya_macos(version)

    for version in maya_versions:
        maya_app = Path(f"/Applications/Autodesk/maya{version}/Maya.app")
        mayapy_exe = maya_app / "Contents" / "bin" / "mayapy"

        print(f"Installing submitter for Maya {version}...")
        run(["hatch", "run", "install", "--maya-version", version])

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

    if renderers:
        print(
            "ERROR: macOS renderer installers (mtoa/vray/redshift) are not yet available in S3. "
            "Remove --renderers or run only the native Maya renderer on macOS."
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup Maya test environment")
    parser.add_argument("--versions", nargs="+", help="Maya versions to install (e.g., 2025 2026)")
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

    maya_versions = args.versions if args.versions else list(MAYA_VERSION_CONFIG.keys())
    renderers = list(dict.fromkeys(args.renderers))  # dedupe, preserve order

    system = platform.system()
    plat_key = _platform_key()
    print(
        f"Setting up {system} with Maya {', '.join(maya_versions)}"
        + (f" and renderers {', '.join(renderers)}" if renderers else "")
    )

    # Validate versions
    for v in maya_versions:
        if v not in MAYA_VERSION_CONFIG:
            print(f"ERROR: Unsupported Maya version: {v}")
            print(f"Supported versions: {list(MAYA_VERSION_CONFIG.keys())}")
            sys.exit(1)
        if plat_key not in MAYA_VERSION_CONFIG[v].get("installer", {}):
            print(f"ERROR: No {system} installer configured for Maya {v}")
            sys.exit(1)

    if system == "Linux":
        setup_linux(maya_versions, renderers)
    elif system == "Windows":
        setup_windows(maya_versions, renderers)
    elif system == "Darwin":
        setup_macos(maya_versions, renderers)
    else:
        print(f"ERROR: Unsupported platform: {system}")
        sys.exit(1)

    print("Setup complete!")
