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
