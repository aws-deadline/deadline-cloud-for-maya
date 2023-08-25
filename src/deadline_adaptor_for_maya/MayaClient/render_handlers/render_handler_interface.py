# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from abc import ABC as _ABC
from abc import abstractmethod as _abstractmethod
from typing import Any as _Any
from typing import Callable as _Callable
from typing import Dict as _Dict


class RenderHandlerInterface(_ABC):
    action_dict: _Dict[str, _Callable[[_Dict[str, _Any]], None]] = {}

    def __init__(self):
        self.action_dict = {
            "start_render": self.start_render,
            "animation": self.set_animation,
            "camera": self.set_camera,
            "image_height": self.set_image_height,
            "image_width": self.set_image_width,
            "output_file_path": self.set_output_file_path,
            "output_file_prefix": self.set_output_file_prefix,
            "path_mapping": self.set_path_mapping,
            "project_path": self.set_project_path,
            "render_layer": self.set_render_layer,
            "render_setup_include_lights": self.set_render_setup_include_lights,
            "scene_file": self.set_scene_file,
        }

    @_abstractmethod
    def start_render(self, data: dict) -> None:
        """
        Starts a render in Maya.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['frame']
        """
        pass  # pragma: no cover

    @_abstractmethod
    def set_animation(self, data: dict) -> None:
        """
        Sets the Animation flag in maya

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['animation']
        """
        pass  # pragma: no cover

    @_abstractmethod
    def set_camera(self, data: dict) -> None:
        """
        Sets the Camera that will be renderered.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['camera']
        """
        pass  # pragma: no cover

    @_abstractmethod
    def set_image_height(self, data: dict) -> None:
        """
        Sets the image height.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['image_height']
        """
        pass  # pragma: no cover

    @_abstractmethod
    def set_image_width(self, data: dict) -> None:
        """
        Sets the image width.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['image_width']
        """
        pass  # pragma: no cover

    @_abstractmethod
    def set_output_file_path(self, data: dict) -> None:
        """
        Sets the output file path.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['output_file_path']
        """
        pass  # pragma: no cover

    @_abstractmethod
    def set_output_file_prefix(self, data: dict) -> None:
        """
        Sets the output file prefix.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['output_file_prefix']
        """
        pass  # pragma: no cover

    @_abstractmethod
    def set_path_mapping(self, data: dict):
        """
        Applies pathmapping within Maya.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['path_mapping_rules']
        """
        raise NotImplementedError  # pragma: no cover

    @_abstractmethod
    def set_project_path(self, data: dict) -> None:
        """
        Sets the project path.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['project_path']
        """
        pass  # pragma: no cover

    @_abstractmethod
    def set_render_layer(self, data: dict) -> None:
        """
        Sets the render layer.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['render_layer']

        Raises:
            RuntimeError: _description_
        """
        pass  # pragma: no cover

    @_abstractmethod
    def set_render_setup_include_lights(self, data: dict) -> None:
        """
        Sets the renderSetup_includeAllLights flag.

        Args:
            data (dict): The data given from the Adaptor. Keys expected:
                ['render_setup_include_lights']
        """
        pass  # pragma: no cover

    @_abstractmethod
    def set_scene_file(self, data: dict) -> None:
        """Opens a scene file in maya.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['scene_file']

        Raises:
            FileNotFoundError: If the file provided in the data dictionary does not exist.
        """
        pass  # pragma: no cover
