# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

RENDER_SUBMITTER_SETTINGS_FILE_EXT = ".deadline_render_settings.json"
INSTALLATION_REQUIREMENTS_DEFAULT = "renderman deadline-cloud-for-renderman"


@dataclass
class RenderSubmitterUISettings:
    """
    Settings that the submitter UI will use
    """

    submitter_name: str = field(default="RenderMan")
    name: str = ""
    description: str = field(default="")
    initial_status: str = field(default="READY")
    failed_tasks_limit: int = field(default=100)
    task_retry_limit: int = field(default=5)
    priority: int = field(default=50)
    rib_file_paths: str = ""
    continue_on_error = "false"
    override_installation_requirements: bool = field(default=True)
    installation_requirements: str = field(default=INSTALLATION_REQUIREMENTS_DEFAULT)

    input_asset_paths: List[str] = field(default_factory=list)
    input_job_outputs: List[str] = field(default_factory=list)

    include_adaptor_wheels: bool = field(default=False)

    def to_render_submitter_settings(self) -> "RenderSubmitterSettings":
        return RenderSubmitterSettings(
            name=self.name,
            description=self.description,
            override_installation_requirements=self.override_installation_requirements,
            input_asset_paths=self.input_asset_paths,
            input_job_outputs=self.input_job_outputs,
            failed_tasks_limit=self.failed_tasks_limit,
            task_retry_limit=self.task_retry_limit,
            priority=self.priority,
        )

    def apply_saved_settings(self, settings: "RenderSubmitterSettings") -> None:
        self.name = settings.name
        self.description = settings.description
        self.override_installation_requirements = settings.override_installation_requirements
        self.installation_requirements = settings.installation_requirements
        self.input_asset_paths = settings.input_asset_paths
        self.input_job_outputs = settings.input_job_outputs
        self.failed_tasks_limit = settings.failed_tasks_limit
        self.task_retry_limit = settings.task_retry_limit
        self.priority = settings.priority


#PersistentDataclass
@dataclass
class RenderSubmitterSettings:  # pylint: disable=too-many-instance-attributes
    """
    Global settings for the Render Submitter
    """

    name: str = ""
    description: str = field(default="")
    initial_state: str = field(default="READY")
    failed_tasks_limit: int = field(default=100)
    task_retry_limit: int = field(default=5)
    priority: int = field(default=50)
    override_installation_requirements: bool = field(default=True)
    installation_requirements: str = field(default=INSTALLATION_REQUIREMENTS_DEFAULT)

    input_asset_paths: List[str] = field(default_factory=list)
    input_job_outputs: List[str] = field(default_factory=list)

    @classmethod
    def instantiate(cls, data: Dict[str, Any]):
        return RenderSubmitterSettings(**data)

