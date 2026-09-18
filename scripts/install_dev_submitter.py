# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import argparse
import json
import platform
import re
import shutil
import subprocess
from pathlib import Path

from typing import Optional

from _project import Dependency, get_git_root, get_dependencies, get_project_dict, get_pip_platform
from deps_bundle import _add_console_extra, _canonical_name


class MayaVersion:
    major: int

    PYTHON_VERSIONS = {
        "2023": "3.9",
        "2024": "3.10",
        "2025": "3.11",
        "2026": "3.11",
        "2027": "3.13",
    }

    def __init__(self, arg_version: Optional[str]):
        self.major = self._get_maya_version(arg_version)

    @classmethod
    def _validate_version(cls, version: str) -> str:
        return str(int(version))

    @classmethod
    def _get_maya_version(cls, arg: Optional[str]) -> str:
        if arg is not None:
            return cls._validate_version(arg)
        maya_version_file = get_git_root() / "maya_version.txt"
        if maya_version_file.exists():
            with open(maya_version_file, "r", encoding="utf-8") as f:
                return cls._validate_version(f.read().strip())
        return cls._validate_version(input("Please enter the Maya version: "))

    def python_major_minor(self) -> str:
        major = self.major
        if major in self.PYTHON_VERSIONS:
            return self.PYTHON_VERSIONS[major]
        raise ValueError(f"Unknown Maya version: {major}")


def _get_maya_env_file(version: str) -> Path:
    if platform.system() == "Windows":
        return Path.home() / "Documents" / "maya" / version / "Maya.env"
    elif platform.system() == "Darwin":
        return Path.home() / "Library" / "Preferences" / "Autodesk" / "maya" / version / "Maya.env"
    elif platform.system() == "Linux":
        return Path.home() / "maya" / version / "Maya.env"
    else:
        raise RuntimeError(f"Unsupported platform: {platform.system()}")


def _setup_maya_env_file(maya_mod_path: Path, install_path: Path):
    """MAYA_ENV_DIR will point to this Maya.env file to discover the submitter"""
    maya_env = f"MAYA_MODULE_PATH={install_path}"

    with open(maya_mod_path / "Maya.env", "w") as f:
        f.write(maya_env)


_REQUIREMENT_NAME_REGEX = re.compile(r"\s*([A-Za-z0-9._-]+)")


def _requirement_name(spec: str) -> str:
    """The canonical package name of a requirement string, regardless of spacing.

    _project.Dependency.name splits on a single space, which misparses spaceless
    strings ("botocore[crt]>=1.34.0" would yield the whole string), so name
    comparisons against requirement strings from other pyproject.toml files go
    through this instead.
    """
    match = _REQUIREMENT_NAME_REGEX.match(spec)
    if not match:
        raise ValueError(f"Cannot parse a requirement name out of: {spec!r}")
    return _canonical_name(match.group(1))


def _specs_for_pipgrip(dependencies: list, add_console_extra: bool = True) -> list[str]:
    """Requirement strings for pipgrip, with deadline's console extra applied.

    This tree is a submitter, the same as the installer's dependency bundle, so it
    needs the same rewrite scripts/deps_bundle.py applies: the console extra lives
    at build time rather than in project.dependencies (see the comment in
    _build_base_environment there). Without it the dev submitter would silently
    lack AWS Console sign-in while the shipped one has it.

    _add_console_extra tolerates pyproject.toml's spacing and preserves the
    specifier and any environment marker byte-for-byte, and returns anything not
    named deadline untouched -- important here because this list includes
    --local-dep checkouts' requirement strings.
    """
    if not add_console_extra:
        return [dep.spec for dep in dependencies]
    return [_add_console_extra(dep.spec) for dep in dependencies]


def _console_extra_requirements(
    local_dep_project_dicts: list[dict], local_dep_names: set[str]
) -> list:
    """The contents of deadline's console extra, for a --local-dep'd deadline.

    When deadline itself is supplied with --local-dep, the requirement on it is
    filtered out before _specs_for_pipgrip runs, so _add_console_extra never fires
    and awscrt plus the crt-capable botocore floor would silently drop out of the
    tree -- precisely the setup someone debugging console sign-in would be running.
    Instead, feed the extra's own requirements from that checkout's pyproject.toml.

    The extra's requirements honour the same local_dep_names filter as the declared
    dependencies: anything also supplied with --local-dep must not be pinned from
    PyPI on top of the local checkout. local_dep_names must already be canonical.

    A deadline checkout with no console extra at all is a broken dev setup rather
    than a no-op -- the extra exists in every release from 0.60.4, the floor
    pyproject.toml requires -- so it raises instead of silently building a
    submitter that cannot sign in.
    """
    requirements = []
    for project_dict in local_dep_project_dicts:
        if _canonical_name(project_dict["project"]["name"]) != "deadline":
            continue
        optional = project_dict["project"].get("optional-dependencies", {})
        if "console" not in optional:
            raise Exception(
                "the --local-dep deadline checkout declares no console extra; every "
                "deadline release from 0.60.4 (the floor pyproject.toml requires) has "
                "one, so the checkout is older than the floor or on a broken branch -- "
                "update it, or drop --local-dep for deadline"
            )
        requirements.extend(
            Dependency(req)
            for req in optional["console"]
            if _requirement_name(req) not in local_dep_names
        )
    return requirements


def _resolve_dependencies(local_deps: list[Path], add_console_extra: bool = True) -> dict[str, str]:
    project_dict = get_project_dict()
    local_dep_project_dicts = [get_project_dict(local_dep) for local_dep in local_deps]
    # Canonical on both sides: a checkout declaring name = "PyYAML" or "deadline_cloud"
    # must still match a requirement spelled pyyaml / deadline-cloud.
    local_dep_names = set(
        _canonical_name(local_dep["project"]["name"]) for local_dep in local_dep_project_dicts
    )
    all_project_dicts = [*local_dep_project_dicts, project_dict]
    dependency_lists = [get_dependencies(project_dict) for project_dict in all_project_dicts]
    filtered_dependency_lists = [
        [dep for dep in dependency_list if _requirement_name(dep.spec) not in local_dep_names]
        for dependency_list in dependency_lists
    ]
    flattened_dependency_list = [
        dep for dependency_list in filtered_dependency_lists for dep in dependency_list
    ]
    if add_console_extra:
        flattened_dependency_list.extend(
            _console_extra_requirements(local_dep_project_dicts, local_dep_names)
        )

    args = [
        "pipgrip",
        "--json",
        *_specs_for_pipgrip(flattened_dependency_list, add_console_extra=add_console_extra),
    ]
    try:
        result = subprocess.run(args, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(e.stderr)
        print(e.stdout)
        raise
    return json.loads(result.stdout)


def _build_deps_env(
    destination: Path, python_version: str, local_deps: list[Path], add_console_extra: bool = True
) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if not destination.is_dir():
        raise Exception(f"{str(destination)} is not a directory")

    resolved_dependencies_dict = _resolve_dependencies(
        local_deps, add_console_extra=add_console_extra
    )
    resolved_dependencies = [
        f"{dep_name}=={resolved_version}"
        for dep_name, resolved_version in resolved_dependencies_dict.items()
    ]

    args = [
        "pip",
        "install",
        "--target",
        str(destination),
        "--python-version",
        python_version,
        "--only-binary=:all:",
        *resolved_dependencies,
    ]
    if python_version == "3.9":
        # maya 2023 on mac relies on rosetta
        # should probably swap to maya's pip to avoid specifying platform
        args = [
            "pip",
            "install",
            "--target",
            str(destination),
            "--platform",
            get_pip_platform(platform.system()),
            "--python-version",
            python_version,
            "--only-binary=:all:",
            *resolved_dependencies,
        ]

    subprocess.run(args, check=True)


def _copy_maya_submitter_source(dest_path: Path):
    shutil.copytree(get_git_root() / "src", dest_path, dirs_exist_ok=True)


def _copy_maya_submitter_plugin(dest_path: Path):
    shutil.copytree(get_git_root() / "maya_submitter_plugin", dest_path, dirs_exist_ok=True)


def install_submitter_package(maya_version_arg: Optional[str], local_deps: list[Path]) -> None:
    """Installs deadline-cloud-for-maya similarly to install builder.
    Requires `hatch shell` activation and then launching Maya
    """
    maya_version = MayaVersion(maya_version_arg)
    python_version = maya_version.python_major_minor()
    # Maya 2023 targets Python 3.9, where _build_deps_env adds an explicit
    # --platform for the host OS and pipgrip's pins are exact, so every dependency
    # must have a cp39 wheel for that literal tag -- pip cannot walk back. Today
    # only macOS fails that bar: no awscrt wheel satisfying deadline's console
    # extra exists for macosx_10_9_x86_64 (see pyproject.toml), while cp39 wheels
    # for win_amd64 and manylinux2014_x86_64 do exist, so those platforms keep
    # console sign-in. If awscrt drops cp39 wheels entirely, the same hard failure
    # appears on every platform and this condition must widen to all of 3.9.
    # Skip it, loudly: the adaptor package excludes the extra for the same tag.
    skip_console_extra = python_version == "3.9" and platform.system() == "Darwin"
    if skip_console_extra:
        print(
            "WARNING: not requesting deadline's console extra: no awscrt wheel exists "
            "for --platform macosx_10_9_x86_64 (Maya 2023 / Python 3.9 on macOS), so "
            "AWS Console sign-in will be unavailable in this dev submitter."
        )
    plugin_env_path = get_git_root() / "plugin_env"
    scripts_path = plugin_env_path / "scripts"
    shutil.rmtree(plugin_env_path, ignore_errors=True)
    _build_deps_env(
        scripts_path,
        python_version,
        local_deps,
        add_console_extra=not skip_console_extra,
    )
    _copy_maya_submitter_source(dest_path=scripts_path)
    _copy_maya_submitter_plugin(dest_path=plugin_env_path)

    # TODO: For actual installation, we'll want to use the env
    # file in the installation, skipping for now
    maya_mod_path = plugin_env_path
    _setup_maya_env_file(plugin_env_path, maya_mod_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--maya-version",
        help="Maya version to install the submitter for",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--local-dep",
        help="Path to a repository containing a dependency for in-place install",
        action="append",
        type=str,
    )
    args = parser.parse_args()
    local_deps = [Path(dep) for dep in args.local_dep or []]

    install_submitter_package(args.maya_version, local_deps)
