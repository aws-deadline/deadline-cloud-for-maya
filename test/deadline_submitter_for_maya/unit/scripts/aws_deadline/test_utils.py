# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from typing import List

import pytest

from deadline_submitter_for_maya.scripts.aws_deadline.utils import join_paths

join_path_parameters = [
    ("some\\path\\with\\backslashes", [], "some/path/with/backslashes"),
    ("another\\path", ["with", "backslashes"], "another/path/with/backslashes"),
    ("some\\path\\with\\forwardslashes", [], "some/path/with/forwardslashes"),
    ("another\\path", ["with", "forwardslashes"], "another/path/with/forwardslashes"),
]


@pytest.mark.parametrize("first, remainder, expected", join_path_parameters)
def test_join_paths(first: str, remainder: List[str], expected: str) -> None:
    # WHEN
    new_path = join_paths(first, *remainder)

    # THEN
    assert new_path == expected
