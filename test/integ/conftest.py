# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import pytest

from pathlib import Path


@pytest.fixture
def script_location() -> Path:
    return Path(__file__).parent / "test_scripts"
