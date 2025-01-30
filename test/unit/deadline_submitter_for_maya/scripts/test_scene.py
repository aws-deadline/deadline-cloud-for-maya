# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from typing import Optional

import pytest

from deadline.maya_submitter.scene import (
    FrameRange,
)


class TestFrameRange:
    frame_range_params = [(1, 100, 7), (1, 100, None), (1, None, 7), (10, 10, 10), (1, 10, 1)]

    @pytest.mark.parametrize("start, stop, step", frame_range_params)
    def test_frame_range_iter(self, start: int, stop: int, step: Optional[int]) -> None:
        # GIVEN
        frame_range = FrameRange(start, stop, step)

        # WHEN
        frames = [f for f in frame_range]

        # THEN
        if stop is None:
            stop = start
        if step is None:
            step = 1
        assert frames == [i for i in range(start, stop + step, step)]

    @pytest.mark.parametrize("start, stop, step", frame_range_params)
    def test_frame_repr(self, start: int, stop: int, step: Optional[int]) -> None:
        # GIVEN
        frame_range = FrameRange(start, stop, step)

        # WHEN
        fr_repr = repr(frame_range)

        # THEN
        if stop is None or start == stop:
            assert fr_repr == str(start)
        elif step is None or step == 1:
            assert fr_repr == f"{start}-{stop}"
        else:
            assert fr_repr == f"{start}-{stop}:{step}"
