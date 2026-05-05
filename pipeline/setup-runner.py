# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#!/usr/bin/env python3
"""Setup runner for Maya integration tests in CodeBuild.

Currently supports Linux only with Maya 2025 and 2026.
TODO: Add Windows and macOS support once installers are uploaded to S3.
TODO: Add third-party renderer (Arnold, V-Ray, Redshift) installation.
"""
import argparse
import hashlib
import os
import platform
import shlex
import subprocess
import sys
import time
from pathlib import Path

import boto3
from botocore.config import Config

MAYA_VERSION_CONFIG = {
    "2025": {
        "python": "3.11",
        "installer": {
            "linux": "Autodesk_MayaIO_2025_3_ML_Linux_64bit.run",
        },
    },
    "2026": {
        "python": "3.11",
        "installer": {
            "linux": "Autodesk_MayaIO_2026_3_Update_Linux.run",
        },
    },
}

MAYA_CHECKSUMS = {
    "2025": {
        "linux": "a4c46a576aea91e1e52a06355b413f98000b884feb8eb1349a7459990e212395",
    },
    "2026": {
        "linux": "b17b0700933e8e4329939da38cc52c93ed483a93b02e9fa78031fddae763c8e8",
    },
}


def run(cmd, check=True, cwd=None):
    print(f"Running: {cmd if isinstance(cmd, str) else shlex.join(cmd)}")
    result = subprocess.run(cmd, check=False, cwd=cwd)
    if check and result.returncode != 0:
        sys.exit(result.returncode)
    return result


def download_from_s3(s3_path, local_path):
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


def verify_checksum(file_path, expected_checksum):
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


def setup_linux(maya_versions):
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
            "libXp",
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

    for version in maya_versions:
        config = MAYA_VERSION_CONFIG[version]
        installer_name = config["installer"]["linux"]
        maya_dir = Path(f"/opt/Autodesk/mayaio/{version}")
        maya_marker = maya_dir / ".installed"

        if maya_marker.exists():
            print(f"Maya {version} already installed")
            continue

        lock_file = Path(f"/tmp/maya-{version}.lock")
        if lock_file.exists():
            print(f"Waiting for concurrent Maya {version} install...")
            for _ in range(120):
                time.sleep(1)
                if maya_marker.exists():
                    break
            continue

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
                # List what was installed for debugging
                run(["find", str(maya_dir), "-name", "mayapy", "-o", "-name", "maya"], check=False)
                sys.exit(1)

            installer_path.unlink(missing_ok=True)
            run(["rm", "-rf", str(extract_dir)], check=False)
        finally:
            lock_file.unlink(missing_ok=True)

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


# TODO: Add setup_windows() and setup_macos() once installers are available in S3.
# See deadline-cloud-for-blender and deadline-cloud-for-houdini setup-runner.py for patterns.


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup Maya test environment")
    parser.add_argument("--versions", nargs="+", help="Maya versions to install (e.g., 2025 2026)")
    args = parser.parse_args()

    maya_versions = args.versions if args.versions else list(MAYA_VERSION_CONFIG.keys())

    system = platform.system()
    print(f"Setting up {system} with Maya {', '.join(maya_versions)}")

    # Validate versions
    for v in maya_versions:
        if v not in MAYA_VERSION_CONFIG:
            print(f"ERROR: Unsupported Maya version: {v}")
            print(f"Supported versions: {list(MAYA_VERSION_CONFIG.keys())}")
            sys.exit(1)
        if system.lower() not in MAYA_VERSION_CONFIG[v].get("installer", {}):
            print(f"ERROR: No {system} installer configured for Maya {v}")
            sys.exit(1)

    if system == "Linux":
        setup_linux(maya_versions)
    else:
        print(f"ERROR: {system} is not yet supported for Maya CI.")
        print("Only Linux is currently supported. See TODO in this file.")
        sys.exit(1)

    print("Setup complete!")
