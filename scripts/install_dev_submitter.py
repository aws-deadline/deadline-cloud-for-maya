# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import argparse
import json
import platform
import shutil
import subprocess
from pathlib import Path

from typing import Optional

from _project import Dependency, get_git_root, get_dependencies, get_project_dict, get_pip_platform
from deps_bundle import _add_console_extra


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


def _specs_for_pipgrip(dependencies: list, add_console_extra: bool = True) -> list[str]:
    """Requirement strings for pipgrip, with deadline's console extra applied.

    This tree is a submitter, the same as the installer's dependency bundle, so it
    needs the same rewrite scripts/deps_bundle.py applies: the console extra lives
    at build time rather than in project.dependencies (see the comment in
    _build_base_environment there). Without it the dev submitter would silently
    lack AWS Console sign-in while the shipped one has it.

    Spaces are stripped before matching because _project.Dependency.spec preserves
    pyproject.toml's spacing ("deadline >= 0.60.4") and _add_console_extra matches
    the requirement name at the start of the string. The stripped form is used only
    when the rewrite actually fired: every other spec passes through byte-for-byte,
    since this list includes --local-dep checkouts' requirement strings, whose
    environment markers whitespace removal can corrupt ('... >= "3.10" and ...'
    is not tokenizable without its spaces).
    """
    specs = []
    for dep in dependencies:
        stripped = dep.spec.replace(" ", "")
        rewritten = _add_console_extra(stripped)
        specs.append(rewritten if add_console_extra and rewritten != stripped else dep.spec)
    return specs


def _console_extra_requirements(local_dep_project_dicts: list[dict]) -> list:
    """The contents of deadline's console extra, for a --local-dep'd deadline.

    When deadline itself is supplied with --local-dep, the requirement on it is
    filtered out before _specs_for_pipgrip runs, so _add_console_extra never fires
    and awscrt plus the crt-capable botocore floor would silently drop out of the
    tree -- precisely the setup someone debugging console sign-in would be running.
    Instead, feed the extra's own requirements from that checkout's pyproject.toml.
    """
    requirements = []
    for project_dict in local_dep_project_dicts:
        if project_dict["project"]["name"] != "deadline":
            continue
        optional = project_dict["project"].get("optional-dependencies", {})
        requirements.extend(Dependency(req) for req in optional.get("console", []))
    return requirements


def _resolve_dependencies(local_deps: list[Path], add_console_extra: bool = True) -> dict[str, str]:
    project_dict = get_project_dict()
    local_dep_project_dicts = [get_project_dict(local_dep) for local_dep in local_deps]
    local_dep_names = set([local_dep["project"]["name"] for local_dep in local_dep_project_dicts])
    all_project_dicts = [*local_dep_project_dicts, project_dict]
    dependency_lists = [get_dependencies(project_dict) for project_dict in all_project_dicts]
    filtered_dependency_lists = [
        [dep for dep in dependency_list if dep.name not in local_dep_names]
        for dependency_list in dependency_lists
    ]
    flattened_dependency_list = [
        dep for dependency_list in filtered_dependency_lists for dep in dependency_list
    ]
    if add_console_extra:
        flattened_dependency_list.extend(_console_extra_requirements(local_dep_project_dicts))

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
    # Maya 2023's Python 3.9 install on macOS pins --platform macosx_10_9_x86_64,
    # and no awscrt wheel satisfying deadline's console extra exists for that tag
    # (see pyproject.toml). pipgrip's pins are exact, so requesting the extra there
    # is not a degraded install but a hard resolver failure. Skip it, loudly: the
    # adaptor package excludes the extra for the same tag.
    add_console_extra = not (python_version == "3.9" and platform.system() == "Darwin")
    if not add_console_extra:
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
        add_console_extra=add_console_extra,
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
