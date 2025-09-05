# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import re
from unittest.mock import MagicMock, patch

import pytest

from deadline.maya_submitter.utils import join_paths, timed_func
from deadline.maya_submitter import utils as utils_module


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


@pytest.mark.parametrize("frame_symbol", ["<f>", "<frame>"])
@patch.object(utils_module.os.path, "isfile", return_value=True)
@patch.object(utils_module.os, "listdir")
@patch.object(utils_module.os.path, "isdir", return_value=True)
@patch.object(utils_module, "_patternToRegex")
def test_findAllFilesForPattern(
    mock_patternToRegex: MagicMock,
    mock_isdir: MagicMock,
    mock_listdir: MagicMock,
    mock_isfile: MagicMock,
    frame_symbol: str,
) -> None:
    # GIVEN
    pattern = f"/test/file/path.{frame_symbol}.png"
    frame_number = 2
    mock_listdir.return_value = [
        "/test/file/path.0001.png",
        "/test/file/path.0002.png",
        "/test/file/path.0003.png",
        "/test/file/path.000002.png",
        "/test/file/path.2.png",
    ]
    # TODO: Figure out what patternToRegex actually does
    mock_patternToRegex.return_value = pattern.replace("<f>", f"0*{frame_number}").replace(
        "<frame>", f"0*{frame_number}"
    )

    # WHEN
    result = utils_module.findAllFilesForPattern(pattern, frame_number)

    # THEN
    assert result == [
        "/test/file/path.0002.png",
        "/test/file/path.000002.png",
        "/test/file/path.2.png",
    ]
