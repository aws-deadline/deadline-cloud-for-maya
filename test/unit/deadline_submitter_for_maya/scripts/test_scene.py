# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from typing import Optional
import pytest
import os
from unittest.mock import patch, Mock

from deadline.maya_submitter.scene import FrameRange, Scene


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


class TestScene:

    @patch("deadline.maya_submitter.scene.maya.cmds")
    def test_project_path(self, mock_maya_cmds: Mock) -> None:
        Scene.project_path()

        mock_maya_cmds.workspace.assert_called_once_with(query=True, rootDirectory=True)

    @patch.object(Scene, "project_path")
    @patch("deadline.maya_submitter.scene.maya")
    def test_output_path_with_images_suffix(self, mock_maya: Mock, mock_project_path: Mock) -> None:
        test_images_dir: str = "test_images_dir"
        test_project_path: str = "test_project_path"
        mock_maya.mel.eval.return_value = test_images_dir
        mock_project_path.return_value = test_project_path

        output_path: str = Scene.output_path()

        assert output_path == os.path.join(test_project_path, test_images_dir)

    @patch.object(Scene, "project_path")
    @patch("deadline.maya_submitter.scene.maya")
    def test_output_path_without_images_suffix(
        self, mock_maya: Mock, mock_project_path: Mock
    ) -> None:
        test_project_path: str = "test_project_path"
        mock_maya.mel.eval.return_value = None
        mock_project_path.return_value = test_project_path

        output_path: str = Scene.output_path()

        assert output_path == test_project_path
