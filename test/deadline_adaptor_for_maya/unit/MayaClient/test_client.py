# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
from unittest.mock import Mock, patch

import pytest

from deadline.maya_adaptor.MayaClient.maya_client import MayaClient, main


class TestMayaClient:
    @patch("deadline.maya_adaptor.MayaClient.maya_client.HTTPClientInterface")
    def test_mayaclient(self, mock_httpclient: Mock) -> None:
        """Tests that the maya client can initialize, set a renderer and close"""
        client = MayaClient(server_path=str(9999))
        client.set_renderer({"renderer": "mayaSoftware"})
        client.close()

    @patch("deadline.maya_adaptor.MayaClient.maya_client.os.path.exists")
    @patch.dict(os.environ, {"MAYA_ADAPTOR_SERVER_PATH": "server_path"})
    @patch("deadline.maya_adaptor.MayaClient.MayaClient.poll")
    @patch("deadline.maya_adaptor.MayaClient.maya_client.HTTPClientInterface")
    def test_main(self, mock_httpclient: Mock, mock_poll: Mock, mock_exists: Mock) -> None:
        """Tests that the main method starts the maya client polling method"""
        # GIVEN
        mock_exists.return_value = True

        # WHEN
        main()

        # THEN
        mock_exists.assert_called_once_with("server_path")
        mock_poll.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    @patch("deadline.maya_adaptor.MayaClient.MayaClient.poll")
    def test_main_no_server_socket(self, mock_poll: Mock) -> None:
        """Tests that the main method raises an OSError if no server socket is found"""
        # WHEN
        with pytest.raises(OSError) as exc_info:
            main()

        # THEN
        assert str(exc_info.value) == (
            "MayaClient cannot connect to the Adaptor because the environment variable "
            "MAYA_ADAPTOR_SERVER_PATH does not exist"
        )
        mock_poll.assert_not_called()

    @patch.dict(os.environ, {"MAYA_ADAPTOR_SERVER_PATH": "/a/path/that/does/not/exist"})
    @patch("deadline.maya_adaptor.MayaClient.maya_client.os.path.exists")
    @patch("deadline.maya_adaptor.MayaClient.MayaClient.poll")
    def test_main_server_socket_not_exists(self, mock_poll: Mock, mock_exists: Mock) -> None:
        """Tests that the main method raises an OSError if the server socket does not exist"""
        # GIVEN
        mock_exists.return_value = False

        # WHEN
        with pytest.raises(OSError) as exc_info:
            main()

        # THEN
        mock_exists.assert_called_once_with(os.environ["MAYA_ADAPTOR_SERVER_PATH"])
        assert str(exc_info.value) == (
            "MayaClient cannot connect to the Adaptor because the socket at the path defined by "
            "the environment variable MAYA_ADAPTOR_SERVER_PATH does not exist. Got: "
            f"{os.environ['MAYA_ADAPTOR_SERVER_PATH']}"
        )
        mock_poll.assert_not_called()
