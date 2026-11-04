# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Unit tests for pipeline/configure-maya-license.py.

The product list is the helper's real `list` output on a machine with Maya 2027
installed (Arnold and Maya entries), trimmed to the fields the script reads.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parents[2] / "pipeline" / "configure-maya-license.py"

PRODUCTS = [
    {
        "feature_id": "ARNOL",
        "def_prod_key": "C0PS1",
        "def_prod_ver": "2027.0.0.F",
        "sel_prod_key": "C0PS1",
        "sel_prod_ver": "2027.0.0.F",
        "lic_method": 4,
    },
    {
        "feature_id": "MAYA",
        "def_prod_key": "657S1",
        "def_prod_ver": "2027.0.0.F",
        "sel_prod_key": "657S1",
        "sel_prod_ver": "2027.0.0.F",
    },
]


@pytest.fixture(scope="module")
def script():
    """Load the script by path; its filename has hyphens so it cannot be imported."""
    spec = importlib.util.spec_from_file_location("configure_maya_license", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_finds_maya_and_not_arnold(script):
    product = script.find_maya_product(PRODUCTS, "2027")

    assert product is not None
    assert product["sel_prod_key"] == "657S1"


def test_returns_none_for_a_version_that_is_not_installed(script):
    assert script.find_maya_product(PRODUCTS, "2026") is None


def test_change_command_selects_network_licensing(script):
    command = script.change_command(Path("helper"), PRODUCTS[1], "27002@127.0.0.1")

    assert command == [
        "helper",
        "change",
        "--pk",
        "657S1",
        "--pv",
        "2027.0.0.F",
        "--lm",
        "NETWORK",
        "--lt",
        "SINGLE",
        "--ls",
        "27002@127.0.0.1",
    ]
