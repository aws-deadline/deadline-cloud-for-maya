# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import os as _os
from types import FrameType as _FrameType
from typing import Optional as _Optional

from openjobio_adaptor_runtime_client import HTTPClientInterface as _HTTPClientInterface

from deadline_adaptor_for_maya.MayaClient.render_handlers.get_render_handler import (
    get_render_handler as _get_render_handler,
)


class MayaClient(_HTTPClientInterface):
    def __init__(self, socket_path: str) -> None:
        super().__init__(socket_path=socket_path)
        self.actions.update(
            {
                "renderer": self.set_renderer,
            }
        )

    def set_renderer(self, renderer: dict):
        render_handler = _get_render_handler(renderer["renderer"])
        self.actions.update(render_handler.action_dict)

    def close(self, args: _Optional[dict] = None) -> None:
        return

    def graceful_shutdown(self, signum: int, frame: _FrameType | None):
        return


def main():
    socket_path = _os.environ.get("MAYA_ADAPTOR_SOCKET_PATH")
    if not socket_path:
        raise OSError(
            "MayaClient cannot connect to the Adaptor because the environment variable "
            "MAYA_ADAPTOR_SOCKET_PATH does not exist"
        )

    if not _os.path.exists(socket_path):
        raise OSError(
            "MayaClient cannot connect to the Adaptor because the socket at the path defined by "
            "the environment variable MAYA_ADAPTOR_SOCKET_PATH does not exist. Got: "
            f"{_os.environ['MAYA_ADAPTOR_SOCKET_PATH']}"
        )

    client = MayaClient(socket_path)
    client.poll()


if __name__ == "__main__":  # pragma: no cover
    main()
