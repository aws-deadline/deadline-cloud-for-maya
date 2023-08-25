# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import os
from logging import getLogger
from pathlib import Path
from typing import Any, Optional
import yaml  # type: ignore[import]
from copy import deepcopy
from dataclasses import dataclass

from deadline.client.job_bundle._yaml import deadline_yaml_dump
from deadline.client.ui.dialogs.submit_job_to_deadline_dialog import (  # pylint: disable=import-error
    SubmitJobToDeadlineDialog,
)
from deadline.client.exceptions import DeadlineOperationError
from PySide2.QtCore import Qt  # pylint: disable=import-error

from . import Animation, Scene  # type: ignore
from .assets import AssetIntrospector
from .data_classes.render_submitter_settings import (
    RenderSubmitterUISettings,
)
from .render_layers import (
    saved_current_render_layer,
    get_current_render_layer_name,
    get_render_layer_display_name,
    set_current_render_layer,
    get_all_renderable_render_layer_names,
    render_setup_include_all_lights,
    LayerSelection,
)
from .cameras import get_renderable_camera_names, ALL_CAMERAS
from .ui.components.scene_settings_tab import SceneSettingsWidget
from deadline.client.job_bundle.submission import FlatAssetReferences

logger = getLogger(__name__)


@dataclass
class RenderLayerData:
    name: str
    display_name: str
    renderer_name: str
    ui_group_label: str
    frames_parameter_name: Optional[str]
    frame_range: str
    renderable_camera_names: list[str]
    output_directories: set[str]


def _get_job_template(
    settings: RenderSubmitterUISettings,
    per_layer_frames_parameters: bool,
    renderers: set[str],
    render_layers: list[RenderLayerData],
    all_layer_selectable_cameras,
    current_layer_selectable_cameras,
) -> dict[str, Any]:
    with open(Path(__file__).parent / "default_maya_job_template.yaml") as f:
        job_template = yaml.safe_load(f)

    # Set the job's name
    job_template["name"] = settings.name

    # If there are multiple frame ranges, split up the Frames parameter by layer
    if per_layer_frames_parameters:
        # Extract the Frames parameter
        frame_param = [param for param in job_template["parameters"] if param["name"] == "Frames"][
            0
        ]
        job_template["parameters"] = [
            param for param in job_template["parameters"] if param["name"] != "Frames"
        ]

        # Create layer-specific Frames parameters
        for layer_data in render_layers:
            layer_frame_param = deepcopy(frame_param)
            layer_frame_param["name"] = layer_data.frames_parameter_name
            layer_frame_param["userInterface"]["groupLabel"] = layer_data.ui_group_label
            job_template["parameters"].append(layer_frame_param)

    # If we're rendering a specific camera, add the Camera job parameter
    if settings.camera_selection != ALL_CAMERAS:
        if settings.render_layer_selection == LayerSelection.ALL:
            selectable_cameras = all_layer_selectable_cameras
        else:
            selectable_cameras = current_layer_selectable_cameras
        camera_param = {
            "name": "Camera",
            "type": "STRING",
            "userInterface": {
                "control": "DROPDOWN_LIST",
                "groupLabel": "Maya Settings",
            },
            "description": "Select which camera to render.",
            "allowedValues": selectable_cameras,
        }
        job_template["parameters"].append(camera_param)

    # Replicate the default step, once per render layer, and adjust its settings
    default_step = job_template["steps"][0]
    job_template["steps"] = []
    for layer_data in render_layers:
        step = deepcopy(default_step)
        job_template["steps"].append(step)

        step["name"] = layer_data.display_name

        parameter_space = step["parameterSpace"]
        # Update the 'Param.Frames' reference in the Frame task parameter
        if layer_data.frames_parameter_name:
            parameter_space["parameters"][0]["range"] = (
                "{{Param." + layer_data.frames_parameter_name + "}}"
            )
        # If we're submitting all cameras, create another parameter space dimension
        if settings.camera_selection == ALL_CAMERAS:
            parameter_space["parameters"].append(
                {
                    "name": "Camera",
                    "type": "STRING",
                    "range": layer_data.renderable_camera_names,
                }
            )
            run_data = step["script"]["embeddedFiles"][0]
            run_data["data"] += "camera: '{{Task.Param.Camera}}'\n"

        # Update the init data of the step
        init_data = step["environments"][0]["script"]["embeddedFiles"][0]
        init_data["data"] = (
            f"renderer: {layer_data.renderer_name}\nrender_layer: {layer_data.display_name}\n"
            + init_data["data"]
        )
        # If a specific camera is selected, link to the Camera parameter
        if settings.camera_selection != ALL_CAMERAS:
            init_data["data"] += "camera: '{{Param.Camera}}'\n"

        # If the renderer is Arnold, add specific parameters for it
        if layer_data.renderer_name == "arnold":
            init_data[
                "data"
            ] += "error_on_arnold_license_fail: {{Param.ArnoldErrorOnLicenseFailure}}\n"

    # If Arnold is one of the renderers, add Arnold-specific parameters
    if "arnold" in renderers:
        job_template["parameters"].append(
            {
                "name": "ArnoldErrorOnLicenseFailure",
                "type": "STRING",
                "userInterface": {
                    "control": "CHECK_BOX",
                    "label": "Error on License Failure",
                    "groupLabel": "Arnold Renderer Settings",
                },
                "description": "Whether to produce an error when there is an Arnold license failure.",
                "default": "false",
                "allowedValues": ["true", "false"],
            }
        )

    # If this developer option is enabled, merge the adaptor_override_environment
    if settings.include_adaptor_wheels:
        with open(Path(__file__).parent / "adaptor_override_environment.yaml") as f:
            override_environment = yaml.safe_load(f)

        # Read DEVELOPMENT.md for instructions to create the wheels directory.
        wheels_path = Path(__file__).parent.parent.parent.parent / "wheels"
        if not wheels_path.exists() and wheels_path.is_dir():
            raise RuntimeError(
                "The Developer Option 'Include Adaptor Wheels' is enabled, but the wheels directory does not exist:\n"
                + str(wheels_path)
            )
        wheels_path_package_names = {
            path.split("-", 1)[0] for path in os.listdir(wheels_path) if path.endswith(".whl")
        }
        if wheels_path_package_names != {"openjobio", "deadline", "deadline_cloud_for_maya"}:
            raise RuntimeError(
                "The Developer Option 'Include Adaptor Wheels' is enabled, but the wheels directory contains the wrong wheels:\n"
                + "Expected: openjobio, deadline, and deadline_cloud_for_maya\n"
                + f"Actual: {wheels_path_package_names}"
            )

        override_adaptor_wheels_param = [
            param
            for param in override_environment["parameters"]
            if param["name"] == "OverrideAdaptorWheels"
        ][0]
        override_adaptor_wheels_param["default"] = str(wheels_path)
        override_adaptor_name_param = [
            param
            for param in override_environment["parameters"]
            if param["name"] == "OverrideAdaptorName"
        ][0]
        override_adaptor_name_param["default"] = "MayaAdaptor"

        # There are no parameter conflicts between these two templates, so this works
        job_template["parameters"].extend(override_environment["parameters"])

        # Add the environment to the end of the template's job environments
        if "environments" not in job_template:
            job_template["environments"] = []
        job_template["environments"].append(override_environment["environment"])

    return job_template


def _get_parameter_values(
    settings: RenderSubmitterUISettings,
    per_layer_frames_parameters: bool,
    renderers: set[str],
    render_layers: list[RenderLayerData],
) -> dict[str, Any]:
    parameter_values = [
        {"name": "deadline:priority", "value": settings.priority},
        {"name": "deadline:targetTaskRunStatus", "value": settings.initial_status},
        {"name": "deadline:maxFailedTasksCount", "value": settings.max_failed_tasks_count},
        {"name": "deadline:maxRetriesPerTask", "value": settings.max_retries_per_task},
    ]

    # Set the Maya scene file value
    parameter_values.append({"name": "MayaSceneFile", "value": Scene.name()})

    if per_layer_frames_parameters:
        for layer_data in render_layers:
            parameter_values.append(
                {
                    "name": layer_data.frames_parameter_name,
                    "value": layer_data.frame_range,
                }
            )
    else:
        if settings.override_frame_range:
            frame_list = settings.frame_list
        else:
            frame_list = render_layers[0].frame_range
        parameter_values.append({"name": "Frames", "value": frame_list})

    # If we're rendering a specific camera, set the Camera parameter value
    if settings.camera_selection != ALL_CAMERAS:
        parameter_values.append({"name": "Camera", "value": settings.camera_selection})

    parameter_values.append({"name": "ProjectPath", "value": settings.project_path})
    parameter_values.append({"name": "OutputFilePath", "value": settings.output_path})
    parameter_values.append(
        {
            "name": "RenderSetupIncludeLights",
            "value": "true" if render_setup_include_all_lights() else "false",
        }
    )

    # Set the Arnold-specific parameter values
    if "arnold" in renderers:
        parameter_values.append(
            {
                "name": "ArnoldErrorOnLicenseFailure",
                "value": "true" if Scene.error_on_arnold_license_fail() else "false",
            }
        )

    # Set the RezPackages parameter value
    if settings.override_rez_packages:
        parameter_values.append({"name": "RezPackages", "value": settings.rez_packages})

    return {"parameterValues": parameter_values}


def show_maya_render_submitter(
    parent, render_settings: RenderSubmitterUISettings, f=Qt.WindowFlags()
) -> "Optional[SubmitJobToDeadlineDialog]":
    # Create a dictionary for the layers, and accumulate data about each layer
    render_layer_names = get_all_renderable_render_layer_names()
    if not render_layer_names:
        raise DeadlineOperationError(
            "No render layer is set as renderable. At least one must be renderable to submit a job."
        )

    render_layers: list[RenderLayerData] = []
    with saved_current_render_layer():
        for render_layer_name in render_layer_names:
            set_current_render_layer(render_layer_name)

            display_name = get_render_layer_display_name(render_layer_name)
            renderer_name = Scene.renderer()
            renderable_camera_names = get_renderable_camera_names()
            output_directories: set[str] = set()
            for camera_name in renderable_camera_names:
                output_directories.update(
                    Scene.get_output_directories(render_layer_name, camera_name)
                )

            render_layers.append(
                RenderLayerData(
                    name=render_layer_name,
                    display_name=display_name,
                    renderer_name=renderer_name,
                    ui_group_label=f"Layer {display_name} Settings ({renderer_name} renderer)",
                    frames_parameter_name=None,
                    frame_range=str(Animation.frame_list()),
                    renderable_camera_names=renderable_camera_names,
                    output_directories=output_directories,
                )
            )

    # Sort the layers by name
    render_layers.sort(key=lambda layer: layer.display_name)

    # Tell the settings tab the selectable cameras when only the current layer is in the job
    current_layer_selectable_cameras = get_renderable_camera_names()
    render_settings.current_layer_selectable_cameras = [ALL_CAMERAS] + sorted(
        current_layer_selectable_cameras
    )

    # Tell the settings tab the selectable cameras when all layers are in the job
    all_layer_selectable_cameras = set(render_layers[0].renderable_camera_names)
    for layer in render_layers:
        all_layer_selectable_cameras = all_layer_selectable_cameras.intersection(
            layer.renderable_camera_names
        )
    render_settings.all_layer_selectable_cameras = [ALL_CAMERAS] + sorted(
        all_layer_selectable_cameras
    )

    def job_bundle_callback(
        widget: SubmitJobToDeadlineDialog,
        settings: RenderSubmitterUISettings,
        job_bundle_dir: str,
        asset_references: FlatAssetReferences,
    ) -> None:
        job_bundle_path = Path(job_bundle_dir)

        # If we're only submitting the current layer, filter our list of layers by that
        if settings.render_layer_selection == LayerSelection.CURRENT:
            current_render_layer_name = get_current_render_layer_name()
            submit_render_layers = [
                layer for layer in render_layers if layer.name == current_render_layer_name
            ]
            if not submit_render_layers:
                raise DeadlineOperationError(
                    f"The current render layer, {current_render_layer_name}, is not set as renderable. It must be renderable to submit as a job."
                )
        else:
            submit_render_layers = render_layers

        # Check if there are multiple frame ranges across the layers
        first_frame_range = submit_render_layers[0].frame_range
        per_layer_frames_parameters = not settings.override_frame_range and any(
            layer.frame_range != first_frame_range for layer in submit_render_layers
        )

        # If there are multiple frame ranges and we're not overriding the range,
        # then we create per-layer Frames parameters.
        if per_layer_frames_parameters:
            for layer_data in submit_render_layers:
                layer_data.frames_parameter_name = f"{layer_data.display_name}Frames"

        renderers: set[str] = {layer_data.renderer_name for layer_data in submit_render_layers}

        job_template = _get_job_template(
            settings,
            per_layer_frames_parameters,
            renderers,
            submit_render_layers,
            all_layer_selectable_cameras,
            current_layer_selectable_cameras,
        )
        parameter_values = _get_parameter_values(
            settings, per_layer_frames_parameters, renderers, submit_render_layers
        )

        with open(job_bundle_path / "template.yaml", "w", encoding="utf8") as f:
            deadline_yaml_dump(job_template, f, indent=1)

        with open(job_bundle_path / "parameter_values.yaml", "w", encoding="utf8") as f:
            deadline_yaml_dump(parameter_values, f, indent=1)

        with open(job_bundle_path / "asset_references.yaml", "w", encoding="utf8") as f:
            deadline_yaml_dump(asset_references.to_dict(), f, indent=1)

        # Save Sticky Settings
        attachments: FlatAssetReferences = widget.job_attachments.attachments
        settings.input_filenames = sorted(attachments.input_filenames)
        settings.input_directories = sorted(attachments.input_directories)
        settings.input_filenames = sorted(attachments.input_filenames)

        settings.to_render_submitter_settings().save()

    auto_detected_attachments = FlatAssetReferences()
    introspector = AssetIntrospector()
    auto_detected_attachments.input_filenames = set(
        os.path.normpath(path) for path in introspector.parse_scene_assets()
    )

    for layer_data in render_layers:
        auto_detected_attachments.output_directories.update(layer_data.output_directories)

    attachments = FlatAssetReferences(
        input_filenames=set(render_settings.input_filenames),
        input_directories=set(render_settings.input_directories),
        output_directories=set(render_settings.output_directories),
    )

    submitter_dialog = SubmitJobToDeadlineDialog(
        SceneSettingsWidget,
        render_settings,
        auto_detected_attachments,
        attachments,
        job_bundle_callback,
        parent=parent,
        f=f,
    )

    submitter_dialog.show()
    return submitter_dialog
