# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for Maya version selection in ``pipeline/setup-runner.py``.

The module is loaded by path because its filename is hyphenated and so cannot be
imported as ``pipeline.setup_runner``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

_SETUP_RUNNER_PATH = Path(__file__).parents[3] / "pipeline" / "setup-runner.py"

LINUX_ONLY: dict[str, Any] = {"python": "3.13", "installer": {"linux": "Maya2027.run"}}
WINDOWS_ONLY: dict[str, Any] = {"python": "3.13", "installer": {"windows": "Maya2027.zip"}}
NO_INSTALLERS: dict[str, Any] = {"python": "3.13", "installer": {}}


@pytest.fixture(scope="module")
def setup_runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("setup_runner", _SETUP_RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestValidateVersions:
    def test_accepts_every_configured_version(self, setup_runner: ModuleType) -> None:
        setup_runner.validate_versions(list(setup_runner.MAYA_YEAR_TO_CONFIG))

    def test_rejects_unknown_version(self, setup_runner: ModuleType) -> None:
        with pytest.raises(SystemExit) as exit_info:
            setup_runner.validate_versions(["1999"])

        assert exit_info.value.code == 1

    def test_rejects_version_with_no_installer_for_any_platform(
        self, setup_runner: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(setup_runner.MAYA_YEAR_TO_CONFIG, "2027", NO_INSTALLERS)

        with pytest.raises(SystemExit) as exit_info:
            setup_runner.validate_versions(["2027"])

        assert exit_info.value.code == 1


class TestSelectInstallableVersions:
    @pytest.mark.parametrize(
        "config, plat_key, system, expected",
        [
            pytest.param(LINUX_ONLY, "linux", "Linux", ["2027"], id="linux-only-on-linux"),
            pytest.param(LINUX_ONLY, "windows", "Windows", [], id="linux-only-on-windows"),
            pytest.param(
                WINDOWS_ONLY, "windows", "Windows", ["2027"], id="windows-only-on-windows"
            ),
            pytest.param(WINDOWS_ONLY, "linux", "Linux", [], id="windows-only-on-linux"),
        ],
    )
    def test_selects_by_platform_availability(
        self,
        setup_runner: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        config: dict[str, Any],
        plat_key: str,
        system: str,
        expected: list[str],
    ) -> None:
        monkeypatch.setitem(setup_runner.MAYA_YEAR_TO_CONFIG, "2027", config)

        assert setup_runner.select_installable_versions(["2027"], plat_key, system) == expected

    def test_skipping_one_version_leaves_the_others(
        self, setup_runner: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(setup_runner.MAYA_YEAR_TO_CONFIG, "2027", LINUX_ONLY)

        assert setup_runner.select_installable_versions(["2026", "2027"], "windows", "Windows") == [
            "2026"
        ]

    def test_keeps_versions_available_on_both_platforms(self, setup_runner: ModuleType) -> None:
        both = [
            version
            for version, config in setup_runner.MAYA_YEAR_TO_CONFIG.items()
            if config["installer"].keys() >= {"linux", "windows"}
        ]

        for plat_key, system in (("linux", "Linux"), ("windows", "Windows")):
            assert setup_runner.select_installable_versions(both, plat_key, system) == both


class TestInstallerLookups:
    def test_absent_platform_has_no_installer_or_checksum(
        self, setup_runner: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(setup_runner.MAYA_YEAR_TO_CONFIG, "2027", LINUX_ONLY)

        assert setup_runner.maya_installer_name("2027", "windows") is None
        assert setup_runner.maya_checksum("2027", "windows") == ""

    def test_configured_platform_resolves_installer_and_sha256(
        self, setup_runner: ModuleType
    ) -> None:
        for version, config in setup_runner.MAYA_YEAR_TO_CONFIG.items():
            for plat_key, installer in config["installer"].items():
                assert setup_runner.maya_installer_name(version, plat_key) == installer
                assert len(setup_runner.maya_checksum(version, plat_key)) == 64


class TestVerifyChecksum:
    def test_unconfigured_checksum_is_allowed(
        self, setup_runner: ModuleType, tmp_path: Path
    ) -> None:
        installer = tmp_path / "Maya2027.run"
        installer.write_bytes(b"installer")

        assert setup_runner.verify_checksum(installer, "") is True

    def test_mismatched_checksum_still_fails(
        self, setup_runner: ModuleType, tmp_path: Path
    ) -> None:
        installer = tmp_path / "Maya2027.run"
        installer.write_bytes(b"installer")

        with pytest.raises(SystemExit) as exit_info:
            setup_runner.verify_checksum(installer, "0" * 64)

        assert exit_info.value.code == 1
