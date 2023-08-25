# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

from .. import Animation, Scene  # type: ignore
from ..cameras import ALL_CAMERAS
from ..persistent_dataclass import PersistentDataclass
from ..render_layers import LayerSelection  # type: ignore

RENDER_SUBMITTER_SETTINGS_FILE_EXT = ".deadline_render_settings.json"
REZ_PACKAGES_DEFAULT = "mayaIO mtoa deadline_cloud_for_maya"


@dataclass
class RenderSubmitterUISettings:
    """
    Settings that the submitter UI will use
    """

    submitter_name: str = field(default="Maya")
    name: str = field(default_factory=lambda: Path(Scene.name()).name if Scene.name() else "")
    description: str = field(default="")
    initial_status: str = field(default="READY")
    max_failed_tasks_count: int = field(default=20)
    max_retries_per_task: int = field(default=5)
    priority: int = field(default=50)
    override_frame_range: bool = field(default=False)
    frame_list: str = field(default_factory=lambda: str(Animation.frame_list()))
    project_path: str = field(default_factory=Scene.project_path)
    output_path: str = field(default_factory=Scene.output_path)
    override_rez_packages: bool = field(default=True)
    rez_packages: str = field(default=REZ_PACKAGES_DEFAULT)

    input_filenames: list[str] = field(default_factory=list)
    input_directories: list[str] = field(default_factory=list)
    output_directories: list[str] = field(default_factory=list)

    render_layer_selection: LayerSelection = field(default=LayerSelection.ALL)
    all_layer_selectable_cameras: list[str] = field(default_factory=lambda: [ALL_CAMERAS])
    current_layer_selectable_cameras: list[str] = field(default_factory=lambda: [ALL_CAMERAS])
    camera_selection: str = field(default=ALL_CAMERAS)

    # developer options
    include_adaptor_wheels: bool = False

    def to_render_submitter_settings(self) -> "RenderSubmitterSettings":
        return RenderSubmitterSettings(
            name=self.name,
            description=self.description,
            override_frame_range=self.override_frame_range,
            frame_list=self.frame_list,
            override_rez_packages=self.override_rez_packages,
            rez_packages=self.rez_packages,
            input_filenames=self.input_filenames,
            input_directories=self.input_directories,
            output_directories=self.output_directories,
            render_layer_selection=self.render_layer_selection,
            camera_selection=self.camera_selection,
            initial_status=self.initial_status,
            max_failed_tasks_count=self.max_failed_tasks_count,
            max_retries_per_task=self.max_retries_per_task,
            priority=self.priority,
            include_adaptor_wheels=self.include_adaptor_wheels,
        )

    def apply_saved_settings(self, settings: "RenderSubmitterSettings") -> None:
        self.name = settings.name
        self.description = settings.description
        self.override_frame_range = settings.override_frame_range
        self.frame_list = settings.frame_list
        self.override_rez_packages = settings.override_rez_packages
        self.rez_packages = settings.rez_packages
        self.input_filenames = settings.input_filenames
        self.input_directories = settings.input_directories
        self.output_directories = settings.output_directories
        self.render_layer_selection = settings.render_layer_selection
        self.camera_selection = settings.camera_selection
        self.initial_status = settings.initial_status
        self.max_failed_tasks_count = settings.max_failed_tasks_count
        self.max_retries_per_task = settings.max_retries_per_task
        self.priority = settings.priority
        self.include_adaptor_wheels = settings.include_adaptor_wheels


@dataclass
class RenderSubmitterSettings(PersistentDataclass):  # pylint: disable=too-many-instance-attributes
    """
    Global settings for the Render Submitter
    """

    name: str = field(default_factory=lambda: Path(Scene.name()).name if Scene.name() else "")
    description: str = field(default="")
    initial_status: str = field(default="READY")
    max_failed_tasks_count: int = field(default=20)
    max_retries_per_task: int = field(default=5)
    priority: int = field(default=50)
    override_frame_range: bool = field(default=False)
    frame_list: str = field(default_factory=lambda: str(Animation.frame_list()))
    override_rez_packages: bool = field(default=True)
    rez_packages: str = field(default=REZ_PACKAGES_DEFAULT)

    input_filenames: list[str] = field(default_factory=list)
    input_directories: list[str] = field(default_factory=list)
    output_directories: list[str] = field(default_factory=list)

    render_layer_selection: LayerSelection = field(default=LayerSelection.ALL)
    camera_selection: str = field(default=ALL_CAMERAS)

    # developer options
    include_adaptor_wheels: bool = False

    @classmethod
    def instantiate(cls, data: Dict[str, Any]):
        return RenderSubmitterSettings(**data)

    @classmethod
    def file_path(cls) -> Path:
        return (
            Path(Scene.name()).with_suffix(RENDER_SUBMITTER_SETTINGS_FILE_EXT)
            if Path(Scene.name()).stem
            else Path(RENDER_SUBMITTER_SETTINGS_FILE_EXT)
        )
