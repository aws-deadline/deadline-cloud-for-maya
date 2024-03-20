# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import re

import pytest

from deadline.maya_submitter.utils import join_paths, timed_func


def test_timed_func(capsys):
    """Basic test to ensure the timed captures func and timing info"""
    # GIVEN
    args = ("args",)
    kwargs = {"key": "word"}

    @timed_func
    def quick_func(*args, **kwargs) -> bool:
        print("I'm a quick func")
        return True

    # WHEN
    result = quick_func(*args, **kwargs)
    output = capsys.readouterr()

    # THEN
    # ensure the inner func ran properly
    assert result is True
    assert "I'm a quick func" in output.out

    # ensure we have the decorator info
    expected_re = (
        rf"func: quick_func with args: {re.escape(str(args))}, "
        rf"kwargs: {re.escape(str(kwargs))}, "
        r"took \d.\d{3} seconds"
    )
    match = re.search(expected_re, output.out)
    assert match is not None


@pytest.mark.parametrize(
    ("first_path, second_path, expected_output"),
    [
        (
            "test\\path",
            "path\\",
            "test/path/path/",
        ),
        (
            "test",
            "path",
            "test/path",
        ),
        (
            "test/path",
            "path",
            "test/path/path",
        ),
    ],
)
def test_join_paths(first_path: str, second_path: str, expected_output: str):
    """Basic test to ensure backslash paths are replaced"""
    assert join_paths(first_path, second_path) == expected_output
