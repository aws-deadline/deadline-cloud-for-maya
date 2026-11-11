# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#!/usr/bin/env python3
"""Setup runner for Maya integration tests in CodeBuild.

Supports Linux and Windows with Maya 2025, 2026 and 2027.

Installs the Arnold (MtoA), V-Ray, and Redshift renderers into each Maya
version so the renderer-specific integ tests can run.
Use --renderers to select which renderers to install (default: none).

On Windows, installs the pywin32 support DLLs so child processes (mayapy) can
load win32file. This mirrors the pattern used by deadline-cloud-for-3ds-max.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import Callable, Sequence, TypedDict

import boto3
from botocore.config import Config

# ---------------------------------------------------------------------------
# Configuration types
# ---------------------------------------------------------------------------


class InstallerPaths(TypedDict):
    linux: str
    windows: str


class MayaVersionConfig(TypedDict):
    python: str
    installer: InstallerPaths


class MayaChecksums(TypedDict):
    linux: str
    windows: str


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
    "2027": {
        "python": "3.13",
        "installer": {
            "linux": "Autodesk_MayaIO_2027_2_Update_Linux.run",
            "windows": "Maya2027_Windows.zip",
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
    "2027": {
        "linux": "eac310135486b2a33e64223721dc451ffca294444880e3a94a96bcc48a4efe9e",
        "windows": "5380c20e1ab2321776c000e245819b36f33697918ee2cc344efb3ac22e1ead62",
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
    "2027": {
        "s3_key": "mtoa/5.6.3/MtoA-5.6.3-linux-2027.run",
        "checksum": "a745b3ef022a1fe41f1d1b90597af6df92deaf2dc49f63593705a96a0f3e6ed1",
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
    "2027": {
        "s3_key": "maya-vray/74004/vray_74004_maya2027_dr2_rhel8",
        "checksum": "67dab04ce9f71a23d0fcbfd76bdd096b7fc90863c47e86eae7824a4464dff2cf",
    },
}

# Redshift — single installer supports Maya 2025, 2026 and 2027.
REDSHIFT_PLATFORM_CONFIG: dict[str, RedshiftPlatformConfig] = {
    "linux": {
        "s3_key": "redshift/2026/redshift_2026.8.1_2741261432_linux_x64.run",
        "checksum": "d653b210ebd7e51e1ceac8795f385fa0204cc8fde38496a7c92b02c97d384e1f",
    },
}

SUPPORTED_RENDERERS: tuple[str, ...] = ("mtoa", "vray", "redshift")

# Bundled SONAMEs to delete per Maya version, so ld.so resolves them from the host. E.g.
# Maya 2027's libfreetype statically links libpng 1.6.55 and exports its symbols, which
# collide with the host's libpng16.so.16.
BUNDLED_SONAMES_TO_DROP: dict[str, tuple[str, ...]] = {
    "2027": ("libfreetype.so.6",),
}

# Adaptor dispatchers live here so run-integ-tests.py can put them ahead of the hatch
# env's console scripts on PATH.
ADAPTOR_DISPATCH_DIR = Path("/usr/local/maya-adaptor-bin")


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


# ---------------------------------------------------------------------------
# Linux
# ---------------------------------------------------------------------------


def _host_provided_sonames() -> set[str]:
    """SONAMEs the host's dynamic linker can already resolve."""
    result = subprocess.run(["ldconfig", "-p"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"ERROR: ldconfig -p failed (rc={result.returncode}): {result.stderr.strip()}")
        sys.exit(1)
    return {line.split()[0] for line in result.stdout.splitlines() if "=>" in line}


def _link_sonames(lib_dir: Path) -> None:
    """Add the SONAME symlinks the RPM does not ship, skipping host-provided ones.

    Maya 2025 installs lib/libssl.so.1.1.1k, whose SONAME is libssl.so.1.1, with no
    link at that name, so ld.so cannot find it. lib_dir outranks /lib64, so linking a
    SONAME the host already provides would override a working library instead.
    """

    def existing_symlinks() -> set[str]:
        return {p.name for p in lib_dir.iterdir() if p.is_symlink()}

    shipped_symlinks = existing_symlinks()
    run(["ldconfig", "-n", str(lib_dir)], check=False)
    created_symlinks = existing_symlinks() - shipped_symlinks

    host_provides = _host_provided_sonames()
    for name in sorted(created_symlinks):
        link = lib_dir / name
        if name in host_provides:
            link.unlink()
        else:
            print(f"Linked {name} -> {link.readlink()}")


def _drop_bundled_sonames(lib_dir: Path, sonames: Sequence[str]) -> None:
    """Delete the named SONAMEs from lib_dir, along with the links resolving to them."""
    for soname in sonames:
        entry = lib_dir / soname
        if not entry.exists():
            print(f"WARNING: {soname} is not in {lib_dir}, nothing to drop")
            continue
        target = entry.resolve()
        if lib_dir.resolve() not in target.parents:
            print(f"WARNING: {soname} resolves outside {lib_dir}, not dropping")
            continue
        for path in sorted(lib_dir.glob("*.so*")):
            if path.is_symlink() and path.resolve() == target:
                path.unlink()
        target.unlink(missing_ok=True)
        print(f"Dropped {soname}; ld.so will resolve it from the host")


def _find_mayapy(maya_dir: Path) -> Path:
    """Locate mayapy; the directory name inside an installed tree varies by version."""
    result = subprocess.run(
        ["find", str(maya_dir), "-name", "mayapy", "-type", "f"],
        capture_output=True,
        text=True,
        check=False,
    )
    mayapy_exe = None
    if result.stdout.strip():
        mayapy_exe = Path(result.stdout.strip().split("\n")[0])
    if not mayapy_exe or not mayapy_exe.exists():
        print(f"ERROR: mayapy NOT found under {maya_dir}")
        run(["find", str(maya_dir), "-maxdepth", "5", "-type", "f", "-name", "maya*"], check=False)
        sys.exit(1)
    return mayapy_exe


def _verify_maya_loads(mayapy_exe: Path) -> None:
    """Exit unless Maya's binaries can load their shared libraries.

    mayapy runs even when they cannot, so probe Render instead. Render never exits 0, so
    judge on the usage banner, which a binary that failed to load never prints.
    """
    render_exe = mayapy_exe.parent / "Render"
    probe = subprocess.run([str(render_exe), "-help"], capture_output=True, check=False)
    output = probe.stdout + probe.stderr
    if b"Usage:" not in output:
        print(f"ERROR: {render_exe} did not run; it cannot load its shared libraries")
        print(output.decode("utf-8", errors="replace"))
        sys.exit(1)


def _install_maya_linux(version: str) -> Path:
    config = MAYA_YEAR_TO_CONFIG[version]
    installer_name = config["installer"]["linux"]
    maya_dir = Path(f"/opt/Autodesk/mayaio/{version}")

    marker = maya_dir / ".installed"
    if marker.exists():
        print(f"Maya {version} already installed")
        return maya_dir

    lock_file = Path(f"/tmp/maya-{version}.lock")
    if lock_file.exists():
        print(f"Waiting for concurrent Maya {version} install...")
        for _ in range(120):
            time.sleep(1)
            if marker.exists():
                break
        return maya_dir

    lock_file.touch()
    try:
        if maya_dir.exists():
            print(f"Reinstalling Maya {version}: no verified install marker")
            run(["rm", "-rf", str(maya_dir)], check=False)

        print(f"Installing Maya {version}...")
        installer_path = Path(f"/tmp/{installer_name}")

        download_from_s3(f"maya/{version}/{installer_name}", installer_path)
        verify_checksum(installer_path, MAYA_YEAR_TO_CHECKSUMS[version]["linux"])

        run(["chmod", "+x", str(installer_path)])
        # Extract to /opt (not /tmp) and clean any stale dir from prior runs
        extract_dir = Path(f"/opt/maya-{version}-extract")
        if extract_dir.exists():
            run(["rm", "-rf", str(extract_dir)], check=False)
        extract_dir.mkdir(parents=True, exist_ok=True)

        # --tar extracts without running the stub's interactive prompts.
        print("Extracting installer (this may take a moment)...")
        run([str(installer_path), "--tar", "xf"], cwd=extract_dir)

        rpms = list(extract_dir.rglob("*.rpm"))
        if not rpms:
            print(f"ERROR: No RPM found in {extract_dir}")
            run(["ls", "-la", str(extract_dir)], check=False)
            sys.exit(1)
        rpm_path = rpms[0].resolve()

        # Install rather than unpack: %post creates bin/maya -> maya<version> and the
        # /usr/local/bin links, which rpm2cpio silently skips.
        #
        # --prefix replaces the package's declared Prefix (/usr) rather than prepending,
        # so the trailing /usr keeps the tree at <maya_dir>/usr/autodesk/mayaIO<version>.
        maya_dir.mkdir(parents=True, exist_ok=True)
        run(["rpm", "-Uvh", "--force", f"--prefix={maya_dir}/usr", str(rpm_path)])

        mayapy_exe = _find_mayapy(maya_dir)
        lib_dir = mayapy_exe.parent.parent / "lib"

        _link_sonames(lib_dir)
        _drop_bundled_sonames(lib_dir, BUNDLED_SONAMES_TO_DROP.get(version, ()))

        _verify_maya_loads(mayapy_exe)
        print(f"SUCCESS: Maya {version} installed and loadable ({mayapy_exe})")
        marker.touch()

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
        # MtoA is a Makeself archive. Extract it, then unpack the payload.
        extract_tmp = Path(f"/tmp/mtoa-{version}-extract")
        if extract_tmp.exists():
            run(["rm", "-rf", str(extract_tmp)], check=False)
        run([str(installer_path), "--noexec", "--target", str(extract_tmp)])
        # MtoA 5.5.x shipped the payload as a .zip; 5.6.x ships package.tgz.
        pkg = next(extract_tmp.glob("*.zip"), None) or next(extract_tmp.glob("*.tgz"), None)
        if pkg is None:
            print(f"ERROR: No .zip or .tgz payload found in {extract_tmp}")
            run(["ls", "-la", str(extract_tmp)], check=False)
            sys.exit(1)
        if pkg.suffix == ".zip":
            run(["unzip", "-qo", str(pkg), "-d", str(mtoa_install_dir)])
        else:
            run(["tar", "-xzf", str(pkg), "-C", str(mtoa_install_dir)])
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
        vray_install_dir.mkdir(parents=True, exist_ok=True)
        # -unpackInstall as a separate argument, unpacking into the cwd, as the Conda
        # recipes invoke it for every Maya version. V-Ray 7.40.04 silently unpacks
        # nothing given the equals-joined form that worked for 7.2.
        run([str(installer_path), "-unpackInstall", "."], check=False, cwd=vray_install_dir)

        # 7.40.04 no longer ships vray/bin/vray, so verify the plugin Maya loads. It is
        # what the MayaVray Conda recipes patchelf, so this path holds across versions.
        vray_plugin = vray_install_dir / "maya_vray" / "plug-ins" / "vrayformaya.so"
        if not vray_plugin.exists():
            print(f"ERROR: V-Ray install incomplete for Maya {version}: no {vray_plugin}")
            run(["find", str(vray_install_dir), "-maxdepth", "2"], check=False)
            sys.exit(1)
        print(f"SUCCESS: vrayformaya.so found at {vray_plugin}")
        marker.touch()

        installer_path.unlink(missing_ok=True)
    finally:
        lock_file.unlink(missing_ok=True)


def _install_redshift_linux(maya_versions: Sequence[str]) -> None:
    """Install Redshift once; it plugs into every Maya version at runtime."""
    redshift_root = Path("/usr/redshift")
    marker = redshift_root / ".installed"
    # One install serves every Maya version, but only those its payload ships. Require a
    # plugin dir per requested version: reserved-capacity hosts carry a marker from an
    # older Redshift that has no redshift4maya/2027, and would skip the reinstall.
    missing = [v for v in maya_versions if not (redshift_root / "redshift4maya" / v).is_dir()]
    if marker.exists() and not missing:
        print("Redshift already installed")
        return
    if marker.exists():
        print(f"Redshift missing plugins for {', '.join(missing)}; reinstalling")
        marker.unlink(missing_ok=True)

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

        # Verify — redshiftCmdLine lands in $prefix/bin, plus a plugin per Maya version.
        redshift_cmd = redshift_root / "bin" / "redshiftCmdLine"
        still_missing = [
            v for v in maya_versions if not (redshift_root / "redshift4maya" / v).is_dir()
        ]
        if not redshift_cmd.exists() or still_missing:
            print("ERROR: Redshift install incomplete:")
            print(f"  redshiftCmdLine exists={redshift_cmd.exists()}")
            if still_missing:
                print(f"  no redshift4maya plugin for: {', '.join(still_missing)}")
            run(["find", str(redshift_root / "redshift4maya"), "-maxdepth", "1"], check=False)
            sys.exit(1)
        print(f"SUCCESS: redshiftCmdLine found at {redshift_cmd}")
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


def _write_mayapy_dispatcher() -> None:
    """Write /usr/local/bin/mayapy, dispatching to the MAYA_VERSION wrapper.

    Every integ-ci matrix cell exports MAYA_VERSION, so routing through this keeps
    pytest, the adaptor, and its children on the version that cell is testing.
    Fails loudly rather than guessing, since silently using the wrong Maya makes
    tests pass or fail for the wrong reasons.
    """
    dispatcher = Path("/usr/local/bin/mayapy")
    script = """\
        #!/bin/sh
        if [ -z "${MAYA_VERSION:-}" ]; then
            echo "mayapy: MAYA_VERSION is not set, cannot select a Maya version." >&2
            echo "mayapy: installed: $(ls /usr/local/bin/mayapy-* 2>/dev/null | sed 's|.*/mayapy-||' | tr '\\n' ' ')" >&2
            exit 1
        fi
        target="/usr/local/bin/mayapy-${MAYA_VERSION}"
        if [ ! -x "$target" ]; then
            echo "mayapy: no wrapper for Maya ${MAYA_VERSION} at ${target}." >&2
            exit 1
        fi
        exec "$target" "$@"
        """
    dispatcher.write_text(textwrap.dedent(script))
    run(["chmod", "+x", str(dispatcher)])
    print(f"Wrote mayapy dispatcher at {dispatcher}")


def _write_adaptor_dispatchers() -> None:
    """Run the adaptor without Maya's LD_LIBRARY_PATH entries.

    The tests run under mayapy, so every process below inherits Maya's lib directory.
    That is right for the processes that are Maya, and wrong for the one that is not:

        mayapy -m pytest          Maya's python, Maya's lib
         └─ mayapy -m openjd run  Maya's python, Maya's lib
             └─ MayaAdaptor       HOST python, Maya's lib     <- mismatched
                 └─ mayapy        Maya's python, Maya's lib

    `command: MayaAdaptor` resolves through PATH to the hatch env, whose interpreter is
    the host's, and Maya 2027 ships libpython3.13.so.1.0 under the same soname. ld.so
    searches LD_LIBRARY_PATH before the cache, so native imports bound to Maya's copy
    and segfaulted. 2025 and 2026 bundle Python 3.11, so nothing collided.

    We drop only the /opt/Autodesk entries, so anything else on the path stays. The
    mayapy dispatcher later prepends the paths Maya needs to run.
    """
    ADAPTOR_DISPATCH_DIR.mkdir(parents=True, exist_ok=True)
    script = """\
        #!/bin/sh
        clean=$(printf '%s' "${LD_LIBRARY_PATH:-}" | tr ':' '\\n' | grep -v '^/opt/Autodesk/' | paste -sd: -)
        if [ -n "$clean" ]; then
            exec env LD_LIBRARY_PATH="$clean" python -m deadline.maya_adaptor.MayaAdaptor "$@"
        fi
        exec env -u LD_LIBRARY_PATH python -m deadline.maya_adaptor.MayaAdaptor "$@"
        """
    for name in ("MayaAdaptor", "maya-openjd"):
        path = ADAPTOR_DISPATCH_DIR / name
        path.write_text(textwrap.dedent(script))
        run(["chmod", "+x", str(path)])
    print(f"Wrote adaptor dispatchers in {ADAPTOR_DISPATCH_DIR}")


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
            "mesa-libGLU",
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
            # Needed by libQt6XcbQpa.so, which Qt loads for the xcb platform
            "xcb-util-cursor",
            "xcb-util-wm",
            "xcb-util-image",
            "xcb-util-keysyms",
            "xcb-util-renderutil",
            # Maya 2027 needs these beyond 2026's set
            "openjpeg2",
            "libatomic",
            "libpng",
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
        mayapy_exe = _find_mayapy(maya_dir)

        print(f"Installing submitter for Maya {version}...")
        run_with_timeout(
            ["hatch", "run", "install", "--maya-version", version],
            timeout=DEFAULT_CMD_TIMEOUT,
            label=f"hatch install submitter (Maya {version})",
        )

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

        # Per-version wrapper setting MAYA_LOCATION and renderer plugin paths. The
        # `mayapy` dispatcher written after this loop picks one via MAYA_VERSION.
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

        wrapper = Path(f"/usr/local/bin/mayapy-{version}")
        wrapper.write_text(
            f"#!/bin/sh\n"
            f'export MAYA_LOCATION="{mayapy_dir}"\n'
            # ${VAR:+:$VAR} appends the separator only when VAR is set, since an empty
            # element in LD_LIBRARY_PATH means the current directory to ld.so.
            f'export LD_LIBRARY_PATH="{mayapy_dir}/lib${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"\n'
            f'export MAYA_MODULE_PATH="{module_paths}${{MAYA_MODULE_PATH:+:$MAYA_MODULE_PATH}}"\n'
            f'export MAYA_PLUG_IN_PATH="{plugin_paths}${{MAYA_PLUG_IN_PATH:+:$MAYA_PLUG_IN_PATH}}"\n'
            f'export MAYA_SCRIPT_PATH="{script_paths}${{MAYA_SCRIPT_PATH:+:$MAYA_SCRIPT_PATH}}"\n'
            f'export MAYA_RENDER_DESC_PATH="{render_desc_paths}'
            f'${{MAYA_RENDER_DESC_PATH:+:$MAYA_RENDER_DESC_PATH}}"\n'
            f'export REDSHIFT_COREDATAPATH="{redshift_dir}"\n'
            f'exec "{mayapy_exe}" "$@"\n'
        )
        run(["chmod", "+x", str(wrapper)])

    _write_mayapy_dispatcher()
    _write_adaptor_dispatchers()

    # Install requested renderers (always per-Maya-version, except Redshift which
    # is shared across versions).
    if "mtoa" in renderers:
        for version in maya_versions:
            _install_mtoa_linux(version)
    if "vray" in renderers:
        for version in maya_versions:
            _install_vray_linux(version)
    if "redshift" in renderers:
        _install_redshift_linux(maya_versions)


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------


# Upper bound on Maya's Windows installer, from Setup.exe start to the install
# being confirmed finished.
MAYA_SETUP_TIMEOUT = 45 * 60
# How long the install has to look finished before it counts as finished. One
# poll could land between two of the bundle's packages.
MAYA_SETUP_CONFIRM = 30
MAYA_SETUP_POLL = 10
MAYA_SETUP_REPORT_EVERY = 60


def _print_free_space(*paths: str | os.PathLike[str]) -> None:
    for path in paths:
        free_gb = shutil.disk_usage(path).free / 1024**3
        print(f"Free space on {Path(path).anchor or path}: {free_gb:.1f} GB")


def _msi_install_in_progress() -> bool:
    """Whether Windows Installer is running an installation.

    Windows Installer holds the Global\\_MSIExecute mutex for the duration of
    each package install. Any failure to open it other than "not found" (for
    example access denied, which means it exists) counts as busy.
    """
    if sys.platform != "win32":
        return False
    import ctypes

    from ctypes import wintypes

    synchronize = 0x00100000
    error_file_not_found = 2
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenMutexW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.OpenMutexW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel32.OpenMutexW(synchronize, False, "Global\\_MSIExecute")
    if not handle:
        return ctypes.get_last_error() != error_file_not_found
    kernel32.CloseHandle(handle)
    return True


class ProcessInfo(TypedDict):
    Name: str
    ProcessId: int
    ParentProcessId: int
    ExecutablePath: str | None


def _windows_processes() -> list[ProcessInfo] | None:
    """Running processes, or None if they can't be listed."""
    script = (
        "Get-CimInstance Win32_Process | "
        "Select-Object Name,ProcessId,ParentProcessId,ExecutablePath | "
        "ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        data = json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError) as e:
        print(f"WARNING: could not list processes: {e}")
        return None
    return data if isinstance(data, list) else [data]


def _is_install_related(p: ProcessInfo) -> bool:
    path = (p.get("ExecutablePath") or "").lower()
    return "autodesk" in path or "maya_setup" in path or p["Name"].lower() == "msiexec.exe"


def _format_processes(processes: Sequence[ProcessInfo] | None) -> list[str]:
    if processes is None:
        return ["(process list unavailable)"]
    return [
        f"{p['Name']} pid={p['ProcessId']} parent={p['ParentProcessId']} {p.get('ExecutablePath') or ''}"
        for p in processes
    ]


def _print_install_related(processes: Sequence[ProcessInfo] | None) -> None:
    related = None if processes is None else [p for p in processes if _is_install_related(p)]
    for line in _format_processes(related):
        print(f"    {line}")


def _wait_for_maya_setup(
    proc: subprocess.Popen[bytes],
    setup_dir: Path,
    mayapy_exe: Path,
    *,
    list_processes: Callable[[], list[ProcessInfo] | None] = _windows_processes,
    msi_busy: Callable[[], bool] = _msi_install_in_progress,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    """Wait for Maya's Setup.exe install to finish; False if it times out.

    This waits for the installer, not every process it starts. `Start-Process
    -Wait` waits for the whole process tree, and on a runner with a desktop
    session (GitHub-hosted) the installer leaves Autodesk apps running, so that
    never returns.

    The install is finished once, for MAYA_SETUP_CONFIRM seconds in a row,
    Setup.exe has exited, Windows Installer is idle and nothing from the
    extracted package is running. A poll where processes can't be listed
    doesn't count.
    """
    package_dir = str(setup_dir.resolve()).lower()
    start = clock()
    finished_since: float | None = None
    next_report = start
    while True:
        now = clock()
        elapsed = now - start
        exit_code = proc.poll()
        msi_idle = not msi_busy()
        processes = list_processes()
        from_package = (
            None
            if processes is None
            else [
                p
                for p in processes
                if (p.get("ExecutablePath") or "").lower().startswith(package_dir)
            ]
        )

        if exit_code is not None and msi_idle and from_package == []:
            if finished_since is None:
                finished_since = now
            if now - finished_since >= MAYA_SETUP_CONFIRM:
                print(
                    f"Setup.exe exited with code {exit_code}; install finished after {elapsed:.0f}s"
                )
                print("Install-related processes still running (not waited for):")
                _print_install_related(processes)
                return True
        else:
            finished_since = None

        if elapsed >= MAYA_SETUP_TIMEOUT:
            print(f"ERROR: Maya installation did not finish within {MAYA_SETUP_TIMEOUT}s")
            _print_install_related(processes)
            return False

        if now >= next_report:
            state = "running" if exit_code is None else f"exited ({exit_code})"
            print(
                f"[{elapsed:.0f}s] Setup.exe {state}; mayapy.exe"
                f" {'present' if mayapy_exe.exists() else 'absent'};"
                f" Windows Installer {'idle' if msi_idle else 'busy'};"
                f" {shutil.disk_usage(mayapy_exe.anchor or '/').free / 1024**3:.1f} GB free"
                f" on {mayapy_exe.anchor or '/'}"
            )
            _print_install_related(processes)
            next_report = now + MAYA_SETUP_REPORT_EVERY
        sleep(MAYA_SETUP_POLL)


def _dump_maya_setup_diagnostics(since: float) -> None:
    """Print why Autodesk's installer failed, and save its logs and a screenshot.

    Files go to MAYA_SETUP_DIAGNOSTICS_DIR when it's set (the GUI workflow
    uploads it); otherwise they're only listed. Best effort: the installer may
    still be writing, moving or locking any of these files.
    """
    out_dir_env = os.environ.get("MAYA_SETUP_DIAGNOSTICS_DIR")
    out_dir = Path(out_dir_env) if out_dir_env else None
    if out_dir is not None:
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            processes = _format_processes(_windows_processes())
            (out_dir / "processes.txt").write_text("\n".join(processes) + "\n", encoding="utf-8")
        except OSError as e:
            print(f"WARNING: could not save the process list: {e}")
        screenshot = out_dir / "desktop.png"
        script = (
            "Add-Type -AssemblyName System.Windows.Forms, System.Drawing; "
            "$b = [System.Windows.Forms.SystemInformation]::VirtualScreen; "
            "$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height; "
            "[System.Drawing.Graphics]::FromImage($bmp).CopyFromScreen($b.Left, $b.Top, 0, 0, $bmp.Size); "
            f"$bmp.Save('{screenshot}', [System.Drawing.Imaging.ImageFormat]::Png)"
        )
        try:
            run(["powershell", "-NoProfile", "-Command", script], check=False)
        except OSError as e:
            print(f"WARNING: could not take a screenshot: {e}")

    roots = [
        os.environ.get("TEMP"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Autodesk"),
        os.path.join(os.environ.get("PROGRAMDATA", ""), "Autodesk"),
    ]
    logs: list[tuple[float, Path]] = []
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for log in Path(root).rglob("*.log"):
            try:
                stat = log.stat()
            except OSError:
                continue
            if stat.st_mtime >= since and stat.st_size <= 20 * 1024 * 1024:
                logs.append((stat.st_mtime, log))
    logs.sort(reverse=True)
    print(f"Found {len(logs)} log file(s) written since the install started")
    for i, (_, log) in enumerate(logs[:40]):
        print(f"    {log}")
        if out_dir is not None:
            try:
                shutil.copy2(log, out_dir / f"{i:02d}-{log.name}")
            except OSError as e:
                print(f"    WARNING: could not copy it: {e}")

    # ODIS (Autodesk's installer) writes its outcome to Summary.log and the
    # reason a package failed to Install.log.
    odis = Path(os.environ.get("LOCALAPPDATA", "")) / "Autodesk" / "ODIS"
    try:
        summary = odis / "Summary.log"
        if summary.is_file():
            print(f"--- {summary} ---")
            print(summary.read_text(encoding="utf-8", errors="replace").strip())
        install_log = odis / "Install.log"
        if install_log.is_file():
            markers = (
                "Failed to install Package",
                "HandleIntermediateErrors",
                "Disk space",
                "ERROR",
            )
            lines = install_log.read_text(encoding="utf-8", errors="replace").splitlines()
            failures = [line for line in lines if any(m in line for m in markers)]
            print(f"--- failures in {install_log} (last 40 of {len(failures)}) ---")
            for line in failures[-40:]:
                print(line[:400])
    except OSError as e:
        print(f"WARNING: could not read the ODIS logs: {e}")


def _install_maya_windows(version: str) -> Path:
    config = MAYA_YEAR_TO_CONFIG[version]
    installer_name = config["installer"]["windows"]
    maya_dir = Path(f"C:/Program Files/Autodesk/Maya{version}")
    maya_marker = maya_dir / ".installed"

    if maya_marker.exists():
        print(f"Maya {version} already installed")
        return maya_dir

    print(f"Installing Maya {version}...")
    # Staging the installer takes about 12 GB at peak. MAYA_SETUP_WORK_DIR moves
    # it off C:, which Maya itself is installed on; GitHub-hosted runners don't
    # have room for both there.
    setup_dir = Path(os.environ.get("MAYA_SETUP_WORK_DIR") or "C:/maya_setup") / version
    setup_dir.mkdir(parents=True, exist_ok=True)
    installer_zip = setup_dir / installer_name
    _print_free_space(maya_dir.anchor, setup_dir)

    download_from_s3(f"maya/{version}/{installer_name}", installer_zip)
    verify_checksum(installer_zip, MAYA_YEAR_TO_CHECKSUMS[version]["windows"])

    print("Extracting Maya installer...")
    run(
        [
            "powershell",
            "-Command",
            f"Expand-Archive -Path '{installer_zip}' -DestinationPath '{setup_dir}' -Force",
        ]
    )
    installer_zip.unlink()

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
        seven_z.unlink()
    _print_free_space(maya_dir.anchor, setup_dir)

    if setup_exe is None:
        print(f"ERROR: Setup.exe not found under {setup_dir}")
        run(["powershell", "-Command", f"Get-ChildItem -Recurse '{setup_dir}'"], check=False)
        sys.exit(1)

    mayapy_exe = maya_dir / "bin" / "mayapy.exe"
    print(f"Starting Maya installation via {setup_exe}...")
    started_at = time.time()
    # No pipes: Autodesk apps the installer leaves running would inherit them and
    # keep this step's output open.
    proc = subprocess.Popen(
        [str(setup_exe), "-q"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not _wait_for_maya_setup(proc, setup_dir, mayapy_exe):
        proc.kill()
        _dump_maya_setup_diagnostics(started_at)
        sys.exit(1)

    if mayapy_exe.exists():
        print(f"SUCCESS: mayapy.exe found at {mayapy_exe}")
        maya_marker.touch()
    else:
        print(f"ERROR: mayapy.exe NOT found at {mayapy_exe}")
        _dump_maya_setup_diagnostics(started_at)
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
        "2027": "maya-vray/74004/vray_74004_maya2027_dr2_x64.exe",
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
        "2027": "mtoa/5.6.3/MtoA-5.6.3-windows-2027.msi",
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


def _install_redshift_windows(maya_versions: Sequence[str]) -> None:
    """Install Redshift on Windows with Maya plugin registration."""
    redshift_root = Path("C:/Program Files/Maxon Redshift 2026")
    plugins = redshift_root / "Plugins" / "Maya"
    missing = [
        v for v in maya_versions if not (plugins / v / "nt-x86-64" / "redshift4maya.mll").is_file()
    ]
    if not missing:
        print("Redshift already installed")
        return
    print(f"Redshift has no plugin for Maya {', '.join(missing)}; installing")
    s3_key = "redshift/2026/redshift_2026.8.1_2741261432_win_x64.exe"
    installer_path = Path("C:/temp/redshift_install.exe")
    installer_path.parent.mkdir(parents=True, exist_ok=True)
    download_from_s3(s3_key, installer_path)
    components = ",".join(["MayaGroup"] + [f"PluginMaya{v}" for v in maya_versions])
    run(
        [
            "powershell",
            "-Command",
            f'Start-Process "{installer_path}" -ArgumentList "--mode","unattended",'
            f'"--enable-components","{components}" -Wait -NoNewWindow',
        ]
    )
    installer_path.unlink(missing_ok=True)

    # Register Redshift with each Maya version
    for ver in maya_versions:
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
        _install_redshift_windows(maya_versions)

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

    print(
        f"Setting up {system} with Maya {', '.join(maya_versions)}"
        + (f" and renderers {', '.join(renderers)}" if renderers else "")
    )

    # Validate versions
    for v in maya_versions:
        if v not in MAYA_YEAR_TO_CONFIG:
            print(f"ERROR: Unsupported Maya version: {v}")
            print(f"Supported versions: {list(MAYA_YEAR_TO_CONFIG.keys())}")
            sys.exit(1)
        if plat_key not in MAYA_YEAR_TO_CONFIG[v]["installer"]:
            print(f"ERROR: No {system} installer configured for Maya {v}")
            sys.exit(1)

    if system == "Linux":
        setup_linux(maya_versions, renderers)
    elif system == "Windows":
        setup_windows(maya_versions, renderers)

    print("Setup complete!")
