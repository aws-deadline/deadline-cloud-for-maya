# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import os
from types import FrameType
from typing import Optional

# The Maya Adaptor adds the `openjd` namespace directory to PYTHONPATH,
# so that importing just the adaptor_runtime_client should work.
try:
    from adaptor_runtime_client import HTTPClientInterface  # type: ignore[import]
except (ImportError, ModuleNotFoundError):
    try:
        from openjd.adaptor_runtime_client import HTTPClientInterface  # type: ignore[import]
    except (ImportError, ModuleNotFoundError):
        # TODO: Remove this try/except once we bump to openjd.adaptor_runtime_client 0.9+
        # On Windows, HTTPClientInterface is not available, only ClientInterface
        from openjd.adaptor_runtime_client import ClientInterface as HTTPClientInterface  # type: ignore[import]


try:
    from maya_adaptor.MayaClient.render_handlers import (  # type: ignore[import]
        get_render_handler,
    )
except (ImportError, ModuleNotFoundError):
    from deadline.maya_adaptor.MayaClient.render_handlers import (  # type: ignore[import]
        get_render_handler,
    )


class MayaClient(HTTPClientInterface):
    def __init__(self, server_path: str) -> None:
        super().__init__(server_path=server_path)
        self.actions.update(
            {
                "renderer": self.set_renderer,
            }
        )
        import maya.standalone
        import maya.cmds

        maya.standalone.initialize()
        print(f"MayaClient: Maya Version {maya.cmds.about(version=True)}")

    def set_renderer(self, renderer: dict):
        render_handler = get_render_handler(renderer["renderer"])
        self.actions.update(render_handler.action_dict)

    def close(self, args: Optional[dict] = None) -> None:
        import maya.standalone

        maya.standalone.uninitialize()

    def graceful_shutdown(self, signum: int, frame: FrameType | None):
        import maya.standalone

        maya.standalone.uninitialize()


def main():
    server_path = os.environ.get("MAYA_ADAPTOR_SERVER_PATH")
    if not server_path:
        raise OSError(
            "MayaClient cannot connect to the Adaptor because the environment variable "
            "MAYA_ADAPTOR_SERVER_PATH does not exist"
        )

    if not os.path.exists(server_path):
        raise OSError(
            "MayaClient cannot connect to the Adaptor because the socket at the path defined by "
            "the environment variable MAYA_ADAPTOR_SERVER_PATH does not exist. Got: "
            f"{os.environ['MAYA_ADAPTOR_SERVER_PATH']}"
        )

    client = MayaClient(server_path)
    client.poll()


if __name__ == "__main__":  # pragma: no cover
    main()
