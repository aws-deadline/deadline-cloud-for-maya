# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from pathlib import Path

import pytest


@pytest.fixture
def script_location() -> Path:
    return Path(__file__).parent / "test_scripts"
