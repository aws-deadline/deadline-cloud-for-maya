# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import re

from deadline_submitter_for_maya.scripts.aws_deadline.utils import timed_func


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
