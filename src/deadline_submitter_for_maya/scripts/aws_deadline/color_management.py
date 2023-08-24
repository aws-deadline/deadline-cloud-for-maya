# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Helper functions for retiriving maya color management preferences.
"""
from pymel.core.nodetypes import ColorManagementGlobals as pm_Color  # pylint: disable=import-error


class ColorManagement:
    """
    Class used to represent all color management settings of Maya.
    """

    def __init__(self) -> None:
        self._node = pm_Color()

    def config_file_activated(self) -> bool:
        """
        Returns whether or not the OCIO Config file should be used.
        (Machine Level Setting)
        """
        return self._node.configFilePath.get().configFileEnabled.get()

    def config_file_path(self) -> str:
        """
        Returns Maya's OCIO Config file Path.
        (Machine Level Setting)
        """
        return self._node.configFilePath.get()
