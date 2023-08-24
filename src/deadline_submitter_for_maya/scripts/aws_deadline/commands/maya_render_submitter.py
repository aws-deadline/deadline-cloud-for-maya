# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

from dataclasses import dataclass, field
from logging import getLogger
from pathlib import Path
from typing import Any, Optional, Sequence, Union

import pymel.core as pmc  # pylint: disable=import-error
from deadline.client.job_bundle._yaml import deadline_yaml_dump
from deadline.client.job_bundle.adaptors import (
    get_asset_references,
    get_dcc_in_background_environment,
    get_rez_environment,
    get_step,
    write_job_bundle,
)
from deadline.client.ui.dialogs.submit_job_to_deadline_dialog import (  # pylint: disable=import-error
    SubmitJobToDeadlineDialog,
)
from PySide2.QtCore import Qt  # pylint: disable=import-error

from .. import Scene  # type: ignore
from ..assets import AssetIntrospector
from ..cameras import Camera, CameraSelection
from ..data_classes.render_submitter_settings import (
    INSTALLATION_REQUIREMENTS_DEFAULT,
    RenderSubmitterUISettings,
)
from ..render_layers import LayerSelection, RenderLayer
from ..renderers import current_renderer  # type: ignore
from ..ui.components.scene_settings_tab import SceneSettingsWidget

logger = getLogger(__name__)


@dataclass
class LayerCameraCombo:
    """
    Context object for determining building up a job.
    """

    layer: RenderLayer
    camera: Optional[Camera] = field(default=None)

    @property
    def name(self):
        """
        Generate a name for this part of the submission
        """
        components = [("Layer", self.layer.display_name)]
        if self.camera:
            components.append(("Camera", self.camera.name))

        return "-".join(f"{c}:{v}" for c, v in components)


def _get_render_layers(settings: RenderSubmitterUISettings) -> list[RenderLayer]:
    if settings.render_layer_selection == LayerSelection.ALL:
        render_layers = RenderLayer.get_all_layers()
    else:
        render_layers = [RenderLayer.get_current_layer()]

    render_layers = [layer for layer in render_layers if layer.renderable]

    if len(render_layers) == 0:
        logger.error("Failed to submit render jobs.  No Renderable Layers found")

    return render_layers


def _get_layer_camera_combos(settings: RenderSubmitterUISettings) -> list[LayerCameraCombo]:
    render_layers: list[RenderLayer] = _get_render_layers(settings)
    layer_camera_combos = []

    for layer in render_layers:
        with layer.activate():
            cameras: Sequence[Union[Camera, None]] = [None]
            if settings.camera_selection == CameraSelection.SEPARATE:
                cameras = Camera.get_renderable_cameras()

            for cam in cameras:
                layer_camera_combos.append(LayerCameraCombo(layer, cam))

    return layer_camera_combos


def _get_init_data_attachment(
    settings: RenderSubmitterUISettings, layer_camera_combo: LayerCameraCombo
) -> dict[str, Any]:
    renderer = current_renderer()
    plugin_settings = {
        "animation": Scene.Animation.activated(),
        "render_setup_include_lights": RenderLayer.contains_all_lights(),
        "renderer": renderer.name,
        "render_layer": layer_camera_combo.layer.name,
        "strict_error_checking": False,
        "version": int(pmc.versions.shortName()),
        "output_file_path": settings.output_path,
        "project_path": settings.project_path,
        "scene_file": Scene.name(),
        "camera": layer_camera_combo.camera.name if layer_camera_combo.camera else "",
    }
    if renderer.name == "arnold":
        plugin_settings["error_on_arnold_license_fail"] = Scene.error_on_arnold_license_fail()
    plugin_settings.update(renderer.get_plugin_settings(layer_camera_combo))
    data = deadline_yaml_dump(plugin_settings, indent=2)
    return {
        "name": "initData",
        "type": "TEXT",
        "data": data,
    }


def _get_job_template(
    settings: RenderSubmitterUISettings, layer_camera_combos: list[LayerCameraCombo]
) -> dict[str, Any]:
    frame_list = (
        settings.frame_list if settings.override_frame_range else str(Scene.Animation.frame_list())
    )

    installation_requirements = (
        settings.installation_requirements
        if settings.override_installation_requirements
        else INSTALLATION_REQUIREMENTS_DEFAULT
    ).split(" ")

    steps: list[dict[str, Any]] = []
    for layer_camera_combo in layer_camera_combos:
        environments = [
            get_rez_environment(installation_requirements),
            get_dcc_in_background_environment(
                "Maya", _get_init_data_attachment(settings, layer_camera_combo)
            ),
        ]
        steps.append(get_step("Maya", layer_camera_combo.name, frame_list, environments))

    return {"specificationVersion": "2022-09-01", "name": settings.name, "steps": steps}


def _get_parameter_values(settings: RenderSubmitterUISettings) -> dict[str, Any]:
    return {
        "parameterValues": [
            {"name": "deadline:priority", "value": settings.priority},
            {"name": "deadline:targetTaskRunStatus", "value": settings.initial_state},
            {"name": "deadline:maxFailedTasksCount", "value": settings.failed_tasks_limit},
            {"name": "deadline:maxRetriesPerTask", "value": settings.task_retry_limit},
        ]
    }


def show_maya_render_submitter(
    parent, render_settings: RenderSubmitterUISettings, f=Qt.WindowFlags()
) -> "Optional[SubmitJobToDeadlineDialog]":
    def get_scene_assets():
        introspector = AssetIntrospector()
        if render_settings.input_asset_paths:
            return list(
                set(introspector.parse_scene_assets()).union(render_settings.input_asset_paths)
            )
        return list(introspector.parse_scene_assets())

    def submission_callback(
        widget: SubmitJobToDeadlineDialog,
        settings: RenderSubmitterUISettings,
        job_bundle_dir: str,
        asset_references: dict[str, Any],
    ) -> None:
        job_bundle_path = Path(job_bundle_dir)
        layer_camera_combos = _get_layer_camera_combos(settings)
        job_template = _get_job_template(settings, layer_camera_combos)
        parameter_values = _get_parameter_values(settings)

        output_directories: set[str] = set()
        for layer_camera_combo in layer_camera_combos:
            camera_name = layer_camera_combo.camera.name if layer_camera_combo.camera else ""
            output_directories.update(
                current_renderer().get_output_directories(
                    layer_camera_combo.layer.name, camera_name
                )
            )
        asset_references = get_asset_references(output_directories, asset_references)
        write_job_bundle(job_bundle_path, job_template, parameter_values, asset_references)

        # Save the settings for sticky settings
        settings.input_job_outputs = (
            asset_references["assetReferences"]["outputs"]["directories"]
            + asset_references["assetReferences"]["outputs"]["filenames"]
        )
        settings.input_asset_paths = (
            asset_references["assetReferences"]["inputs"]["directories"]
            + asset_references["assetReferences"]["inputs"]["filenames"]
        )
        settings.to_render_submitter_settings().save()

    submitter_dialog = SubmitJobToDeadlineDialog(
        SceneSettingsWidget,
        render_settings,
        get_scene_assets,
        submission_callback,
        parent=parent,
        f=f,
    )

    submitter_dialog.show()
    return submitter_dialog
