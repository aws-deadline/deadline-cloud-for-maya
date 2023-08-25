# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import os
import re
from collections import namedtuple
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, PropertyMock, patch

import pytest
import jsonschema  # type: ignore
from openjobio_adaptor_runtime import PathMappingRule
from openjobio_adaptor_runtime.configuration.sysname import OSName

import deadline_adaptor_for_maya.MayaAdaptor.adaptor as adaptor_module
from deadline_adaptor_for_maya.MayaAdaptor import MayaAdaptor
from deadline_adaptor_for_maya.MayaAdaptor.adaptor import _FIRST_MAYA_ACTIONS, MayaNotRunningError

# , _MAYA_INIT_KEYS


@pytest.fixture()
def init_data() -> dict:
    """
    Pytest Fixture to return an init_data dictionary that passes validation

    Returns:
        dict: An init_data dictionary
    """
    return {
        "animation": True,
        "render_setup_include_lights": True,
        "renderer": "mayaSoftware",
        "render_layer": "renderSetupLayer1",
        "strict_error_checking": True,
        "version": 2022,
        "output_file_path": "C:\\Temp\\my_output",
        "project_path": "C:\\Temp\\mynewproject",
        "scene_file": "C:\\Users\\samcan\\Downloads\\Maya\\maya-test.mb",
        "camera": "cameraShape1",
        "image_width": 100,
        "image_height": 100,
        "output_file_prefix": "<Scene>/<RenderLayer>",
    }


@pytest.fixture()
def run_data() -> dict:
    """
    Pytest Fixture to return a run_data dictionary that passes validation

    Returns:
        dict: A run_data dictionary
    """
    return {"frame": 42}


class TestMayaAdaptor_on_start:
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._ActionsQueue.__len__", return_value=0)
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._LoggingSubprocess")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._AdaptorServer")
    def test_no_error(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        init_data: dict,
    ) -> None:
        """Tests that on_start completes without error"""
        adaptor = MayaAdaptor(init_data)
        mock_server.return_value.socket_path = "/tmp/9999"
        adaptor.on_start()

    @patch("time.sleep")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._ActionsQueue.__len__", return_value=0)
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._LoggingSubprocess")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._AdaptorServer")
    def test__wait_for_socket(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_sleep: Mock,
        init_data: dict,
    ) -> None:
        """Tests that the _wait_for_socket method sleeps until a socket is available"""
        # GIVEN
        adaptor = MayaAdaptor(init_data)
        socket_mock = PropertyMock(
            side_effect=[None, None, None, "/tmp/9999", "/tmp/9999", "/tmp/9999"]
        )
        type(mock_server.return_value).socket_path = socket_mock

        # WHEN
        adaptor.on_start()

        # THEN
        assert mock_sleep.call_count == 3

    @patch("threading.Thread")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._AdaptorServer")
    def test_server_init_fail(self, mock_server: Mock, mock_thread: Mock, init_data: dict) -> None:
        """Tests that an error is raised if no socket becomes available"""
        # GIVEN
        adaptor = MayaAdaptor(init_data)

        with patch.object(adaptor, "_SERVER_START_TIMEOUT_SECONDS", 0.01), pytest.raises(
            RuntimeError
        ) as exc_info:
            # WHEN
            adaptor.on_start()

        # THEN
        assert (
            str(exc_info.value)
            == "Could not find a socket path because the server did not finish initializing"
        )

    @patch.object(adaptor_module._os.path, "isfile", return_value=False)
    def test_client_not_found(
        self,
        mock_isfile: Mock,
        init_data: dict,
    ) -> None:
        """Tests that the an error is raised if the maya client file cannot be found"""
        # GIVEN
        adaptor = MayaAdaptor(init_data)
        test_dir = "test_dir"

        with patch.object(adaptor_module._sys, "path", ["unreported_dir", test_dir]):
            with pytest.raises(FileNotFoundError) as exc_info:
                # WHEN
                adaptor._get_maya_client_path()

        # THEN
        error_msg = (
            "Could not find maya_client.py. Check that the MayaClient package is in "
            f"one of the following directories: {[test_dir]}"
        )
        assert str(exc_info.value) == error_msg
        mock_isfile.assert_called_with(
            os.path.join(test_dir, "deadline_adaptor_for_maya", "MayaClient", "maya_client.py")
        )

    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._ActionsQueue.__len__", return_value=1)
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._LoggingSubprocess")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._AdaptorServer")
    def test_maya_init_timeout(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        init_data: dict,
    ) -> None:
        """
        Tests that a TimeoutError is raised if the maya client does not complete initialization
        tasks within a given time frame
        """
        # GIVEN
        adaptor = MayaAdaptor(init_data)
        mock_server.return_value.socket_path = "/tmp/9999"
        new_timeout = 0.01

        with patch.object(adaptor, "_MAYA_START_TIMEOUT_SECONDS", new_timeout), pytest.raises(
            TimeoutError
        ) as exc_info:
            # WHEN
            adaptor.on_start()

        # THEN
        error_msg = (
            f"Maya did not complete initialization actions in {new_timeout} seconds and "
            "failed to start."
        )
        assert str(exc_info.value) == error_msg

    @patch.object(MayaAdaptor, "_maya_is_running", False)
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._ActionsQueue.__len__", return_value=1)
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._LoggingSubprocess")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._AdaptorServer")
    def test_maya_init_fail(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        init_data: dict,
    ) -> None:
        """
        Tests that an RuntimeError is raised if the maya client encounters an exception
        """
        # GIVEN
        adaptor = MayaAdaptor(init_data)
        mock_server.return_value.socket_path = "/tmp/9999"

        with pytest.raises(RuntimeError) as exc_info:
            # WHEN
            adaptor.on_start()

        # THEN
        error_msg = "Maya encountered an error and was not able to complete initialization actions."
        assert str(exc_info.value) == error_msg

    @patch.object(MayaAdaptor, "_action_queue")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._LoggingSubprocess")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._AdaptorServer")
    def test_populate_action_queue_required_keys(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
    ) -> None:
        """Tests that on_start completes without error"""
        mock_actions_queue.__len__.return_value = 0

        adaptor = MayaAdaptor(
            {
                "renderer": "mayaSoftware",
                "scene_file": "/path/to/file",
                "project_path": "/path/to/dir",
                "animation": True,
                "version": 2022,
                "render_layer": "layer",
            }
        )

        mock_server.return_value.socket_path = "/tmp/9999"

        adaptor.on_start()

        calls = mock_actions_queue.enqueue_action.call_args_list
        assert calls[0].args[0].name == "renderer"
        assert calls[1].args[0].name == "path_mapping"
        for call, action in zip(calls[2 : len(_FIRST_MAYA_ACTIONS) + 2], _FIRST_MAYA_ACTIONS):
            assert call.args[0].name == action.name

    @patch.object(MayaAdaptor, "map_path")
    @patch.object(MayaAdaptor, "path_mapping_rules", new_callable=PropertyMock)
    @patch.object(MayaAdaptor, "_action_queue")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._LoggingSubprocess")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._AdaptorServer")
    def test_populate_action_queue_test_mapping(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_rules: Mock,
        mock_map: Mock,
    ) -> None:
        """Tests that on_start completes without error"""
        mock_actions_queue.__len__.return_value = 0
        mock_rules.return_value = [
            PathMappingRule(
                source_os="linux", source_path="/source", destination_path="/destination"
            )
        ]
        adaptor = MayaAdaptor(
            {
                "renderer": "mayaSoftware",
                "scene_file": "/path/to/file",
                "project_path": "/path/to/dir",
                "animation": True,
                "version": 2022,
                "render_layer": "layer",
                "output_file_path": "/output/path",
            }
        )

        mock_server.return_value.socket_path = "/tmp/9999"

        adaptor.on_start()

        calls = mock_actions_queue.enqueue_action.call_args_list

        mapping_call = calls[1].args[0]

        assert mapping_call.name == "path_mapping"
        assert mapping_call.args["path_mapping_rules"] == {"/source": "/destination"}

    @pytest.mark.parametrize("renderer, expected", [("mayaSoftware", False), ("arnold", True)])
    @patch.object(MayaAdaptor, "_setup_arnold_pathmapping")
    @patch.object(MayaAdaptor, "map_path")
    @patch.object(MayaAdaptor, "path_mapping_rules", new_callable=PropertyMock)
    @patch.object(MayaAdaptor, "_action_queue")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._LoggingSubprocess")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._AdaptorServer")
    def test_arnold_pathmapping_called(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_rules: Mock,
        mock_map: Mock,
        mock_setup_arnold_pathmapping: Mock,
        renderer: str,
        expected: bool,
    ):
        """Tests that the _setup_arnold_pathmapping is called if the renderer is arnold"""
        # GIVEN
        mock_actions_queue.__len__.return_value = 0
        mock_rules.return_value = [
            PathMappingRule(
                source_os="linux", source_path="/source", destination_path="/destination"
            )
        ]
        mock_server.return_value.socket_path = "/tmp/9999"
        adaptor = MayaAdaptor(
            {
                "renderer": renderer,
                "scene_file": "/path/to/file",
                "project_path": "/path/to/dir",
                "animation": True,
                "version": 2022,
                "render_layer": "layer",
            }
        )

        # WHEN
        adaptor.on_start()

        # THEN
        if expected:
            mock_setup_arnold_pathmapping.assert_called_once()
        else:
            mock_setup_arnold_pathmapping.assert_not_called()

    @pytest.mark.parametrize(
        "running_os, arnold_os_name",
        [(OSName.WINDOWS, "windows"), (OSName.LINUX, "linux"), (OSName.MACOS, "mac")],
    )
    @patch.object(adaptor_module._OSName, "__new__")
    @patch.dict(os.environ, {}, clear=True)
    @patch.object(adaptor_module, "secure_open")
    @patch.object(adaptor_module, "_json")
    @patch.object(MayaAdaptor, "path_mapping_rules", new_callable=PropertyMock)
    def test_arnold_pathmapping(
        self,
        mock_rules: Mock,
        mock_json: Mock,
        mock_open: Mock,
        mock_osname__new__: Mock,
        running_os: str,
        arnold_os_name: str,
    ):
        """Tests that the _setup_arnold_pathmapping is called if the renderer is arnold"""
        # GIVEN
        mock_rules.return_value = [
            PathMappingRule(
                source_os="linux", source_path="/source", destination_path="/destination"
            ),
            PathMappingRule(
                source_os="windows", source_path="C:\\source", destination_path="/destination"
            ),
            PathMappingRule(
                source_os="mac os", source_path="/mac_source", destination_path="/destination"
            ),
        ]
        mock_osname__new__.return_value = running_os

        expected_json = {
            arnold_os_name: {
                "C:/source": "/destination",
                "/source": "/destination",
                "/mac_source": "/destination",
            },
        }

        adaptor = MayaAdaptor(
            {
                "renderer": "arnold",
                "scene_file": "/path/to/file",
                "project_path": "/path/to/dir",
                "animation": True,
                "version": 2022,
                "render_layer": "layer",
            }
        )

        # WHEN
        adaptor._setup_arnold_pathmapping()

        # THEN
        assert isinstance(adaptor._arnold_temp_dir, TemporaryDirectory)
        assert "ARNOLD_PATHMAP" in os.environ
        assert (arnold_json_path := os.environ["ARNOLD_PATHMAP"]) == str(
            Path(adaptor._arnold_temp_dir.name) / "arnold_pathmapping.json"
        )
        mock_open.assert_called_with(Path(arnold_json_path), open_mode="w")
        mock_json.dump.assert_called_once_with(
            expected_json, mock_open.return_value.__enter__.return_value
        )

    @patch.object(MayaAdaptor, "_maya_is_running", False)
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._ActionsQueue.__len__", return_value=1)
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._LoggingSubprocess")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._AdaptorServer")
    def test_init_data_wrong_schema(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
    ) -> None:
        """
        Tests that an RuntimeError is raised if the maya client encounters an exception
        """
        # GIVEN
        init_data = {"doesNot": "conform", "thisData": "isBad"}
        adaptor = MayaAdaptor(init_data)

        with pytest.raises(jsonschema.exceptions.ValidationError) as exc_info:
            # WHEN
            adaptor.on_start()

        # THEN
        error_msg = " is a required property"
        assert error_msg in exc_info.value.message


class TestMayaAdaptor_on_run:
    @patch("time.sleep")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._ActionsQueue.__len__", return_value=0)
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._LoggingSubprocess")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._AdaptorServer")
    def test_on_run(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_sleep: Mock,
        init_data: dict,
        run_data: dict,
    ) -> None:
        """Tests that on_run completes without error, and waits"""
        # GIVEN
        adaptor = MayaAdaptor(init_data)
        mock_server.return_value.socket_path = "/tmp/9999"
        # First side_effect value consumed by setter
        is_rendering_mock = PropertyMock(side_effect=[None, True, False])
        MayaAdaptor._is_rendering = is_rendering_mock
        adaptor.on_start()

        # WHEN
        adaptor.on_run(run_data)

        # THEN
        mock_sleep.assert_called_once_with(0.1)

    @patch("time.sleep")
    @patch(
        "deadline_adaptor_for_maya.MayaAdaptor.adaptor.MayaAdaptor._is_rendering",
        new_callable=PropertyMock,
    )
    @patch(
        "deadline_adaptor_for_maya.MayaAdaptor.adaptor.MayaAdaptor._maya_is_running",
        new_callable=PropertyMock,
    )
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._ActionsQueue.__len__", return_value=0)
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._LoggingSubprocess")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._AdaptorServer")
    def test_on_run_render_fail(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_maya_is_running: Mock,
        mock_is_rendering: Mock,
        mock_sleep: Mock,
        init_data: dict,
        run_data: dict,
    ) -> None:
        """Tests that on_run raises an error if the render fails"""
        # GIVEN
        mock_is_rendering.side_effect = [None, True, False]
        mock_maya_is_running.side_effect = [True, True, True, False, False]
        mock_logging_subprocess.return_value.returncode = 1
        adaptor = MayaAdaptor(init_data)
        mock_server.return_value.socket_path = "/tmp/9999"
        adaptor.on_start()

        # WHEN
        with pytest.raises(RuntimeError) as exc_info:
            adaptor.on_run(run_data)

        # THEN
        mock_sleep.assert_called_once_with(0.1)
        assert str(exc_info.value) == (
            "Maya exited early and did not render successfully, please check render logs. "
            "Exit code 1"
        )

    @patch("time.sleep")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._ActionsQueue.__len__", return_value=0)
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._LoggingSubprocess")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._AdaptorServer")
    def test_run_data_wrong_schema(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_sleep: Mock,
        init_data: dict,
    ) -> None:
        """Tests that on_run completes without error, and waits"""
        # GIVEN
        adaptor = MayaAdaptor(init_data)
        mock_server.return_value.socket_path = "/tmp/9999"
        # First side_effect value consumed by setter
        is_rendering_mock = PropertyMock(side_effect=[None, True, False])
        MayaAdaptor._is_rendering = is_rendering_mock
        adaptor.on_start()
        run_data = {"bad": "data"}

        with pytest.raises(jsonschema.exceptions.ValidationError) as exc_info:
            # WHEN
            adaptor.on_run(run_data)

        # THEN
        error_msg = " is a required property"
        assert error_msg in exc_info.value.message


class TestMayaAdaptor_on_end:
    @patch.object(MayaAdaptor, "_cleanup_arnold_dir")
    @patch("time.sleep")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._ActionsQueue.__len__", return_value=0)
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._LoggingSubprocess")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._AdaptorServer")
    def test_on_end(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_sleep: Mock,
        mock_cleanup_arnold: Mock,
        init_data: dict,
        run_data: dict,
    ) -> None:
        """Tests that on_end completes without error"""
        # GIVEN
        adaptor = MayaAdaptor(init_data)
        mock_server.return_value.socket_path = "/tmp/9999"
        is_rendering_mock = PropertyMock(return_value=False)
        MayaAdaptor._is_rendering = is_rendering_mock
        adaptor.on_start()
        adaptor.on_run(run_data)

        # WHEN
        adaptor.on_end()

        # THEN
        mock_cleanup_arnold.assert_called_once()


class TestMayaAdaptor_on_cleanup:
    @patch("time.sleep")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._logger")
    def test_on_cleanup_maya_not_graceful_shutdown(
        self, mock_logger: Mock, mock_sleep: Mock, init_data: dict
    ) -> None:
        """Tests that on_cleanup reports when maya does not gracefully shutdown"""
        # GIVEN
        adaptor = MayaAdaptor(init_data)

        with patch(
            "deadline_adaptor_for_maya.MayaAdaptor.adaptor.MayaAdaptor._maya_is_running",
            new_callable=lambda: True,
        ), patch.object(adaptor, "_MAYA_END_TIMEOUT_SECONDS", 0.01), patch.object(
            adaptor, "_maya_client"
        ) as mock_client:
            # WHEN
            adaptor.on_cleanup()

        # THEN
        mock_logger.error.assert_called_once_with(
            "Maya did not complete cleanup actions and failed to gracefully shutdown. Terminating."
        )
        mock_client.terminate.assert_called_once()

    @patch("time.sleep")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._logger")
    def test_on_cleanup_server_not_graceful_shutdown(
        self, mock_logger: Mock, mock_sleep: Mock, init_data: dict
    ) -> None:
        """Tests that on_cleanup reports when the server does not shutdown"""
        # GIVEN
        adaptor = MayaAdaptor(init_data)

        with patch(
            "deadline_adaptor_for_maya.MayaAdaptor.adaptor.MayaAdaptor._maya_is_running",
            new_callable=lambda: False,
        ), patch.object(adaptor, "_SERVER_END_TIMEOUT_SECONDS", 0.01), patch.object(
            adaptor, "_server_thread"
        ) as mock_server_thread:
            mock_server_thread.is_alive.return_value = True
            # WHEN
            adaptor.on_cleanup()

        # THEN
        mock_logger.error.assert_called_once_with("Failed to shutdown the Maya Adaptor server.")
        mock_server_thread.join.assert_called_once_with(timeout=0.01)

    @patch.object(MayaAdaptor, "_cleanup_arnold_dir")
    @patch("time.sleep")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._ActionsQueue.__len__", return_value=0)
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._LoggingSubprocess")
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor._AdaptorServer")
    def test_on_cleanup(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_sleep: Mock,
        mock_cleanup_arnold: Mock,
        init_data: dict,
        run_data: dict,
    ) -> None:
        """Tests that on_end completes without error"""
        # GIVEN
        adaptor = MayaAdaptor(init_data)
        mock_server.return_value.socket_path = "/tmp/9999"
        is_rendering_mock = PropertyMock(return_value=False)
        MayaAdaptor._is_rendering = is_rendering_mock

        adaptor.on_start()
        adaptor.on_run(run_data)
        adaptor.on_end()
        mock_cleanup_arnold.reset_mock()

        with patch(
            "deadline_adaptor_for_maya.MayaAdaptor.adaptor.MayaAdaptor._maya_is_running",
            new_callable=lambda: False,
        ):
            # WHEN
            adaptor.on_cleanup()

        # THEN
        mock_cleanup_arnold.assert_called_once()

    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor.MayaAdaptor.update_status")
    def test_handle_complete(self, mock_update_status: Mock, init_data: dict):
        """Tests that the _handle_complete method updates the progress correctly"""
        # GIVEN
        adaptor = MayaAdaptor(init_data)
        regex_callbacks = adaptor._get_regex_callbacks()
        complete_regex = regex_callbacks[0].regex_list[0]

        # WHEN
        match = complete_regex.search("MayaClient: Finished Rendering Frame 1")
        if match:
            adaptor._handle_complete(match)

        # THEN
        assert match is not None
        mock_update_status.assert_called_once_with(progress=100)

    handle_progess_params = [(0, "[PROGRESS] 99 percent", 99), (1, " 45% done - 11 rays/pixel", 45)]

    @pytest.mark.parametrize("regex_index, stdout, expected_progress", handle_progess_params)
    @patch("deadline_adaptor_for_maya.MayaAdaptor.adaptor.MayaAdaptor.update_status")
    def test_handle_progress(
        self,
        mock_update_status: Mock,
        regex_index: int,
        stdout: str,
        expected_progress: float,
        init_data: dict,
    ) -> None:
        """Tests that the _handle_progress method updates the progress correctly"""
        # GIVEN
        adaptor = MayaAdaptor(init_data)
        regex_callbacks = adaptor._get_regex_callbacks()
        progress_regex = regex_callbacks[1].regex_list[regex_index]

        # WHEN
        match = progress_regex.search(stdout)
        if match:
            adaptor._handle_progress(match)

        # THEN
        assert match is not None
        mock_update_status.assert_called_once_with(progress=expected_progress)

    @pytest.mark.parametrize(
        "stdout, error_regex",
        [
            (
                "RuntimeError: Error encountered when initializing Maya - Please check for "
                "sufficient disk space and necessary write permissions of MAYA_APP_DIR.",
                re.compile(".*Error:.*"),
            ),
            (
                "Warning: file: somefile.mel line 1: filePathEditor: Attribute 'aiVolume.filename'"
                " is invalid or is not designated 'usedAsFilename'.",
                re.compile(".*Warning:.*"),
            ),
        ],
    )
    def test_handle_error(self, init_data: dict, stdout: str, error_regex: re.Pattern) -> None:
        """Tests that the _handle_error method throws a runtime error correctly"""
        # GIVEN
        adaptor = MayaAdaptor(init_data)

        # WHEN
        match = error_regex.search(stdout)
        if match:
            adaptor._handle_error(match)

        # THEN
        assert match is not None
        assert str(adaptor._exc_info) == f"Maya Encountered an Error: {stdout}"

    @patch.object(adaptor_module._shutil, "disk_usage")
    def test_license_handle_error(self, mock_disk_usage: Mock, init_data: dict) -> None:
        """Tests that the _handle_license_error method throws a runtime error correctly"""
        # GIVEN
        adaptor = MayaAdaptor(init_data)
        _maya_license_error = (
            "RuntimeError: Error encountered when initializing Maya - "
            "Please check for sufficient disk space "
            "and necessary write permissions of MAYA_APP_DIR."
        )
        disk_usage = 999999999
        Usage = namedtuple("Usage", ["total", "used", "free"])
        mock_disk_usage.return_value = Usage(disk_usage, 0, disk_usage)

        # WHEN
        match = re.compile(_maya_license_error).search(_maya_license_error)
        if match:
            adaptor._handle_license_error(match)
        license_file = os.environ.get("ADSKFLEX_LICENSE_FILE")
        maya_app_dir = os.environ.get("MAYA_APP_DIR")

        # THEN
        assert str(adaptor._exc_info) == (
            f"{_maya_license_error}\n"
            "This error is typically associated with a licensing error"
            " when using MayaIO. Check your licensing configuration.\n"
            f"Free disc space: {disk_usage//1024//1024}M\n"
            f"MAYA_APP_DIR: {maya_app_dir}\n"
            f"ADSKFLEX_LICENSE_FILE: {license_file}"
        )

    @pytest.mark.parametrize("strict_error_checking", [True, False])
    def test_strict_error_checking(self, init_data: dict, strict_error_checking: bool) -> None:
        """
        Tests that the strict_error_checking flag in the init_data determines if the handle_error
        RegexCallback is returned in the _get_regex_callbacks function
        """
        # GIVEN
        init_data["strict_error_checking"] = strict_error_checking
        adaptor = MayaAdaptor(init_data)
        error_regexes = [re.compile(".*Exception:.*|.*Error:.*|.*Warning.*")]

        # WHEN
        callbacks = adaptor._get_regex_callbacks()

        # THEN
        assert (
            any(error_regexes == regex_callback.regex_list for regex_callback in callbacks)
            == strict_error_checking
        )

    @pytest.mark.parametrize("error_on_arnold_license_fail", [True, False])
    def test_error_on_arnold_license_fail(
        self, init_data: dict, error_on_arnold_license_fail: bool
    ) -> None:
        """
        Tests that the error_on_arnold_license_fail flag in the init_data determines if the relevent
        RegexCallback is returned in the _get_regex_callbacks function
        """
        # GIVEN
        init_data["error_on_arnold_license_fail"] = error_on_arnold_license_fail
        adaptor = MayaAdaptor(init_data)
        expected_regex_list = [
            re.compile("(aborting render because the abort_on_license_fail option was enabled)")
        ]

        # WHEN
        callbacks = adaptor._get_regex_callbacks()

        # THEN
        assert (
            any(expected_regex_list == regex_callback.regex_list for regex_callback in callbacks)
            == error_on_arnold_license_fail
        )

    @pytest.mark.parametrize("adaptor_exc_info", [RuntimeError("Something Bad Happened!"), None])
    def test_has_exception(self, init_data: dict, adaptor_exc_info: Exception | None) -> None:
        """
        Validates that the adaptor._has_exception property raises when adaptor._exc_info is not None
        and returns false when adaptor._exc_info is None
        """
        adaptor = MayaAdaptor(init_data)
        adaptor._exc_info = adaptor_exc_info

        if adaptor_exc_info:
            with pytest.raises(RuntimeError) as exc_info:
                adaptor._has_exception

            assert exc_info.value == adaptor_exc_info
        else:
            assert not adaptor._has_exception

    @patch.object(MayaAdaptor, "_maya_is_running", new_callable=PropertyMock(return_value=False))
    def test_raises_if_maya_not_running(
        self,
        init_data: dict,
        run_data: dict,
    ) -> None:
        """Tests that on_run raises a MayaNotRunningError if maya is not running"""
        # GIVEN
        adaptor = MayaAdaptor(init_data)

        # WHEN
        with pytest.raises(MayaNotRunningError) as raised_err:
            adaptor.on_run(run_data)

        # THEN
        assert raised_err.match("Cannot render because Maya is not running.")


class TestMayaAdaptor_on_cancel:
    """Tests for MayaAdaptor.on_cancel"""

    def test_terminates_maya_client(self, init_data: dict, caplog: pytest.LogCaptureFixture):
        """Tests that the maya client is terminated on cancel"""
        # GIVEN
        caplog.set_level(0)
        adaptor = MayaAdaptor(init_data)
        adaptor._maya_client = mock_client = Mock()

        # WHEN
        adaptor.on_cancel()

        # THEN
        mock_client.terminate.assert_called_once_with(grace_time_s=0)
        assert "CANCEL REQUESTED" in caplog.text

    def test_does_nothing_if_maya_not_running(
        self, init_data: dict, caplog: pytest.LogCaptureFixture
    ):
        """Tests that nothing happens if a cancel is requested when maya is not running"""
        # GIVEN
        caplog.set_level(0)
        adaptor = MayaAdaptor(init_data)
        adaptor._maya_client = None

        # WHEN
        adaptor.on_cancel()

        # THEN
        assert "CANCEL REQUESTED" in caplog.text
        assert "Nothing to cancel because Maya is not running" in caplog.text
