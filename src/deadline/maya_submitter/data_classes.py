# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
import json

from deadline.client.ui.dataclasses.timeouts import TimeoutEntry, TimeoutTableEntries
from datetime import timedelta
from .cameras import ALL_CAMERAS
from .render_layers import LayerSelection  # type: ignore

RENDER_SUBMITTER_SETTINGS_FILE_EXT = ".deadline_render_settings.json"


def default_time_entries() -> TimeoutTableEntries:
    entries = {
        "Task Run": TimeoutEntry(
            tooltip="Maximum duration for a task to run or for rendering a frame",
            seconds=int(timedelta(days=2).total_seconds()),
            is_activated=False,  # The default maya job template doesn't have timeout for task run
        ),
        "Maya Launch": TimeoutEntry(
            tooltip="Maximum duration for Maya to start",
            seconds=87000,  # comes from the default_maya_job_template
            is_activated=True,
        ),
        "Maya Shutdown": TimeoutEntry(
            tooltip="Maximum duration for Maya to shutdown",
            seconds=600,
            is_activated=True,  # comes from the default_maya_job_template
        ),
    }
    return TimeoutTableEntries(entries=entries)


@dataclass
class RenderSubmitterUISettings:
    """
    Settings that the submitter UI will use
    """

    submitter_name: str = field(default="Maya")

    name: str = field(default="", metadata={"sticky": True})
    description: str = field(default="", metadata={"sticky": True})

    priority: int = field(default=50, metadata={"sticky": True})
    initial_status: str = field(default="READY", metadata={"sticky": True})
    max_failed_tasks_count: int = field(default=20, metadata={"sticky": True})
    max_retries_per_task: int = field(default=5, metadata={"sticky": True})
    max_worker_count: int = field(
        default=-1, metadata={"sticky": True}
    )  # -1 indicates unlimited max worker count

    override_frame_range: bool = field(default=False, metadata={"sticky": True})
    frame_list: str = field(default="", metadata={"sticky": True})
    project_path: str = field(default="")
    output_path: str = field(default="")

    # field and property can't have the same name
    _timeouts: TimeoutTableEntries = field(
        default_factory=default_time_entries,
        metadata={"sticky": True, "sticky_key": "timeouts", "sticky_save_attr": "_timeouts_sticky"},
    )

    input_filenames: list[str] = field(default_factory=list, metadata={"sticky": True})
    input_directories: list[str] = field(default_factory=list, metadata={"sticky": True})
    output_directories: list[str] = field(default_factory=list, metadata={"sticky": True})

    render_layer_selection: LayerSelection = field(default=LayerSelection.ALL)
    all_layer_selectable_cameras: list[str] = field(default_factory=lambda: [ALL_CAMERAS])
    current_layer_selectable_cameras: list[str] = field(default_factory=lambda: [ALL_CAMERAS])
    camera_selection: str = field(default=ALL_CAMERAS)

    # developer options
    include_adaptor_wheels: bool = field(default=False, metadata={"sticky": True})

    @property
    def timeouts(self) -> TimeoutTableEntries:
        return self._timeouts

    @timeouts.setter
    def timeouts(self, value: "TimeoutTableEntries | dict") -> None:
        # A setter for timeouts. The value used to set timeouts can either be a TimeoutTableEntries or a dict
        if isinstance(value, dict):
            self._timeouts.update_from_sticky_settings(value)
        else:
            self._timeouts = value

    @property
    def _timeouts_sticky(self) -> dict:
        # Serialized form used when writing sticky settings
        return self._timeouts.to_sticky_settings_dict()

    def load_sticky_settings(self, scene_filename: str):
        sticky_settings_filename = Path(scene_filename).with_suffix(
            RENDER_SUBMITTER_SETTINGS_FILE_EXT
        )
        if sticky_settings_filename.exists() and sticky_settings_filename.is_file():
            try:
                with open(sticky_settings_filename, encoding="utf8") as fh:
                    sticky_settings = json.load(fh)

                if isinstance(sticky_settings, dict):
                    sticky_keys = {
                        # either get sticky_key for non_primitive that is supported by @property
                        # or field.name for primitive
                        field.metadata.get("sticky_key", field.name)
                        for field in dataclasses.fields(self)
                        if field.metadata.get("sticky")
                    }
                    for name, value in sticky_settings.items():
                        if name in sticky_keys:
                            setattr(self, name, value)
            except (OSError, json.JSONDecodeError):
                # If something bad happened to the sticky settings file,
                # just use the defaults instead of producing an error.
                import traceback

                traceback.print_exc()
                print(
                    f"WARNING: Failed to load sticky settings file {sticky_settings_filename}, reverting to the default settings."
                )
                pass

    def save_sticky_settings(self, scene_filename: str):
        sticky_settings_filename = Path(scene_filename).with_suffix(
            RENDER_SUBMITTER_SETTINGS_FILE_EXT
        )
        with open(sticky_settings_filename, "w", encoding="utf8") as fh:
            obj = {
                field.metadata.get("sticky_key", field.name): getattr(
                    self, field.metadata.get("sticky_save_attr", field.name)
                )
                for field in dataclasses.fields(self)
                if field.metadata.get("sticky")
            }
            json.dump(obj, fh, indent=1)
