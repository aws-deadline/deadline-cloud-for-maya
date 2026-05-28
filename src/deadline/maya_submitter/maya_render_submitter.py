# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import os
from logging import getLogger
from pathlib import Path
from typing import Any, Optional, cast
import yaml  # type: ignore[import]
from copy import deepcopy
from dataclasses import dataclass

import maya.cmds  # pylint: disable=import-error

from deadline.client.api import (
    get_deadline_cloud_library_telemetry_client,
    get_queue_parameter_definitions,
)
from deadline.client.config import get_setting
from deadline.client.job_bundle.parameters import JobParameter
from deadline.client.job_bundle._yaml import deadline_yaml_dump
from deadline.client.ui.dialogs.submit_job_to_deadline_dialog import (  # pylint: disable=import-error
    SubmitJobToDeadlineDialog,
    JobBundlePurpose,
)
from deadline.client.exceptions import DeadlineOperationError
from qtpy.QtCore import Qt  # type: ignore

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
from ._version import version, version_tuple as adaptor_version_tuple
from .ui.components.scene_settings_tab import SceneSettingsWidget
from deadline.client.job_bundle.submission import AssetReferences
import time

logger = getLogger(__name__)


def _populate_selectable_cameras(
    render_settings: "RenderSubmitterUISettings",
    render_layers: list["RenderLayerData"],
) -> None:
    """Populate the selectable camera lists on render_settings for the UI dropdowns.

    - current_layer_selectable_cameras: all renderable cameras in the current layer
    - all_layer_selectable_cameras: only cameras common to ALL render layers (intersection)
    """
    current_layer_selectable_cameras: list[str] = get_renderable_camera_names()
    render_settings.current_layer_selectable_cameras = [ALL_CAMERAS] + sorted(
        current_layer_selectable_cameras
    )

    all_layer_selectable_cameras_set: set[str] = set(render_layers[0].renderable_camera_names)
    for layer in render_layers:
        all_layer_selectable_cameras_set = all_layer_selectable_cameras_set.intersection(
            layer.renderable_camera_names
        )
    render_settings.all_layer_selectable_cameras = [ALL_CAMERAS] + sorted(
        all_layer_selectable_cameras_set
    )


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
    all_layer_selectable_cameras: list[str],
    current_layer_selectable_cameras: list[str],
) -> dict[str, Any]:
    job_template = deepcopy(default_job_template)

    # Set the job's name and description
    job_template["name"] = settings.name
    if settings.description:
        job_template["description"] = settings.description

    # If there are multiple frame ranges, split up the Frames parameter by layer
    if render_layers[0].frames_parameter_name:
        # Extract the Frames parameter definition
        frame_param = [
            param for param in job_template["parameterDefinitions"] if param["name"] == "Frames"
        ][0]
        job_template["parameterDefinitions"] = [
            param for param in job_template["parameterDefinitions"] if param["name"] != "Frames"
        ]

        # Create layer-specific Frames parameters
        for layer_data in render_layers:
            layer_frame_param = deepcopy(frame_param)
            layer_frame_param["name"] = layer_data.frames_parameter_name
            layer_frame_param["userInterface"]["groupLabel"] = layer_data.ui_group_label
            job_template["parameterDefinitions"].append(layer_frame_param)

    # If there are multiple output image formats, split that up by layer
    if render_layers[0].output_file_prefix_parameter_name:
        for layer_data in render_layers:
            job_template["parameterDefinitions"].append(
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
        job_template["parameterDefinitions"].append(
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
            job_template["parameterDefinitions"].append(
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
            job_template["parameterDefinitions"].append(
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
        job_template["parameterDefinitions"].append(
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
        job_template["parameterDefinitions"].append(
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
        selectable_cameras: list[str]
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
        job_template["parameterDefinitions"].append(camera_param)

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
            parameter_space["taskParameterDefinitions"][0]["range"] = (
                "{{Param." + layer_data.frames_parameter_name + "}}"
            )
        # If we're submitting all cameras, create another parameter space dimension
        if settings.camera_selection == ALL_CAMERAS:
            parameter_space["taskParameterDefinitions"].append(
                {
                    "name": "Camera",
                    "type": "STRING",
                    "range": layer_data.renderable_camera_names,
                }
            )
            run_data = step["script"]["embeddedFiles"][0]
            run_data["data"] += "camera: '{{Task.Param.Camera}}'\n"

        # Update the init data of the step
        init_data = step["stepEnvironments"][0]["script"]["embeddedFiles"][0]
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
            + "cache_pathmapping: true\n"
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
        job_template["parameterDefinitions"].append(
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
        if wheels_path_package_names != {
            "openjd_adaptor_runtime",
            "deadline",
            "deadline_cloud_for_maya",
        }:
            raise RuntimeError(
                "The Developer Option 'Include Adaptor Wheels' is enabled, but the wheels directory contains the wrong wheels:\n"
                + "Expected: openjd_adaptor_runtime, deadline, and deadline_cloud_for_maya\n"
                + f"Actual: {wheels_path_package_names}"
            )

        override_adaptor_name_param = [
            param
            for param in override_environment["parameterDefinitions"]
            if param["name"] == "OverrideAdaptorName"
        ][0]
        override_adaptor_name_param["default"] = "MayaAdaptor"

        # There are no parameter conflicts between these two templates, so this works
        job_template["parameterDefinitions"].extend(override_environment["parameterDefinitions"])

        # Add the environment to the end of the template's job environments
        if "jobEnvironments" not in job_template:
            job_template["jobEnvironments"] = []
        job_template["jobEnvironments"].append(override_environment["environment"])

    return job_template


def _get_parameter_values(
    settings: RenderSubmitterUISettings,
    renderers: set[str],
    render_layers: list[RenderLayerData],
    queue_parameters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    parameter_values: list[dict[str, Any]] = []

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
                "value": get_width(),
            }
        )
        parameter_values.append(
            {
                "name": "ImageHeight",
                "value": get_height(),
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

    # Add OCIO config file parameter if present
    ocio_config = Scene.ocio_config_file()
    if ocio_config:
        parameter_values.append({"name": "OCIOConfigFile", "value": ocio_config})

    # Set the Arnold-specific parameter values
    if "arnold" in renderers:
        parameter_values.append(
            {
                "name": "ArnoldErrorOnLicenseFailure",
                "value": "true" if Scene.error_on_arnold_license_fail() else "false",
            }
        )

    # Check for any overlap between the job parameters we've defined and the
    # queue parameters. This is an error, as we weren't synchronizing the values
    # between the two different tabs where they came from.
    parameter_names = {param["name"] for param in parameter_values}
    queue_parameter_names = {param["name"] for param in queue_parameters}
    parameter_overlap = parameter_names.intersection(queue_parameter_names)
    if parameter_overlap:
        raise DeadlineOperationError(
            "The following queue parameters conflict with the Maya job parameters:\n"
            + f"{', '.join(parameter_overlap)}"
        )

    # If we're overriding the adaptor with wheels, remove the adaptor from the Packages parameters
    if settings.include_adaptor_wheels:
        wheels_path = str(Path(__file__).parent.parent.parent.parent / "wheels")
        parameter_values.append({"name": "OverrideAdaptorWheels", "value": wheels_path})

        rez_param = {}
        conda_param = {}
        # Find the Packages parameter definition
        for param in queue_parameters:
            if param["name"] == "RezPackages":
                rez_param = param
            if param["name"] == "CondaPackages":
                conda_param = param
        # Remove the deadline_cloud_for_maya/maya-openjd package
        if rez_param:
            current_value = rez_param.get("value", rez_param.get("default", ""))
            rez_param["value"] = " ".join(
                pkg
                for pkg in current_value.split()
                if not pkg.startswith("deadline_cloud_for_maya")
            )
        if conda_param:
            current_value = conda_param.get("value", conda_param.get("default", ""))
            conda_param["value"] = " ".join(
                pkg for pkg in current_value.split() if not pkg.startswith("maya-openjd")
            )

    parameter_values.extend(
        {"name": param["name"], "value": param.get("value", param.get("default", ""))}
        for param in queue_parameters
        if "value" in param or "default" in param
    )

    return parameter_values


def _set_render_setting(load_sticky_setting: bool = False) -> RenderSubmitterUISettings:
    render_settings = RenderSubmitterUISettings()

    # Set the setting defaults that come from the scene
    render_settings.name = Path(Scene.name()).name
    render_settings.frame_list = str(Animation.frame_list())
    render_settings.project_path = Scene.project_path()
    render_settings.output_path = Scene.output_path()

    # Load the sticky settings
    if load_sticky_setting:
        render_settings.load_sticky_settings(Scene.name())

    return render_settings


def _set_render_layer_data() -> list[RenderLayerData]:
    # Create a dictionary for the layers, and accumulate data about each layer
    print(f"_set_render_layer_data - get_all_renderable_render_layer_names {time.time()}")
    render_layer_names = get_all_renderable_render_layer_names()
    if not render_layer_names:
        raise DeadlineOperationError(
            "No render layer is set as renderable. At least one must be renderable to submit a job."
        )
    print(f"_set_render_layer_data processing layers {time.time()}")
    render_layers: list[RenderLayerData] = []
    with saved_current_render_layer():
        for render_layer_name in render_layer_names:
            set_current_render_layer(render_layer_name)

            display_name = get_render_layer_display_name(render_layer_name)
            print(f"_set_render_layer_data processing layer {display_name} {time.time()}")
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
            print(f"_set_render_layer_data done processing layer {time.time()}")

    # Sort the layers by name
    render_layers.sort(key=lambda layer: layer.display_name)

    return render_layers


@dataclass
class SubmissionContext:
    """Pre-computed scene data for submission.

    Caches expensive Maya scene queries (render layer switching, camera
    enumeration, etc.) so that multiple submission functions can share
    the same data without redundant computation.

    Use create_submission_context() to build an instance.
    """

    render_layers: list[RenderLayerData]
    current_layer_selectable_cameras: list[str]
    all_layer_selectable_cameras: list[str]


def create_submission_context() -> SubmissionContext:
    """Gather scene data and build a SubmissionContext.

    This performs the expensive Maya queries (render layer switching,
    camera enumeration, etc.) exactly once.

    Returns:
        SubmissionContext with all scene data populated.
    """
    render_layers = _set_render_layer_data()
    current_layer_selectable_cameras = [ALL_CAMERAS] + sorted(get_renderable_camera_names())

    all_layer_selectable_cameras_set: set[str] = set(render_layers[0].renderable_camera_names)
    for layer in render_layers:
        all_layer_selectable_cameras_set = all_layer_selectable_cameras_set.intersection(
            layer.renderable_camera_names
        )
    all_layer_selectable_cameras = [ALL_CAMERAS] + sorted(all_layer_selectable_cameras_set)

    return SubmissionContext(
        render_layers=render_layers,
        current_layer_selectable_cameras=current_layer_selectable_cameras,
        all_layer_selectable_cameras=all_layer_selectable_cameras,
    )


@dataclass
class PreparedRenderLayers:
    """Result of filtering and annotating render layers for submission."""

    layers: list[RenderLayerData]
    renderers: set[str]


def _prepare_render_layers_for_submission(
    settings: RenderSubmitterUISettings,
    context: SubmissionContext,
) -> PreparedRenderLayers:
    """Filter and annotate render layers based on settings.

    This is a pure transformation — no Maya scene queries. It works on
    deep copies of the context's render layers to avoid mutation issues
    when the context is reused across multiple calls.

    Args:
        settings: The render submitter UI settings.
        context: Pre-computed submission context.

    Returns:
        PreparedRenderLayers with the filtered layers and renderer set.
    """
    render_layers = deepcopy(context.render_layers)

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

    return PreparedRenderLayers(layers=submit_render_layers, renderers=renderers)


def get_default_job_template() -> dict[str, Any]:
    """Returns the default job template for Maya render submissions."""
    with open(Path(__file__).parent / "default_maya_job_template.yaml") as fh:
        return yaml.safe_load(fh)


def _get_python_script_job_template(settings: RenderSubmitterUISettings) -> dict[str, Any]:
    """Build a job template for a Python-script job.

    The template has a single step (`RunPythonScript`) whose task parameter
    space iterates over Frames. The adaptor's `daemon run` is invoked once per
    task with run-data containing `script_file`, optional `frame`, and
    optional `script_args`.

    The user's scene file and Python script file are declared as PATH/IN
    parameters so the Deadline Cloud job attachments system uploads them to
    the worker and applies path mapping at runtime.
    """
    return {
        "specificationVersion": "jobtemplate-2023-09",
        "name": settings.name or "Maya Python Script Job",
        "parameterDefinitions": [
            {
                "name": "MayaSceneFile",
                "type": "PATH",
                "objectType": "FILE",
                "dataFlow": "IN",
                "userInterface": {
                    "control": "CHOOSE_INPUT_FILE",
                    "label": "Maya Scene File",
                    "groupLabel": "Maya Settings",
                    "fileFilters": [
                        {
                            "label": "Maya Scene Files",
                            "patterns": ["*.mb", "*.ma"],
                        },
                        {"label": "All Files", "patterns": ["*"]},
                    ],
                },
                "description": "The Maya scene file to load before running the Python script.",
            },
            {
                "name": "PythonScriptFile",
                "type": "PATH",
                "objectType": "FILE",
                "dataFlow": "IN",
                "userInterface": {
                    "control": "CHOOSE_INPUT_FILE",
                    "label": "Python Script",
                    "groupLabel": "Maya Settings",
                    "fileFilters": [
                        {"label": "Python Scripts", "patterns": ["*.py"]},
                        {"label": "All Files", "patterns": ["*"]},
                    ],
                },
                "description": "The user-provided Python script that runs inside Maya per task.",
            },
            {
                "name": "Frames",
                "type": "STRING",
                "userInterface": {
                    "control": "LINE_EDIT",
                    "label": "Frames",
                    "groupLabel": "Maya Settings",
                },
                "description": (
                    "Task range. Each task runs the Python script once with "
                    "DEADLINE_TASK_FRAME set to the value. Use '1' for a single task."
                ),
                "minLength": 1,
                "default": "1",
            },
            {
                "name": "ProjectPath",
                "type": "PATH",
                "objectType": "DIRECTORY",
                "dataFlow": "NONE",
                "userInterface": {
                    "control": "CHOOSE_DIRECTORY",
                    "label": "Project Path",
                    "groupLabel": "Maya Settings",
                },
                "description": "The Maya project path.",
            },
            {
                "name": "OutputFilePath",
                "type": "PATH",
                "objectType": "DIRECTORY",
                "dataFlow": "OUT",
                "userInterface": {
                    "control": "CHOOSE_DIRECTORY",
                    "label": "Output File Path",
                    "groupLabel": "Maya Settings",
                },
                "description": "The output path.",
            },
            {
                "name": "ScriptArgs",
                "type": "STRING",
                "userInterface": {
                    "control": "LINE_EDIT",
                    "label": "Script Args",
                    "groupLabel": "Maya Settings",
                },
                "description": (
                    "Optional arguments passed to the Python script via the "
                    "DEADLINE_SCRIPT_ARGS environment variable."
                ),
                "default": "",
            },
            {
                "name": "StrictErrorChecking",
                "type": "STRING",
                "userInterface": {
                    "control": "CHECK_BOX",
                    "label": "Strict Error Checking",
                    "groupLabel": "Maya Settings",
                },
                "description": "Fail when errors occur.",
                "default": "false",
                "allowedValues": ["true", "false"],
            },
            {
                "name": "OCIOConfigFile",
                "type": "PATH",
                "objectType": "FILE",
                "dataFlow": "IN",
                "userInterface": {"control": "HIDDEN"},
                "description": "The OCIO configuration file path (auto-detected from scene).",
                "default": "",
            },
        ],
        "steps": [
            {
                "name": "RunPythonScript",
                "parameterSpace": {
                    "taskParameterDefinitions": [
                        {
                            "name": "Frame",
                            "type": "INT",
                            "range": "{{Param.Frames}}",
                        }
                    ]
                },
                "stepEnvironments": [
                    {
                        "name": "Maya",
                        "description": "Runs Maya in the background.",
                        "script": {
                            "embeddedFiles": [
                                {
                                    "name": "initData",
                                    "filename": "init-data.yaml",
                                    "type": "TEXT",
                                    "data": (
                                        "job_type: python_script\n"
                                        "scene_file: '{{Param.MayaSceneFile}}'\n"
                                        "project_path: '{{Param.ProjectPath}}'\n"
                                        "output_file_path: '{{Param.OutputFilePath}}'\n"
                                        "strict_error_checking: "
                                        "{{Param.StrictErrorChecking}}\n"
                                        "ocio_config_file: '{{Param.OCIOConfigFile}}'\n"
                                    ),
                                }
                            ],
                            "actions": {
                                "onEnter": {
                                    "command": "MayaAdaptor",
                                    "args": [
                                        "daemon",
                                        "start",
                                        "--path-mapping-rules",
                                        "file://{{Session.PathMappingRulesFile}}",
                                        "--connection-file",
                                        "{{Session.WorkingDirectory}}/connection.json",
                                        "--init-data",
                                        "file://{{Env.File.initData}}",
                                    ],
                                    "cancelation": {"mode": "NOTIFY_THEN_TERMINATE"},
                                    "timeout": 87000,
                                },
                                "onExit": {
                                    "command": "MayaAdaptor",
                                    "args": [
                                        "daemon",
                                        "stop",
                                        "--connection-file",
                                        "{{ Session.WorkingDirectory }}/connection.json",
                                    ],
                                    "cancelation": {"mode": "NOTIFY_THEN_TERMINATE"},
                                    "timeout": 600,
                                },
                            },
                        },
                    }
                ],
                "script": {
                    "embeddedFiles": [
                        {
                            "name": "runData",
                            "filename": "run-data.yaml",
                            "type": "TEXT",
                            "data": (
                                "frame: {{Task.Param.Frame}}\n"
                                "script_file: '{{Param.PythonScriptFile}}'\n"
                                "script_args: '{{Param.ScriptArgs}}'\n"
                            ),
                        }
                    ],
                    "actions": {
                        "onRun": {
                            "command": "MayaAdaptor",
                            "args": [
                                "daemon",
                                "run",
                                "--connection-file",
                                "{{ Session.WorkingDirectory }}/connection.json",
                                "--run-data",
                                "file://{{ Task.File.runData }}",
                            ],
                            "cancelation": {"mode": "NOTIFY_THEN_TERMINATE"},
                        }
                    },
                },
            }
        ],
    }


def _get_python_script_parameter_values(
    settings: RenderSubmitterUISettings,
    queue_parameters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build parameter_values for a Python-script job.

    Mirrors the relevant subset of `_get_parameter_values` but for the
    python-script template. Frames defaults to '1' when the user leaves
    it blank, producing a single task.
    """
    parameter_values: list[dict[str, Any]] = [
        {"name": "MayaSceneFile", "value": Scene.name()},
        {"name": "PythonScriptFile", "value": settings.python_script_path},
        {
            "name": "Frames",
            "value": (
                settings.frame_list
                if (settings.override_frame_range and settings.frame_list)
                else (settings.frame_list or "1")
            ),
        },
        {"name": "ProjectPath", "value": settings.project_path},
        {"name": "OutputFilePath", "value": settings.output_path},
        {"name": "ScriptArgs", "value": settings.script_args},
        {"name": "StrictErrorChecking", "value": "false"},
    ]

    ocio_config = Scene.ocio_config_file()
    if ocio_config:
        parameter_values.append({"name": "OCIOConfigFile", "value": ocio_config})

    # Validate against queue parameters as the render path does.
    parameter_names = {p["name"] for p in parameter_values}
    queue_parameter_names = {p["name"] for p in queue_parameters}
    overlap = parameter_names.intersection(queue_parameter_names)
    if overlap:
        raise DeadlineOperationError(
            "The following queue parameters conflict with the Maya job parameters:\n"
            + f"{', '.join(overlap)}"
        )

    # Developer option: override adaptor wheels (same as render path)
    if settings.include_adaptor_wheels:
        wheels_path = str(Path(__file__).parent.parent.parent.parent / "wheels")
        parameter_values.append({"name": "OverrideAdaptorWheels", "value": wheels_path})

        for param in queue_parameters:
            if param["name"] == "RezPackages":
                current_value = param.get("value", param.get("default", ""))
                param["value"] = " ".join(
                    pkg
                    for pkg in current_value.split()
                    if not pkg.startswith("deadline_cloud_for_maya")
                )
            if param["name"] == "CondaPackages":
                current_value = param.get("value", param.get("default", ""))
                param["value"] = " ".join(
                    pkg for pkg in current_value.split() if not pkg.startswith("maya-openjd")
                )

    parameter_values.extend(
        {"name": param["name"], "value": param.get("value", param.get("default", ""))}
        for param in queue_parameters
        if "value" in param or "default" in param
    )

    return parameter_values


def get_job_template_for_submission(
    settings: RenderSubmitterUISettings,
    host_requirements: Optional[dict[str, Any]] = None,
    *,
    context: Optional[SubmissionContext] = None,
) -> dict[str, Any]:
    """Generate the job template for Maya render submissions.

    Args:
        settings: The render submitter UI settings.
        host_requirements: Optional host requirements to inject into job steps.
        context: Optional pre-computed submission context. If not provided,
            one will be created (which queries the Maya scene).

    Returns:
        The job template dictionary ready for serialization.
    """
    if context is None:
        context = create_submission_context()

    # Python-script job: build a different template entirely; render-layer
    # specific logic does not apply.
    if getattr(settings, "job_type", "render") == "python_script":
        job_template = _get_python_script_job_template(settings)
        if host_requirements:
            for step in job_template["steps"]:
                step["hostRequirements"] = host_requirements
        return job_template

    default_job_template = get_default_job_template()
    prepared = _prepare_render_layers_for_submission(settings, context)

    job_template = _get_job_template(
        default_job_template=default_job_template,
        settings=settings,
        renderers=prepared.renderers,
        render_layers=prepared.layers,
        all_layer_selectable_cameras=context.all_layer_selectable_cameras,
        current_layer_selectable_cameras=context.current_layer_selectable_cameras,
    )

    if host_requirements:
        for step in job_template["steps"]:
            step["hostRequirements"] = host_requirements

    return job_template


def get_parameter_values_for_submission(
    settings: RenderSubmitterUISettings,
    queue_parameters: Optional[list[dict[str, Any]]] = None,
    *,
    context: Optional[SubmissionContext] = None,
) -> list[dict[str, Any]]:
    """Generate the parameter values for Maya render submissions.

    Args:
        settings: The render submitter UI settings.
        queue_parameters: Optional queue parameters. When omitted, no
            queue-specific parameters (like RezPackages or CondaPackages)
            will be included.
        context: Optional pre-computed submission context. If not provided,
            one will be created (which queries the Maya scene).

    Returns:
        The parameter values list ready for serialization.
    """
    if context is None:
        context = create_submission_context()
    if queue_parameters is None:
        queue_parameters = []

    if getattr(settings, "job_type", "render") == "python_script":
        return _get_python_script_parameter_values(settings, queue_parameters)

    prepared = _prepare_render_layers_for_submission(settings, context)

    return _get_parameter_values(settings, prepared.renderers, prepared.layers, queue_parameters)


def get_asset_references_for_submission(
    asset_references: AssetReferences,
) -> dict[str, Any]:
    """Get the asset references in dictionary form for Maya render submissions.

    Args:
        asset_references: The asset references object.

    Returns:
        The asset references dictionary ready for serialization.
    """
    return asset_references.to_dict()


def get_queue_parameters(
    farm_id_override: Optional[str] = None,
    queue_id_override: Optional[str] = None,
    initial_values_override: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Get queue parameters from Deadline Cloud for external API usage.

    Retrieves queue parameter definitions from the Deadline Cloud API
    and optionally applies initial values. Use this to construct
    queue_parameters for get_parameter_values_for_submission() without
    going through the UI.

    Args:
        farm_id_override: The farm ID. If not provided, uses the default from settings.
        queue_id_override: The queue ID. If not provided, uses the default from settings.
        initial_values_override: Optional dict of {parameter_name: value} to override
            default parameter values.

    Returns:
        A list of parameter definition dicts suitable for passing to
        get_parameter_values_for_submission().

    Raises:
        DeadlineOperationError: If farm_id or queue_id are not configured.
    """
    farm_id = farm_id_override if farm_id_override is not None else get_setting("defaults.farm_id")
    queue_id = (
        queue_id_override if queue_id_override is not None else get_setting("defaults.queue_id")
    )

    if not farm_id or not queue_id:
        raise DeadlineOperationError(
            "Farm ID and Queue ID must be configured. "
            "Either provide them as arguments or configure them in Deadline Cloud settings."
        )

    queue_parameters = get_queue_parameter_definitions(farmId=farm_id, queueId=queue_id)

    if initial_values_override:
        for parameter in queue_parameters:
            if parameter["name"] in initial_values_override:
                parameter["value"] = initial_values_override[parameter["name"]]

    return cast(list[dict[str, Any]], queue_parameters)


def get_job_bundle_for_submission(
    settings: RenderSubmitterUISettings,
    queue_parameters: Optional[list[dict[str, Any]]] = None,
    host_requirements: Optional[dict[str, Any]] = None,
    asset_references: Optional[AssetReferences] = None,
) -> dict[str, Any]:
    """Generate a complete job bundle in one call.

    This is the recommended entry point for external integrations.
    It performs expensive scene queries exactly once.

    Args:
        settings: Render submitter UI settings.
        queue_parameters: Queue parameters (use get_queue_parameters() to obtain).
        host_requirements: Optional host requirements.
        asset_references: Optional asset references.

    Returns:
        Dict with keys "job_template", "parameter_values", and optionally
        "asset_references".
    """
    context = create_submission_context()

    result: dict[str, Any] = {
        "job_template": get_job_template_for_submission(
            settings, host_requirements, context=context
        ),
        "parameter_values": get_parameter_values_for_submission(
            settings, queue_parameters, context=context
        ),
    }

    if asset_references is not None:
        result["asset_references"] = get_asset_references_for_submission(asset_references)

    return result


def on_create_job_bundle_callback(
    widget: SubmitJobToDeadlineDialog,
    job_bundle_dir: str,
    settings: RenderSubmitterUISettings,
    queue_parameters: list[JobParameter],
    asset_references: AssetReferences,
    host_requirements: Optional[dict[str, Any]] = None,
    purpose: JobBundlePurpose = JobBundlePurpose.SUBMISSION,
) -> dict[str, Any]:
    render_settings = _set_render_setting()

    # Single expensive call — queries Maya scene once
    context = create_submission_context()

    # Tell the settings tab the selectable cameras
    render_settings.current_layer_selectable_cameras = [ALL_CAMERAS] + sorted(
        context.current_layer_selectable_cameras
    )
    render_settings.all_layer_selectable_cameras = [
        ALL_CAMERAS
    ] + context.all_layer_selectable_cameras

    # if submitting, warn if the current scene has been modified
    scene_modified = maya.cmds.file(q=True, mf=True) == 1
    if scene_modified and purpose == JobBundlePurpose.SUBMISSION:
        scene_name = maya.cmds.file(q=True, sn=True)
        button = maya.cmds.confirmDialog(
            title="Warning: Scene Changes not Saved",
            message=(
                "The scene has unsaved local changes that will not be included in the job submission.\n\nDo you want to save the scene to %s before submitting?"
                % scene_name
            ),
            button=["Yes", "No"],
            defaultButton="No",
            cancelButton="No",
            dismissString="No",
        )
        if button == "Yes":
            maya.cmds.file(save=True)

    job_bundle_path = Path(job_bundle_dir)

    # For Python-script jobs, ensure the user-supplied script file is uploaded
    # as a job attachment. The job template declares `PythonScriptFile` as a
    # PATH/IN parameter so Deadline Cloud applies path mapping at runtime.
    if getattr(settings, "job_type", "render") == "python_script":
        script_path = (settings.python_script_path or "").strip()
        if not script_path:
            raise DeadlineOperationError(
                "Python Script job type selected, but no Python script file was specified."
            )
        if not os.path.isfile(script_path):
            raise DeadlineOperationError(f"Python script file does not exist: {script_path}")
        asset_references.input_filenames.add(os.path.normpath(script_path))

    # Reuse the same context — no redundant computation
    job_template = get_job_template_for_submission(settings, host_requirements, context=context)
    parameter_values = get_parameter_values_for_submission(
        settings, cast(list[dict[str, Any]], queue_parameters), context=context
    )

    with open(job_bundle_path / "template.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump(job_template, f, indent=1)

    with open(job_bundle_path / "parameter_values.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump({"parameterValues": parameter_values}, f, indent=1)

    with open(job_bundle_path / "asset_references.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump(asset_references.to_dict(), f, indent=1)

    # Save Sticky Settings
    attachments: AssetReferences = widget.job_attachments.attachments
    settings.input_filenames = sorted(attachments.input_filenames)
    settings.input_directories = sorted(attachments.input_directories)
    settings.input_filenames = sorted(attachments.input_filenames)

    settings.save_sticky_settings(Scene.name())

    return {
        "job_parameters": parameter_values,
    }


def show_maya_render_submitter(
    parent, f=Qt.WindowFlags(), load_sticky_setting: bool = False
) -> Optional[SubmitJobToDeadlineDialog]:
    print("Starting Maya render submitter")

    # Create and show a progress dialog
    from qtpy.QtWidgets import QProgressDialog
    from qtpy.QtCore import Qt  # type: ignore

    progress_dialog = QProgressDialog("Initializing...", "", 0, 1, parent)
    progress_dialog.setWindowTitle("Asset Detection")
    progress_dialog.setWindowModality(Qt.WindowModal)
    progress_dialog.setCancelButton(None)  # Remove cancel button
    progress_dialog.setMinimumDuration(0)  # Show immediately
    progress_dialog.setValue(0)

    # Create a callback function to update the progress dialog
    def update_progress(message):
        progress_dialog.setLabelText(message)
        maya.cmds.refresh(force=True)
        time.sleep(0.05)  # Add a small sleep to ensure the UI has time to update

    # Initialize with first message
    update_progress("Loading render settings...")
    render_settings = _set_render_setting(load_sticky_setting)

    update_progress("Processing render layers...")
    render_layers: list[RenderLayerData] = _set_render_layer_data()
    print(f"Render layers processed at {time.time()}")
    all_renderers: set[str] = {layer_data.renderer_name for layer_data in render_layers}

    # Populate the selectable cameras for the UI dropdowns
    _populate_selectable_cameras(render_settings, render_layers)

    auto_detected_attachments = AssetReferences()
    introspector = AssetIntrospector()
    print(f"Asset introspector initialized at {time.time()}")
    update_progress("Analyzing scene assets...")
    scene_assets = list(introspector.parse_scene_assets(progress_callback=update_progress))
    total_assets = len(scene_assets)

    # Update progress dialog with total assets
    progress_dialog.setMaximum(total_assets)
    progress_dialog.setValue(0)

    # Process assets with progress updates
    processed_files = set()
    processed_directories = set()
    print(f"Starting to process {total_assets} scene assets...")

    for i, asset_path in enumerate(scene_assets):
        progress_dialog.setValue(i)
        normalized = os.path.normpath(asset_path)
        if not os.path.exists(normalized):
            continue
        if os.path.isdir(normalized):
            processed_directories.add(normalized)
        else:
            processed_files.add(normalized)
        # Process in larger batches to improve performance - refresh UI every 100 assets
        if i % 100 == 0 and i > 0:
            print(f"Processed {i+1}/{total_assets} assets at {time.time()}")
            update_progress(f"Processed {i+1}/{total_assets} assets")

    progress_dialog.setValue(total_assets)
    auto_detected_attachments.input_filenames = processed_files
    auto_detected_attachments.input_directories = processed_directories
    print(f"All {total_assets} assets processed at {time.time()}")
    update_progress(f"All {total_assets} assets processed")

    update_progress("Adding output directories...")
    for layer_data in render_layers:
        auto_detected_attachments.output_directories.update(layer_data.output_directories)
    print(f"Output directories added at {time.time()}")

    attachments = AssetReferences(
        input_filenames=set(render_settings.input_filenames),
        input_directories=set(render_settings.input_directories),
        output_directories=set(render_settings.output_directories),
    )

    update_progress("Preparing submission parameters...")
    maya_version = maya.cmds.about(version=True)
    adaptor_version = ".".join(str(v) for v in adaptor_version_tuple[:2])
    # Need Maya and the Maya OpenJD application interface adaptor
    rez_packages = f"mayaIO-{maya_version} deadline_cloud_for_maya"
    conda_packages = f"maya={maya_version}.* maya-openjd={adaptor_version}.*"
    # Initialize telemetry client, opt-out is respected
    get_deadline_cloud_library_telemetry_client().update_common_details(
        {
            "deadline-cloud-for-maya-submitter-version": version,
            "maya-version": maya_version,
        }
    )
    # Add any additional renderers that are used
    if "arnold" in all_renderers:
        rez_packages += " mtoa"
        conda_packages += " maya-mtoa"
    if "vray" in all_renderers:
        conda_packages += " maya-vray"
    if "redshift" in all_renderers:
        conda_packages += " maya-redshift"

    # Close the progress dialog before creating the submission dialog
    progress_dialog.close()
    print("Progress dialog closed, creating submission dialog")

    submitter_dialog = SubmitJobToDeadlineDialog(
        job_setup_widget_type=SceneSettingsWidget,
        initial_job_settings=render_settings,
        initial_shared_parameter_values={
            "RezPackages": rez_packages,
            "CondaPackages": conda_packages,
        },
        auto_detected_attachments=auto_detected_attachments,
        attachments=attachments,
        on_create_job_bundle_callback=on_create_job_bundle_callback,
        parent=parent,
        f=f,
        show_host_requirements_tab=True,
    )
    submitter_dialog.show()
    return submitter_dialog
