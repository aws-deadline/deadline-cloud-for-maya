# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import json as _json
import logging as _logging
import os as _os
import platform as _platform
import re as _re
import shutil as _shutil
import sys as _sys
import tempfile as _tempfile
import threading as _threading
import time as _time
from dataclasses import dataclass
from pathlib import Path as _Path
from typing import Callable as _Callable

from openjobio_adaptor_runtime import AdaptorDataValidators as _AdaptorDataValidators
from openjobio_adaptor_runtime_client import Action as _Action
from openjobio_adaptor_runtime import Adaptor as _Adaptor
from openjobio_adaptor_runtime import AdaptorConfiguration as _AdaptorConfiguration
from openjobio_adaptor_runtime import LoggingSubprocess as _LoggingSubprocess
from openjobio_adaptor_runtime import RegexCallback as _RegexCallback
from openjobio_adaptor_runtime import RegexHandler as _RegexHandler
from openjobio_adaptor_runtime.adaptors.adaptor_ipc import ActionsQueue as _ActionsQueue
from openjobio_adaptor_runtime.adaptors.adaptor_ipc import AdaptorServer as _AdaptorServer
from openjobio_adaptor_runtime.configuration.sysname import OSName as _OSName
from openjobio_adaptor_runtime.utils import secure_open

_logger = _logging.getLogger(__name__)


class MayaNotRunningError(Exception):
    """Error that is raised when attempting to use Maya while it is not running"""

    pass


@dataclass(frozen=True)
class _ActionItem:
    name: str
    requires_path_mapping: bool = False

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        return self.name == other.name


_FIRST_MAYA_ACTIONS = [
    _ActionItem("scene_file", requires_path_mapping=True),
    _ActionItem("project_path", requires_path_mapping=True),
]  # Actions which must be queued before any others
_MAYA_INIT_KEYS = {
    _ActionItem("animation"),
    _ActionItem("camera"),
    _ActionItem("image_height"),
    _ActionItem("image_width"),
    _ActionItem("output_file_path", requires_path_mapping=True),
    _ActionItem("output_file_prefix", requires_path_mapping=True),
    _ActionItem("render_layer"),
    _ActionItem("render_setup_include_lights"),
    _ActionItem("error_on_arnold_license_fail"),
}


def _check_for_exception(func: _Callable) -> _Callable:
    """
    Decorator that checks if an exception has been caught before calling the
    decorated function
    """

    def wrapped_func(self, *args, **kwargs):
        if not self._has_exception:  # Raises if there is an exception
            return func(self, *args, **kwargs)

    return wrapped_func


class MayaAdaptor(_Adaptor[_AdaptorConfiguration]):
    """
    Adaptor that creates a session in Maya to Render interactively.
    """

    _SERVER_START_TIMEOUT_SECONDS = 30
    _SERVER_END_TIMEOUT_SECONDS = 30
    _MAYA_START_TIMEOUT_SECONDS = 86400
    _MAYA_END_TIMEOUT_SECONDS = 30

    _server: _AdaptorServer | None = None
    _server_thread: _threading.Thread | None = None
    _maya_client: _LoggingSubprocess | None = None
    _action_queue = _ActionsQueue()
    _is_rendering: bool = False
    _arnold_temp_dir: _tempfile.TemporaryDirectory | None = None
    # If a thread raises an exception we will update this to raise in the main thread
    _exc_info: Exception | None = None
    _performing_cleanup = False

    @staticmethod
    def _get_timer(timeout: int | float) -> _Callable[[], bool]:
        """Given a timeout length, returns a lambda which returns True until the timeout occurs"""
        timeout_time = _time.time() + timeout
        return lambda: _time.time() < timeout_time

    @property
    def _has_exception(self) -> bool:
        """Property which checks the private _exc_info property for an exception

        Raises:
            self._exc_info: An exception if there is one

        Returns:
            bool: False there is no exception waiting to be raised
        """
        if self._exc_info and not self._performing_cleanup:
            raise self._exc_info
        return False

    @property
    def _maya_is_running(self) -> bool:
        """Property which indicates that the maya client is running

        Returns:
            bool: True if the maya client is running, false otherwise
        """
        return self._maya_client is not None and self._maya_client.is_running

    @property
    def _maya_is_rendering(self) -> bool:
        """Property which indicates if maya is rendering

        Returns:
            bool: True if maya is rendering, false otherwise
        """
        return self._maya_is_running and self._is_rendering

    @_maya_is_rendering.setter
    def _maya_is_rendering(self, value: bool) -> None:
        """Property setter which updates the private _is_rendering boolean.

        Args:
            value (bool): A boolean indicated if maya is rendering.
        """
        self._is_rendering = value

    def _wait_for_socket(self) -> str:
        """
        Performs a busy wait for the socket path that the adaptor server is running on, then
        returns it.

        Raises:
            RuntimeError: If the server does not finish initializing

        Returns:
            str: The socket path the adaptor server is running on.
        """
        is_not_timed_out = self._get_timer(self._SERVER_START_TIMEOUT_SECONDS)
        while (self._server is None or self._server.socket_path is None) and is_not_timed_out():
            _time.sleep(0.01)

        if self._server is not None and self._server.socket_path is not None:
            return self._server.socket_path

        raise RuntimeError(
            "Could not find a socket path because the server did not finish initializing"
        )

    def _start_maya_server(self) -> None:
        """
        Starts a server with the given ActionsQueue, attaches the server to the adaptor and serves
        forever in a blocking call.
        """
        self._server = _AdaptorServer(self._action_queue, self)
        self._server.serve_forever()

    def _start_maya_server_thread(self) -> None:
        """
        Starts the maya adaptor server in a thread.
        Sets the environment variable "MAYA_ADAPTOR_SOCKET_PATH" to the socket the server is running
        on after the server has finished starting.
        """
        self._server_thread = _threading.Thread(
            target=self._start_maya_server, name="MayaAdaptorServerThread"
        )
        self._server_thread.start()
        _os.environ["MAYA_ADAPTOR_SOCKET_PATH"] = self._wait_for_socket()

    def _get_regex_callbacks(self) -> list[_RegexCallback]:
        """
        Returns a list of RegexCallbacks used by the Maya Adaptor
        TODO: Eventually we will want to split this into its own class so each renderer will
        generate its own callback list

        Returns:
            list[RegexCallback]: List of Regex Callbacks to add
        """
        _maya_license_error = (
            "RuntimeError: Error encountered when initializing Maya - "
            "Please check for sufficient disk space "
            "and necessary write permissions of MAYA_APP_DIR."
        )
        callback_list = []
        completed_regexes = [_re.compile("MayaClient: Finished Rendering Frame [0-9]+")]
        progress_regexes = [
            _re.compile("\\[PROGRESS\\] ([0-9]+) percent"),
            _re.compile("([0-9]+)% done"),  # arnold
        ]
        error_regexes = [_re.compile(".*Exception:.*|.*Error:.*|.*Warning.*")]

        callback_list.append(_RegexCallback(completed_regexes, self._handle_complete))
        callback_list.append(_RegexCallback(progress_regexes, self._handle_progress))
        if self.init_data.get("strict_error_checking", False):
            callback_list.append(_RegexCallback(error_regexes, self._handle_error))
        if self.init_data.get("error_on_arnold_license_fail", False):
            callback_list.append(
                _RegexCallback(
                    [
                        _re.compile(
                            "(aborting render because the abort_on_license_fail option was enabled)"
                        )
                    ],
                    self._handle_error,
                )
            )
        callback_list.append(
            _RegexCallback(
                [_re.compile(_maya_license_error)],
                self._handle_license_error,
            )
        )

        return callback_list

    @_check_for_exception
    def _handle_complete(self, match: _re.Match) -> None:
        """
        Callback for stdout that indicate completeness of a render. Updates progress to 100
        Args:
            match (re.Match): The match object from the regex pattern that was matched the message
        """
        self._maya_is_rendering = False
        self.update_status(progress=100)

    @_check_for_exception
    def _handle_progress(self, match: _re.Match) -> None:
        """
        Callback for stdout that indicate progress of a render.
        Args:
            match (re.Match): The match object from the regex pattern that was matched the message
        """
        progress = int(match.groups()[0])
        self.update_status(progress=progress)

    def _handle_error(self, match: _re.Match) -> None:
        """
        Callback for stdout that indicates an error or warning.
        Args:
            match (re.Match): The match object from the regex pattern that was matched the message

        Raises:
            RuntimeError: Always raises a runtime error to halt the adaptor.
        """
        self._exc_info = RuntimeError(f"Maya Encountered an Error: {match.group(0)}")

    def _handle_license_error(self, match: _re.Match) -> None:
        """
        Callback for stdout that indicates an license error.
        Args:
            match (re.Match): The match object from the regex pattern that was matched the message

        Raises:
            RuntimeError: Always raises a runtime error to halt the adaptor.
        """
        license_file = _os.environ.get("ADSKFLEX_LICENSE_FILE")
        maya_app_dir = _os.environ.get("MAYA_APP_DIR")
        shutil_usage = _shutil.disk_usage(maya_app_dir or _os.getcwd())
        self._exc_info = RuntimeError(
            f"{match.group(0)}\n"
            "This error is typically associated with a licensing error"
            " when using MayaIO. Check your licensing configuration.\n"
            f"Free disc space: {shutil_usage.free//1024//1024}M\n"
            f"MAYA_APP_DIR: {maya_app_dir}\n"
            f"ADSKFLEX_LICENSE_FILE: {license_file}"
        )

    def _get_maya_client_path(self) -> str:
        """
        Obtains the maya_client.py path by searching directories in sys.path

        Raises:
            FileNotFoundError: If the maya_client.py file could not be found.

        Returns:
            str: The path to the maya_client.py file.
        """
        for dir_ in _sys.path:
            path = _os.path.join(dir_, "deadline_adaptor_for_maya", "MayaClient", "maya_client.py")
            if _os.path.isfile(path):
                return path
        raise FileNotFoundError(
            "Could not find maya_client.py. Check that the MayaClient package is in one of the "
            f"following directories: {_sys.path[1:]}"
        )

    def _add_site_packages_to_pythonpath(self) -> None:
        """
        MayaPy does not include the site-packages directory containing the WorkerAdaptorRuntime in
        its sys.path. As the WorkerAdaptorRuntime site-package dir contains the IPC code we add it
        to the PYTHONPATH so maya can import the IPC code.
        """
        site_package_dir = _os.path.dirname(_os.path.dirname(__file__))
        _os.environ["PYTHONPATH"] = f"{_os.getenv('PYTHONPATH', '')}{_os.pathsep}{site_package_dir}"

    def _start_maya_client(self, maya_version: str) -> None:
        """
        Starts the maya client by launching MayaPy with the maya_client.py file.

        Args:
            maya_version (str): The version of Maya that we are launching.

        Raises:
            FileNotFoundError: If the maya_client.py file could not be found.
            KeyError: If a configuration for the given platform and version does not exist.
        """
        exe_path = self.config.get_executable_path(_platform.system(), maya_version)
        maya_client_path = self._get_maya_client_path()
        regexhandler = _RegexHandler(self._get_regex_callbacks())
        self._add_site_packages_to_pythonpath()
        if self.init_data["renderer"] == "arnold":
            self._setup_arnold_pathmapping()
        self._maya_client = _LoggingSubprocess(
            args=[exe_path, maya_client_path],
            stdout_handler=regexhandler,
            stderr_handler=regexhandler,
        )

    def _populate_action_queue(self) -> None:
        """
        Populates the adaptor server's action queue with actions from the init_data that the Maya
        Client will request and perform. The action must be present in the _FIRST_MAYA_ACTIONS or
        _MAYA_INIT_KEYS set to be added to the action queue.
        """

        # Set up the renderer
        self._action_queue.enqueue_action(
            _Action("renderer", {"renderer": self.init_data["renderer"]})
        )

        # Set up all pathmapping rules
        self._action_queue.enqueue_action(
            _Action(
                "path_mapping",
                {
                    "path_mapping_rules": {
                        rule.source_path: rule.destination_path for rule in self.path_mapping_rules
                    }
                },
            )
        )

        for action_item in _FIRST_MAYA_ACTIONS:
            self._action_queue.enqueue_action(self._action_from_action_item(action_item))

        for action_item in _MAYA_INIT_KEYS:
            if action_item.name in self.init_data:
                self._action_queue.enqueue_action(self._action_from_action_item(action_item))

    def on_start(self) -> None:
        """
        For job stickiness. Will start everything required for the Task. Will be used for all
        SubTasks.

        Raises:
            jsonschema.ValidationError: When init_data fails validation against the adaptor schema.
            jsonschema.SchemaError: When the adaptor schema itself is nonvalid.
            RuntimeError: If Maya did not complete initialization actions due to an exception
            TimeoutError: If Maya did not complete initialization actions due to timing out.
            FileNotFoundError: If the maya_client.py file could not be found.
            KeyError: If a configuration for the given platform and version does not exist.
        """
        cur_dir = _os.path.dirname(__file__)
        schema_dir = _os.path.join(cur_dir, "schemas")
        validators = _AdaptorDataValidators.for_adaptor(schema_dir)
        validators.init_data.validate(self.init_data)

        self.update_status(progress=0, status_message="Initializing Maya")
        self._start_maya_server_thread()
        self._populate_action_queue()

        version = str(float(self.init_data.get("version", 2022)))
        self._start_maya_client(version)

        is_not_timed_out = self._get_timer(self._MAYA_START_TIMEOUT_SECONDS)
        while (
            self._maya_is_running
            and not self._has_exception
            and len(self._action_queue) > 0
            and is_not_timed_out()
        ):
            _time.sleep(0.1)  # busy wait for maya to finish initialization

        if len(self._action_queue) > 0:
            if is_not_timed_out():
                raise RuntimeError(
                    "Maya encountered an error and was not able to complete initialization actions."
                )
            else:
                raise TimeoutError(
                    "Maya did not complete initialization actions in "
                    f"{self._MAYA_START_TIMEOUT_SECONDS} seconds and failed to start."
                )

    def on_run(self, run_data: dict) -> None:
        """
        This starts a render in Maya for the given frame and performs a busy wait until the render
        completes.
        """
        if not self._maya_is_running:
            raise MayaNotRunningError("Cannot render because Maya is not running.")

        cur_dir = _os.path.dirname(__file__)
        schema_dir = _os.path.join(cur_dir, "schemas")
        validators = _AdaptorDataValidators.for_adaptor(schema_dir)
        validators.run_data.validate(run_data)
        self._maya_is_rendering = True
        self._action_queue.enqueue_action(_Action("start_render", {"frame": run_data["frame"]}))
        while self._maya_is_rendering and not self._has_exception:
            _time.sleep(0.1)  # wait for the render to finish

        if not self._maya_is_running and self._maya_client:  # Maya Client will always exist here.
            #  This is always an error case because the Maya Client should still be running and
            #  waiting for the next command. If the thread finished, then we cannot continue
            exit_code = self._maya_client.returncode
            raise RuntimeError(
                "Maya exited early and did not render successfully, please check render logs. "
                f"Exit code {exit_code}"
            )

    def on_end(self) -> None:
        """
        Cleans up the directory containing the arnold pathmapping file
        """
        self._cleanup_arnold_dir()

    def on_cleanup(self):
        """
        Cleans up the adaptor by closing the maya client and adaptor server.
        """
        self._performing_cleanup = True

        self._action_queue.enqueue_action(_Action("close"), front=True)
        is_not_timed_out = self._get_timer(self._MAYA_END_TIMEOUT_SECONDS)
        while self._maya_is_running and is_not_timed_out():
            _time.sleep(0.1)
        if self._maya_is_running and self._maya_client:
            _logger.error(
                "Maya did not complete cleanup actions and failed to gracefully shutdown. "
                "Terminating."
            )
            self._maya_client.terminate()

        if self._server:
            self._server.shutdown()

        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=self._SERVER_END_TIMEOUT_SECONDS)
            if self._server_thread.is_alive():
                _logger.error("Failed to shutdown the Maya Adaptor server.")

        self._cleanup_arnold_dir()
        self._performing_cleanup = False

    def on_cancel(self):
        """
        Cancels the current render if Maya is rendering.
        """
        _logger.info("CANCEL REQUESTED")
        if not self._maya_client or not self._maya_is_running:
            _logger.info("Nothing to cancel because Maya is not running")
            return

        # Terminate immediately since the Maya client does not have a graceful shutdown
        self._maya_client.terminate(grace_time_s=0)

    def _action_from_action_item(self, item: _ActionItem) -> _Action:
        return _Action(
            item.name,
            {
                item.name: self.map_path(self.init_data[item.name])
                if item.requires_path_mapping
                else self.init_data[item.name]
            },
        )

    def _setup_arnold_pathmapping(self):
        """
        If rendering with arnold, additional pathmapping setup must be done as outlined in
        https://arnoldsupport.com/tag/path-mapping/

        This iterates through the path mapping rules to create a JSON file that follows the syntax
        arnold expects:
            {
                "windows": {source: dest},
                "linux": {source: dest},
                "mac": {source: dest},
            }

        Arnold will only look at the rules under the name of the OS currently running.
        Arnold locates the JSON file created by looking at the value of the ARNOLD_PATHMAP
        environment variable, which is set in this function.

        Note that arnold replaces backslashes with forward slashes, so windows paths must be of the
        form 'X:/path' instead of 'X:\\path'
        """

        def get_arnold_osname():
            return "mac" if _OSName() == _OSName.MACOS else _OSName().lower()

        arnold_pathmapping_rules = {
            get_arnold_osname(): {
                rule._pure_source_path.as_posix(): rule._pure_destination_path.as_posix()
                for rule in self.path_mapping_rules
            }
        }

        self._arnold_temp_dir = _tempfile.TemporaryDirectory(prefix="arnold")  # 0o700
        arnold_pathmapping_file = _Path(self._arnold_temp_dir.name) / "arnold_pathmapping.json"

        with secure_open(arnold_pathmapping_file, open_mode="w") as json_file:
            _json.dump(arnold_pathmapping_rules, json_file)

        _os.environ["ARNOLD_PATHMAP"] = str(arnold_pathmapping_file)

    def _cleanup_arnold_dir(self):
        """
        Cleanup the temporary dir.
        """
        if self._arnold_temp_dir is not None:
            self._arnold_temp_dir.cleanup()
        self._arnold_temp_dir = None
