# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Verify that unpacking MtoA does not omit Autodesk's licensing setup."""

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def setup_runner():
    path = Path(__file__).parents[2] / "pipeline" / "setup-runner.py"
    spec = importlib.util.spec_from_file_location("setup_runner_arnold", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("legacy_installer", [False, True])
def test_licensing_registration_runs_after_optional_legacy_installer(
    setup_runner, monkeypatch, tmp_path, legacy_installer
):
    license_dir = tmp_path / "license"
    license_dir.mkdir()
    updater = license_dir / "LicensingUpdater"
    updater.touch()
    legacy = license_dir / "ArnoldLicensing-8.1-linux.run"
    if legacy_installer:
        legacy.touch()
    commands = []
    monkeypatch.delenv("LICENSE_ENDPOINT_DNS", raising=False)
    monkeypatch.setattr(setup_runner, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        setup_runner, "run_with_timeout", lambda command, **kwargs: commands.append(command)
    )

    setup_runner._configure_arnold_licensing_linux(tmp_path)

    expected = [[str(legacy), "--silent"]] if legacy_installer else []
    assert commands == expected + [[str(updater)]]


def test_missing_registration_tool_fails_setup(setup_runner, tmp_path):
    with pytest.raises(RuntimeError, match="missing its licensing updater"):
        setup_runner._configure_arnold_licensing_linux(tmp_path)


def test_registered_arnold_uses_network_licensing_in_ci(setup_runner, monkeypatch, tmp_path):
    from types import SimpleNamespace

    license_dir = tmp_path / "license"
    license_dir.mkdir()
    (license_dir / "LicensingUpdater").touch()
    monkeypatch.setenv("LICENSE_ENDPOINT_DNS", "licenses.example")
    monkeypatch.setattr(setup_runner, "run", lambda *args, **kwargs: None)
    commands = []
    monkeypatch.setattr(
        setup_runner, "run_with_timeout", lambda command, **kwargs: commands.append(command)
    )
    monkeypatch.setattr(
        setup_runner.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout='[{"feature_id":"ARNOL","def_prod_key":"arnold-key",'
            '"def_prod_ver":"2026.0.0.F"},{"feature_id":"MAYA"}]'
        ),
    )
    setup_runner._configure_arnold_licensing_linux(tmp_path)
    assert commands[-1][1:] == [
        "change",
        "--pk",
        "arnold-key",
        "--pv",
        "2026.0.0.F",
        "--lm",
        "NETWORK",
        "--lt",
        "SINGLE",
        "--ls",
        "2701@licenses.example",
    ]


@pytest.mark.parametrize("maya_version,license_version", [("2025", "2026"), ("2027", "2027")])
def test_mayaio_pit_preserves_maya_and_adds_matching_arnold(
    setup_runner, monkeypatch, tmp_path, maya_version, license_version
):
    from types import SimpleNamespace

    maya_root = tmp_path / "maya"
    maya_pit = maya_root / "lib" / "ProductInformation.pit"
    maya_pit.parent.mkdir(parents=True)
    maya_pit.write_bytes(b"MAYAIO entry")
    install_dir = tmp_path / "mtoa"
    arnold_pit = install_dir / "license" / "pit" / "ArnoldConfig.pit"
    arnold_pit.parent.mkdir(parents=True)
    arnold_pit.touch()
    system_pit = tmp_path / "system" / "ProductInformation.pit"
    monkeypatch.setattr(
        setup_runner,
        "Path",
        lambda value: (
            system_pit
            if str(value).endswith("Adlm/.config/ProductInformation.pit")
            else Path(value)
        ),
    )
    monkeypatch.setattr(setup_runner, "_find_mayapy", lambda path: maya_root / "bin" / "mayapy")
    monkeypatch.setattr(
        setup_runner.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout=f'[{{"feature_id":"ARNOL","def_prod_key":"arnold-key",'
            f'"def_prod_ver":"{license_version}.0.0.F"}}]'
        ),
    )

    def register(command, **kwargs):
        assert system_pit.read_bytes() == b"MAYAIO entry"
        assert command[1:] == [
            "register",
            "--pk",
            "arnold-key",
            "--pv",
            f"{license_version}.0.0.F",
            "--lm",
            "NETWORK",
            "--cf",
            str(arnold_pit),
        ]
        system_pit.write_bytes(system_pit.read_bytes() + b";ARNOLD entry")

    monkeypatch.setattr(setup_runner, "run_with_timeout", register)
    setup_runner._register_arnold_for_mayaio(maya_version, install_dir)
    assert maya_pit.read_bytes() == b"MAYAIO entry;ARNOLD entry"
