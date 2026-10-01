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


class TestOcioConfigFile:
    """Tests for Scene.ocio_config_file"""

    @patch("deadline.maya_submitter.scene.maya.cmds")
    def test_ocio_config_file_cm_disabled(self, mock_maya_cmds: Mock) -> None:
        """Tests that None is returned when color management is disabled"""
        # GIVEN
        mock_maya_cmds.colorManagementPrefs.return_value = False

        # WHEN
        result = Scene.ocio_config_file()

        # THEN
        assert result is None
        mock_maya_cmds.colorManagementPrefs.assert_called_once_with(query=True, cmEnabled=True)

    @patch("deadline.maya_submitter.scene.maya.cmds")
    def test_ocio_config_file_returns_bool(self, mock_maya_cmds: Mock) -> None:
        """Tests that None is returned when Maya returns bool instead of string for configFilePath"""
        # GIVEN
        mock_maya_cmds.colorManagementPrefs.side_effect = [
            True,
            True,
        ]  # cmEnabled=True, configFilePath=True (bool)

        # WHEN
        result = Scene.ocio_config_file()

        # THEN
        assert result is None

    @patch("deadline.maya_submitter.scene.maya.cmds")
    def test_ocio_config_file_maya_default_resources(self, mock_maya_cmds: Mock) -> None:
        """Tests that MAYA_RESOURCES path falls back to OCIO env var"""
        # GIVEN
        mock_maya_cmds.colorManagementPrefs.side_effect = [
            True,  # cmEnabled
            "<MAYA_RESOURCES>/OCIO-configs/Maya2022-default/config.ocio",  # configFilePath
        ]

        # WHEN - no OCIO env var set
        with patch.dict(os.environ, {}, clear=True):
            result = Scene.ocio_config_file()

        # THEN
        assert result is None

    @patch("deadline.maya_submitter.scene.maya.cmds")
    def test_ocio_config_file_maya_default_resources_with_ocio_env(
        self, mock_maya_cmds: Mock
    ) -> None:
        """Tests that MAYA_RESOURCES path falls back to OCIO env var when set"""
        # GIVEN
        mock_maya_cmds.colorManagementPrefs.side_effect = [
            True,  # cmEnabled
            "<MAYA_RESOURCES>/OCIO-configs/Maya2022-default/config.ocio",  # configFilePath
        ]
        ocio_env_path = "/studio/ocio/Maya2022-default/config.ocio"

        # WHEN
        with patch.dict(os.environ, {"OCIO": ocio_env_path}):
            result = Scene.ocio_config_file()

        # THEN
        assert result == ocio_env_path

    @patch("deadline.maya_submitter.scene.maya.cmds")
    def test_ocio_config_file_ocio_env_fallback(self, mock_maya_cmds: Mock) -> None:
        """Tests that OCIO env var is used when colorManagementPrefs returns bool

        Backslash separators in the env var (e.g. on Windows) are
        normalized to forward slashes so the OCIOConfigFile parameter
        emitted into the job bundle uses the same separator convention
        as Maya's other path queries (cmds.file, cmds.workspace).
        """
        # GIVEN
        mock_maya_cmds.colorManagementPrefs.side_effect = [
            True,  # cmEnabled
            True,  # configFilePath returns bool (no path set)
        ]
        ocio_env_path = "Z:\\OCIO\\Maya2022-default\\config.ocio"

        # WHEN
        with patch.dict(os.environ, {"OCIO": ocio_env_path}):
            result = Scene.ocio_config_file()

        # THEN
        assert result == "Z:/OCIO/Maya2022-default/config.ocio"

    @patch("deadline.maya_submitter.scene.maya.cmds")
    def test_ocio_config_file_custom_config(self, mock_maya_cmds: Mock) -> None:
        """Tests that custom OCIO config path is returned"""
        # GIVEN
        custom_path = "/projects/show/config/aces_1.2/config.ocio"
        mock_maya_cmds.colorManagementPrefs.side_effect = [
            True,  # cmEnabled
            custom_path,  # configFilePath
        ]

        # WHEN
        result = Scene.ocio_config_file()

        # THEN
        assert result == custom_path

    @patch("deadline.maya_submitter.scene.maya.cmds")
    def test_ocio_config_file_normalizes_windows_separators(self, mock_maya_cmds: Mock) -> None:
        """Tests that backslash separators returned by Maya on Windows are
        normalized to forward slashes.

        Unlike cmds.file and cmds.workspace which always return
        forward-slashed paths on Windows, cmds.colorManagementPrefs
        preserves the input path verbatim. Without normalization the
        OCIOConfigFile job bundle parameter would use a different
        separator convention than every other path parameter, breaking
        tests and producing an inconsistent bundle.
        """
        # GIVEN
        windows_path = "C:\\Studio\\OCIO\\config.ocio"
        mock_maya_cmds.colorManagementPrefs.side_effect = [
            True,  # cmEnabled
            windows_path,  # configFilePath
        ]

        # WHEN
        result = Scene.ocio_config_file()

        # THEN
        assert result == "C:/Studio/OCIO/config.ocio"
