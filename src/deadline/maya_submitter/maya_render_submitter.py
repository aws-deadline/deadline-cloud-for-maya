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
from .renderers import get_output_prefix_with_tokens, get_height, get_width
from .data_classes import (
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
    output_file_prefix_parameter_name: Optional[str]
    output_file_prefix: str
    image_width_parameter_name: Optional[str]
    image_height_parameter_name: Optional[str]
    image_resolution: tuple[int, int]


def _get_job_template(
    default_job_template: dict[str, Any],
    settings: RenderSubmitterUISettings,
    renderers: set[str],
    render_layers: list[RenderLayerData],
    all_layer_selectable_cameras,
    current_layer_selectable_cameras,
) -> dict[str, Any]:
    job_template = deepcopy(default_job_template)

    # Set the job's name
    job_template["name"] = settings.name

    # If there are multiple frame ranges, split up the Frames parameter by layer
    if render_layers[0].frames_parameter_name:
        # Extract the Frames parameter definition
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

    # If there are multiple output image formats, split that up by layer
    if render_layers[0].output_file_prefix_parameter_name:
        for layer_data in render_layers:
            job_template["parameters"].append(
                {
                    "name": layer_data.output_file_prefix_parameter_name,
                    "type": "STRING",
                    "userInterface": {
                        "control": "LINE_EDIT",
                        "label": "Output File Prefix",
                        "groupLabel": layer_data.ui_group_label,
                    },
                    "description": f"The output filename prefix for layer {layer_data.display_name}",
                }
            )
    else:
        job_template["parameters"].append(
            {
                "name": "OutputFilePrefix",
                "type": "STRING",
                "userInterface": {
                    "control": "LINE_EDIT",
                    "label": "Output File Prefix",
                    "groupLabel": "Maya Settings",
                },
                "description": "The output filename prefix.",
            }
        )

    # If there are multiple output image resolutions, split that up by layer
    if render_layers[0].image_width_parameter_name:
        for layer_data in render_layers:
            job_template["parameters"].append(
                {
                    "name": layer_data.image_width_parameter_name,
                    "type": "INT",
                    "userInterface": {
                        "control": "SPIN_BOX",
                        "label": "Image Width",
                        "groupLabel": layer_data.ui_group_label,
                    },
                    "minValue": 1,
                    "description": f"The image width for layer {layer_data.display_name}.",
                }
            )
            job_template["parameters"].append(
                {
                    "name": layer_data.image_height_parameter_name,
                    "type": "INT",
                    "userInterface": {
                        "control": "SPIN_BOX",
                        "label": "Image Height",
                        "groupLabel": layer_data.ui_group_label,
                    },
                    "minValue": 1,
                    "description": f"The image height for layer {layer_data.display_name}.",
                }
            )
    else:
        job_template["parameters"].append(
            {
                "name": "ImageWidth",
                "type": "INT",
                "userInterface": {
                    "control": "SPIN_BOX",
                    "label": "Image Width",
                    "groupLabel": "Maya Settings",
                },
                "minValue": 1,
                "description": "The image width of the output.",
            }
        )
        job_template["parameters"].append(
            {
                "name": "ImageHeight",
                "type": "INT",
                "userInterface": {
                    "control": "SPIN_BOX",
                    "label": "Image Height",
                    "groupLabel": "Maya Settings",
                },
                "minValue": 1,
                "description": "The image height of the output.",
            }
        )

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
            + "output_file_prefix: '{{Param."
            + (layer_data.output_file_prefix_parameter_name or "OutputFilePrefix")
            + "}}'\n"
            + "image_width: {{Param."
            + (layer_data.image_width_parameter_name or "ImageWidth")
            + "}}\n"
            + "image_height: {{Param."
            + (layer_data.image_height_parameter_name or "ImageHeight")
            + "}}\n"
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
    renderers: set[str],
    render_layers: list[RenderLayerData],
    default_rez_packages: str,
) -> dict[str, Any]:
    parameter_values = [
        {"name": "deadline:priority", "value": settings.priority},
        {"name": "deadline:targetTaskRunStatus", "value": settings.initial_status},
        {"name": "deadline:maxFailedTasksCount", "value": settings.max_failed_tasks_count},
        {"name": "deadline:maxRetriesPerTask", "value": settings.max_retries_per_task},
    ]

    # Set the Maya scene file value
    parameter_values.append({"name": "MayaSceneFile", "value": Scene.name()})

    if render_layers[0].frames_parameter_name:
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

    if render_layers[0].output_file_prefix_parameter_name:
        for layer_data in render_layers:
            parameter_values.append(
                {
                    "name": layer_data.output_file_prefix_parameter_name,
                    "value": layer_data.output_file_prefix,
                }
            )
    else:
        parameter_values.append(
            {"name": "OutputFilePrefix", "value": render_layers[0].output_file_prefix}
        )

    if render_layers[0].image_width_parameter_name:
        for layer_data in render_layers:
            parameter_values.append(
                {
                    "name": layer_data.image_width_parameter_name,
                    "value": layer_data.image_resolution[0],
                }
            )
            parameter_values.append(
                {
                    "name": layer_data.image_height_parameter_name,
                    "value": layer_data.image_resolution[1],
                }
            )
    else:
        parameter_values.append(
            {
                "name": "ImageWidth",
                "value": render_layers[0].image_resolution[0],
            }
        )
        parameter_values.append(
            {
                "name": "ImageHeight",
                "value": render_layers[0].image_resolution[1],
            }
        )

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

    # Set the RezPackages parameter value if their overridden or we need
    # to modify them due to the include_adaptor_wheels setting.
    if settings.override_rez_packages or settings.include_adaptor_wheels:
        if settings.override_rez_packages:
            rez_packages = settings.rez_packages
        else:
            rez_packages = default_rez_packages
        # If the adaptor wheels are included, remove the deadline_cloud_for_maya rez package
        if settings.include_adaptor_wheels:
            rez_packages = " ".join(
                pkg for pkg in rez_packages.split() if not pkg.startswith("deadline_cloud_for_maya")
            )
        parameter_values.append({"name": "RezPackages", "value": rez_packages})

    return {"parameterValues": parameter_values}


def show_maya_render_submitter(parent, f=Qt.WindowFlags()) -> "Optional[SubmitJobToDeadlineDialog]":
    with open(Path(__file__).parent / "default_maya_job_template.yaml") as fh:
        default_job_template = yaml.safe_load(fh)

    render_settings = RenderSubmitterUISettings()

    # Set the setting defaults that come from the scene
    render_settings.name = Path(Scene.name()).name
    render_settings.frame_list = str(Animation.frame_list())
    render_settings.project_path = Scene.project_path()
    render_settings.output_path = Scene.output_path()

    # Get the RezPackages parameter definition, and use the default set there
    rez_package_param = [
        param for param in default_job_template["parameters"] if param["name"] == "RezPackages"
    ]
    if rez_package_param:
        default_rez_packages = render_settings.rez_packages = rez_package_param[0].get(
            "default", ""
        )
    else:
        default_rez_packages = ""

    # Load the sticky settings
    render_settings.load_sticky_settings(Scene.name())

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
            output_file_prefix = get_output_prefix_with_tokens()
            image_resolution = (get_width(), get_height())

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
                    output_file_prefix_parameter_name=None,
                    output_file_prefix=output_file_prefix,
                    image_width_parameter_name=None,
                    image_height_parameter_name=None,
                    image_resolution=image_resolution,
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

        first_output_file_prefix = submit_render_layers[0].output_file_prefix
        per_layer_output_file_prefix = any(
            layer.output_file_prefix != first_output_file_prefix for layer in submit_render_layers
        )

        if per_layer_output_file_prefix:
            for layer_data in submit_render_layers:
                layer_data.output_file_prefix_parameter_name = (
                    f"{layer_data.display_name}OutputFilePrefix"
                )

        first_image_resolution = submit_render_layers[0].image_resolution
        per_layer_image_resolution = any(
            layer.image_resolution != first_image_resolution for layer in submit_render_layers
        )

        if per_layer_image_resolution:
            for layer_data in submit_render_layers:
                layer_data.image_width_parameter_name = f"{layer_data.display_name}ImageWidth"
                layer_data.image_height_parameter_name = f"{layer_data.display_name}ImageHeight"

        renderers: set[str] = {layer_data.renderer_name for layer_data in submit_render_layers}

        job_template = _get_job_template(
            default_job_template,
            settings,
            renderers,
            submit_render_layers,
            all_layer_selectable_cameras,
            current_layer_selectable_cameras,
        )
        parameter_values = _get_parameter_values(
            settings, renderers, submit_render_layers, default_rez_packages
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

        settings.save_sticky_settings(Scene.name())

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
