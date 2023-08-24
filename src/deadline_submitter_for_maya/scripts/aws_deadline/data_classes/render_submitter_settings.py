# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .. import Scene  # type: ignore
from ..cameras import CameraSelection  # type: ignore
from ..persistent_dataclass import PersistentDataclass
from ..render_layers import LayerSelection  # type: ignore

RENDER_SUBMITTER_SETTINGS_FILE_EXT = ".deadline_render_settings.json"
INSTALLATION_REQUIREMENTS_DEFAULT = "mayaIO mtoa deadline_maya"


@dataclass
class RenderSubmitterUISettings:
    """
    Settings that the submitter UI will use
    """

    submitter_name: str = field(default="Maya")
    name: str = field(default_factory=lambda: Path(Scene.name()).name if Scene.name() else "")
    description: str = field(default="")
    initial_state: str = field(default="READY")
    failed_tasks_limit: int = field(default=100)
    task_retry_limit: int = field(default=5)
    priority: int = field(default=50)
    override_frame_range: bool = field(default=False)
    frame_list: str = field(default_factory=lambda: str(Scene.Animation.frame_list()))
    project_path: str = field(default_factory=Scene.project_path)
    output_path: str = field(default_factory=Scene.output_path)
    override_installation_requirements: bool = field(default=True)
    installation_requirements: str = field(default=INSTALLATION_REQUIREMENTS_DEFAULT)

    input_asset_paths: List[str] = field(default_factory=list)
    input_job_outputs: List[str] = field(default_factory=list)
    render_layer_selection: LayerSelection = field(default=LayerSelection.ALL)
    camera_selection: CameraSelection = field(default=CameraSelection.SEPARATE)

    def to_render_submitter_settings(self) -> "RenderSubmitterSettings":
        return RenderSubmitterSettings(
            name=self.name,
            description=self.description,
            override_frame_range=self.override_frame_range,
            frame_list=self.frame_list,
            override_installation_requirements=self.override_installation_requirements,
            input_asset_paths=self.input_asset_paths,
            input_job_outputs=self.input_job_outputs,
            render_layer_selection=self.render_layer_selection,
            camera_selection=self.camera_selection,
            initial_state=self.initial_state,
            failed_tasks_limit=self.failed_tasks_limit,
            task_retry_limit=self.task_retry_limit,
            priority=self.priority,
        )

    def apply_saved_settings(self, settings: "RenderSubmitterSettings") -> None:
        self.name = settings.name
        self.description = settings.description
        self.override_frame_range = settings.override_frame_range
        self.frame_list = settings.frame_list
        self.override_installation_requirements = settings.override_installation_requirements
        self.installation_requirements = settings.installation_requirements
        self.input_asset_paths = settings.input_asset_paths
        self.input_job_outputs = settings.input_job_outputs
        self.render_layer_selection = settings.render_layer_selection
        self.camera_selection = settings.camera_selection
        self.initial_state = settings.initial_state
        self.failed_tasks_limit = settings.failed_tasks_limit
        self.task_retry_limit = settings.task_retry_limit
        self.priority = settings.priority


@dataclass
class RenderSubmitterSettings(PersistentDataclass):  # pylint: disable=too-many-instance-attributes
    """
    Global settings for the Render Submitter
    """

    name: str = field(default_factory=lambda: Path(Scene.name()).name if Scene.name() else "")
    description: str = field(default="")
    initial_state: str = field(default="READY")
    failed_tasks_limit: int = field(default=100)
    task_retry_limit: int = field(default=5)
    priority: int = field(default=50)
    override_frame_range: bool = field(default=False)
    frame_list: str = field(default_factory=lambda: str(Scene.Animation.frame_list()))
    override_installation_requirements: bool = field(default=True)
    installation_requirements: str = field(default=INSTALLATION_REQUIREMENTS_DEFAULT)

    input_asset_paths: List[str] = field(default_factory=list)
    input_job_outputs: List[str] = field(default_factory=list)
    render_layer_selection: LayerSelection = field(default=LayerSelection.ALL)
    camera_selection: CameraSelection = field(default=CameraSelection.SEPARATE)

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
