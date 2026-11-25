# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Unit tests for installer/scripts/remove_legacy_maya_module_path.sh.

Installers up to 0.15.15 appended `export MAYA_MODULE_PATH="<frozen value>:<install dir>/"` to the
user's shell startup files. The script removes exactly those lines and nothing else.

Each test runs against every awk implementation found on the PATH (GNU awk, mawk, BusyBox awk and
the BSD awk that macOS ships), by putting the chosen one first on the PATH as `awk`.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX shell script")

SCRIPT = Path(__file__).parents[2] / "installer" / "scripts" / "remove_legacy_maya_module_path.sh"
STARTUP_FILES = [".bashrc", ".bash_profile", ".bash_login", ".profile", ".zshrc", ".zprofile"]
BACKUP_SUFFIX = ".deadline-cloud-for-maya.bak"
CUSTOMER_LINE = 'export MAYA_MODULE_PATH="/studio/modules:$MAYA_MODULE_PATH"'


def _awk_variants() -> list:
    """Returns pytest params of (name, argv prefix) for each awk implementation available."""
    variants = []
    seen = set()
    for name in ["awk", "gawk", "mawk", "original-awk", "nawk"]:
        path = shutil.which(name)
        if path and os.path.realpath(path) not in seen:
            seen.add(os.path.realpath(path))
            variants.append(pytest.param([path], id=name))
    busybox = shutil.which("busybox")
    if busybox and subprocess.run([busybox, "awk", "BEGIN{}"]).returncode == 0:
        variants.append(pytest.param([busybox, "awk"], id="busybox"))
    return variants


@pytest.fixture(params=_awk_variants())
def awk_bin_dir(request, tmp_path_factory) -> Path:
    """A directory containing an `awk` wrapper for one implementation, to put first on the PATH."""
    bin_dir = tmp_path_factory.mktemp("awk-bin")
    wrapper = bin_dir / "awk"
    argv = " ".join(f"'{a}'" for a in request.param)
    wrapper.write_text(f'#!/bin/sh\nexec {argv} "$@"\n')
    wrapper.chmod(0o755)
    return bin_dir


@pytest.fixture
def home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    return home


@pytest.fixture
def run(awk_bin_dir: Path):
    def _run(*args: str, env_home: str | None = None) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["PATH"] = f"{awk_bin_dir}{os.pathsep}{env['PATH']}"
        if env_home is not None:
            env["HOME"] = env_home
        result = subprocess.run(
            ["/bin/sh", str(SCRIPT), *args], env=env, capture_output=True, text=True
        )
        assert result.returncode == 0, result
        return result

    return _run


def _legacy_lines(install_dir: str) -> list[str]:
    """Every form of the line the old installers wrote for this install dir."""
    return [
        f'export MAYA_MODULE_PATH="{install_dir}/"',
        f'export MAYA_MODULE_PATH="{install_dir}"',
        f'export MAYA_MODULE_PATH="/studio/modules:/other/modules:{install_dir}/"',
        f'export MAYA_MODULE_PATH="/studio/modules:{install_dir}"',
    ]


def _lines_to_keep(install_dir: str) -> list[str]:
    """Lines that look similar to the legacy line but must never be touched."""
    return [
        "# a comment",
        CUSTOMER_LINE,
        "export MAYA_MODULE_PATH=/studio/modules",
        f'export MAYA_MODULE_PATH="{install_dir}/:/studio/modules"',  # not the last entry
        f'export MAYA_MODULE_PATH="{install_dir}-other/"',  # another install dir
        f'export MAYA_MODULE_PATH="/x{install_dir}/"',  # another install dir
        f'export MAYA_MODULE_PATH="/x:prefix{install_dir}/"',  # not a whole entry
        f'export MAYA_MODULE_PATH="{install_dir}//"',  # not the exact form
        f'  export MAYA_MODULE_PATH="{install_dir}/"',  # not the exact form
        f'export MAYA_MODULE_PATH="{install_dir}/" # mine',  # not the exact form
        f'export OTHER_PATH="{install_dir}/"',
        f'export MAYA_MODULE_PATH="a"b:{install_dir}/"',  # not a single quoted value
        "",
    ]


def _write(path: Path, lines: list[str]) -> None:
    path.write_text("".join(f"{line}\n" for line in lines))


@pytest.mark.parametrize("file_name", STARTUP_FILES)
def test_removes_legacy_lines_from_each_startup_file(run, home: Path, file_name: str):
    # GIVEN
    install_dir = "/home/user/DeadlineCloudForMayaSubmitter"
    keep = _lines_to_keep(install_dir)
    legacy = _legacy_lines(install_dir)
    startup_file = home / file_name
    original = [keep[0], legacy[0], *keep[1:6], legacy[1], legacy[2], *keep[6:], legacy[3]]
    _write(startup_file, original)

    # WHEN
    result = run(install_dir, str(home))

    # THEN
    assert startup_file.read_text() == "".join(f"{line}\n" for line in keep)
    backup = home / f"{file_name}{BACKUP_SUFFIX}"
    assert backup.read_text() == "".join(f"{line}\n" for line in original)
    for line in legacy:
        assert f"removed from {startup_file}: {line}" in result.stdout


def test_install_dir_with_regex_metacharacters_is_matched_literally(run, home: Path):
    # GIVEN
    install_dir = r"/opt/a.b*c+d?e(f)g[h]i{2}j|k^l$m\n\\o&p%q"
    bashrc = home / ".bashrc"
    # Each of these would match if the install dir were used as a regex or as a sed replacement.
    near_misses = [
        'export MAYA_MODULE_PATH="/opt/aXbbbcddefgh[h]i{2}j|k^l$m\\n\\\\o&p%q/"',
        'export MAYA_MODULE_PATH="/opt/aXb*c+d?e(f)g[h]i{2}j|k^l$m\\n\\\\o&p%q/"',
        'export MAYA_MODULE_PATH="/opt/a.b*c+d?e(f)g[h]i{2}j|k^l$m\\n\\o&p%q/"',
        'export MAYA_MODULE_PATH="/opt/a.b*c+d?e(f)ghi{2}j|k^l$m\\n\\\\o&p%q/"',
    ]
    legacy = _legacy_lines(install_dir)
    _write(bashrc, [*near_misses, *legacy])

    # WHEN
    run(install_dir, str(home))

    # THEN
    assert bashrc.read_text() == "".join(f"{line}\n" for line in near_misses)


@pytest.mark.parametrize("suffix", ["", "/", "//"])
def test_trailing_slashes_on_install_dir_argument_are_ignored(run, home: Path, suffix: str):
    # GIVEN
    install_dir = "/home/user/Deadline Cloud/Submitters/Maya"
    bashrc = home / ".bashrc"
    _write(bashrc, [CUSTOMER_LINE, *_legacy_lines(install_dir)])

    # WHEN
    run(install_dir + suffix, str(home))

    # THEN
    assert bashrc.read_text() == f"{CUSTOMER_LINE}\n"


def test_symlinked_file_is_rewritten_through_the_link(run, home: Path, tmp_path: Path):
    # GIVEN
    install_dir = "/home/user/DeadlineCloudForMayaSubmitter"
    target = tmp_path / "dotfiles" / "bashrc"
    target.parent.mkdir()
    _write(target, [CUSTOMER_LINE, _legacy_lines(install_dir)[0]])
    link = home / ".bashrc"
    link.symlink_to(target)

    # WHEN
    run(install_dir, str(home))

    # THEN
    assert link.is_symlink()
    assert os.readlink(link) == str(target)
    assert target.read_text() == f"{CUSTOMER_LINE}\n"


def test_file_mode_is_kept(run, home: Path):
    # GIVEN
    install_dir = "/home/user/DeadlineCloudForMayaSubmitter"
    bashrc = home / ".bashrc"
    _write(bashrc, [CUSTOMER_LINE, _legacy_lines(install_dir)[0]])
    bashrc.chmod(0o600)
    inode = bashrc.stat().st_ino

    # WHEN
    run(install_dir, str(home))

    # THEN
    assert bashrc.read_text() == f"{CUSTOMER_LINE}\n"
    assert stat.S_IMODE(bashrc.stat().st_mode) == 0o600
    assert bashrc.stat().st_ino == inode
    backup = home / f".bashrc{BACKUP_SUFFIX}"
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600


def test_files_without_legacy_lines_are_untouched(run, home: Path):
    # GIVEN
    install_dir = "/home/user/DeadlineCloudForMayaSubmitter"
    keep = _lines_to_keep(install_dir)
    for name in STARTUP_FILES:
        _write(home / name, keep)
    # An unrelated file is never read, even if it has the legacy line.
    other = home / ".kshrc"
    _write(other, _legacy_lines(install_dir))
    before = {p.name: (p.read_text(), p.stat().st_mtime_ns) for p in home.iterdir()}

    # WHEN
    result = run(install_dir, str(home))

    # THEN
    after = {p.name: (p.read_text(), p.stat().st_mtime_ns) for p in home.iterdir()}
    assert after == before
    assert "removed" not in result.stdout


def test_legacy_line_for_another_install_dir_is_kept(run, home: Path):
    # GIVEN
    bashrc = home / ".bashrc"
    other = _legacy_lines("/home/user/OtherMayaSubmitter")
    _write(bashrc, other)

    # WHEN
    run("/home/user/DeadlineCloudForMayaSubmitter", str(home))

    # THEN
    assert bashrc.read_text() == "".join(f"{line}\n" for line in other)


@pytest.mark.parametrize("install_dir", ["", "/", "//", "relative/dir", "./dir", "relative/dir/"])
def test_empty_root_or_relative_install_dir_does_nothing(run, home: Path, install_dir: str):
    # GIVEN
    bashrc = home / ".bashrc"
    lines = [
        'export MAYA_MODULE_PATH="/"',
        'export MAYA_MODULE_PATH=""',
        'export MAYA_MODULE_PATH="relative/dir/"',
        'export MAYA_MODULE_PATH="/a:./dir"',
    ]
    _write(bashrc, lines)

    # WHEN
    result = run(install_dir, str(home))

    # THEN
    assert bashrc.read_text() == "".join(f"{line}\n" for line in lines)
    assert "nothing to do" in result.stdout or "refusing" in result.stdout


def test_no_arguments_does_nothing(run, home: Path):
    # GIVEN
    bashrc = home / ".bashrc"
    _write(bashrc, ['export MAYA_MODULE_PATH="/"'])

    # WHEN
    result = run(env_home=str(home))

    # THEN
    assert bashrc.read_text() == 'export MAYA_MODULE_PATH="/"\n'
    assert "nothing to do" in result.stdout


def test_home_defaults_to_home_environment_variable(run, home: Path):
    # GIVEN
    install_dir = "/home/user/DeadlineCloudForMayaSubmitter"
    bashrc = home / ".bashrc"
    _write(bashrc, [CUSTOMER_LINE, _legacy_lines(install_dir)[0]])

    # WHEN
    run(install_dir, env_home=str(home))

    # THEN
    assert bashrc.read_text() == f"{CUSTOMER_LINE}\n"


@pytest.mark.parametrize("missing", ["does-not-exist", ""])
def test_missing_home_does_nothing(run, tmp_path: Path, missing: str):
    # GIVEN
    home = str(tmp_path / missing) if missing else ""

    # WHEN
    result = run("/home/user/DeadlineCloudForMayaSubmitter", home, env_home=home)

    # THEN
    assert "nothing to do" in result.stdout


@pytest.mark.skipif(
    sys.platform != "win32" and os.geteuid() == 0, reason="root can write to read-only files"
)
def test_unwritable_file_is_skipped_without_failing(run, home: Path):
    # GIVEN
    install_dir = "/home/user/DeadlineCloudForMayaSubmitter"
    lines = [CUSTOMER_LINE, _legacy_lines(install_dir)[0]]
    bashrc = home / ".bashrc"
    _write(bashrc, lines)
    bashrc.chmod(0o444)
    zshrc = home / ".zshrc"
    _write(zshrc, lines)

    try:
        # WHEN
        result = run(install_dir, str(home))
    finally:
        bashrc.chmod(0o644)

    # THEN
    assert bashrc.read_text() == "".join(f"{line}\n" for line in lines)
    assert not (home / f".bashrc{BACKUP_SUFFIX}").exists()
    assert f"{bashrc} contains a legacy MAYA_MODULE_PATH line but is not writable" in result.stdout
    # Other files are still cleaned up.
    assert zshrc.read_text() == f"{CUSTOMER_LINE}\n"


def test_running_twice_changes_nothing_the_second_time(run, home: Path):
    # GIVEN
    install_dir = "/home/user/DeadlineCloudForMayaSubmitter"
    original = [CUSTOMER_LINE, _legacy_lines(install_dir)[0]]
    bashrc = home / ".bashrc"
    _write(bashrc, original)

    # WHEN
    run(install_dir, str(home))
    run(install_dir, str(home))

    # THEN
    assert bashrc.read_text() == f"{CUSTOMER_LINE}\n"
    assert (home / f".bashrc{BACKUP_SUFFIX}").read_text() == "".join(
        f"{line}\n" for line in original
    )


def test_file_without_trailing_newline(run, home: Path):
    # GIVEN
    install_dir = "/home/user/DeadlineCloudForMayaSubmitter"
    bashrc = home / ".bashrc"
    bashrc.write_text(f'{CUSTOMER_LINE}\nexport MAYA_MODULE_PATH="{install_dir}/"')

    # WHEN
    run(install_dir, str(home))

    # THEN
    assert bashrc.read_text() == f"{CUSTOMER_LINE}\n"


def test_existing_backup_is_never_overwritten(run, home: Path):
    # GIVEN
    install_dir = "/home/user/DeadlineCloudForMayaSubmitter"
    bashrc = home / ".bashrc"
    earlier_backup = home / f".bashrc{BACKUP_SUFFIX}"
    earlier_backup.write_text("earlier backup\n")
    original = [CUSTOMER_LINE, _legacy_lines(install_dir)[0]]
    _write(bashrc, original)

    # WHEN
    result = run(install_dir, str(home))

    # THEN
    assert bashrc.read_text() == f"{CUSTOMER_LINE}\n"
    assert earlier_backup.read_text() == "earlier backup\n"
    new_backup = home / f".bashrc{BACKUP_SUFFIX}.1"
    assert new_backup.read_text() == "".join(f"{line}\n" for line in original)
    assert f"to {new_backup}" in result.stdout


def test_symlink_at_backup_path_is_never_written_through(run, home: Path, tmp_path: Path):
    # GIVEN
    install_dir = "/home/user/DeadlineCloudForMayaSubmitter"
    precious = tmp_path / "precious"
    precious.write_text("do not touch\n")
    planted = home / f".bashrc{BACKUP_SUFFIX}"
    planted.symlink_to(precious)
    dangling = home / f".bashrc{BACKUP_SUFFIX}.1"
    dangling.symlink_to(tmp_path / "does-not-exist")
    original = [CUSTOMER_LINE, _legacy_lines(install_dir)[0]]
    bashrc = home / ".bashrc"
    _write(bashrc, original)

    # WHEN
    run(install_dir, str(home))

    # THEN
    assert precious.read_text() == "do not touch\n"
    assert not (tmp_path / "does-not-exist").exists()
    assert bashrc.read_text() == f"{CUSTOMER_LINE}\n"
    new_backup = home / f".bashrc{BACKUP_SUFFIX}.2"
    assert not new_backup.is_symlink()
    assert new_backup.read_text() == "".join(f"{line}\n" for line in original)


def test_file_is_skipped_when_all_backup_names_are_taken(run, home: Path):
    # GIVEN
    install_dir = "/home/user/DeadlineCloudForMayaSubmitter"
    for suffix in ["", *(f".{i}" for i in range(1, 10))]:
        (home / f".bashrc{BACKUP_SUFFIX}{suffix}").write_text("taken\n")
    original = [CUSTOMER_LINE, _legacy_lines(install_dir)[0]]
    bashrc = home / ".bashrc"
    _write(bashrc, original)

    # WHEN
    result = run(install_dir, str(home))

    # THEN
    assert bashrc.read_text() == "".join(f"{line}\n" for line in original)
    assert "too many existing backups" in result.stdout


def test_crlf_lines_are_left_alone(run, home: Path):
    """The old installers appended LF lines, so a CRLF line was written by someone else."""
    # GIVEN
    install_dir = "/home/user/DeadlineCloudForMayaSubmitter"
    bashrc = home / ".bashrc"
    content = f'export MAYA_MODULE_PATH="{install_dir}/"\r\n'
    bashrc.write_bytes(content.encode())

    # WHEN
    run(install_dir, str(home))

    # THEN
    assert bashrc.read_bytes() == content.encode()
