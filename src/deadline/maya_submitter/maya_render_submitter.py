# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import os
from logging import getLogger
from pathlib import Path
from typing import Any, Optional, cast
import time

import maya.cmds  # pylint: disable=import-error

from deadline.client.api import (
    get_deadline_cloud_library_telemetry_client,
)
from deadline.client.config import get_setting, str2bool
from deadline.client.job_bundle.parameters import JobParameter
from deadline.client.job_bundle._yaml import deadline_yaml_dump
from deadline.client.ui.dialogs.submit_job_to_deadline_dialog import (  # pylint: disable=import-error
    SubmitJobToDeadlineDialog,
    JobBundlePurpose,
)
from deadline.client.exceptions import DeadlineOperationCanceled
from qtpy.QtCore import Qt  # type: ignore

from .assets import AssetIntrospector
from .data_classes import (
    RenderSubmitterUISettings,
)
from .cameras import get_renderable_camera_names, ALL_CAMERAS
from ._version import version, version_tuple as adaptor_version_tuple
from .submitter import (
    MayaSubmitter,
    MayaSubmitterSettings,
    RenderLayerData,
    _get_render_layer_data,
)
from .ui.components.scene_settings_tab import SceneSettingsWidget
from deadline.client.job_bundle.submission import AssetReferences

# Re-exported so external callers (and the GUI) that historically imported the
# scene helpers from this module keep working after the engine moved to
# submitter.py.
from .scene import Animation, Scene  # type: ignore # noqa: F401

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


def _ui_settings_to_submitter_settings(
    ui_settings: RenderSubmitterUISettings,
) -> MayaSubmitterSettings:
    """Adapt the GUI's RenderSubmitterUISettings to the headless MayaSubmitterSettings.

    The mirror of the old ``_to_native_settings`` (now inverted): the builders
    consume MayaSubmitterSettings directly, so the GUI settings are converted at
    the submission boundary. Only ``name`` -> ``job_name`` needs renaming; every
    other field maps by name, and ``render_layer_selection`` is already a
    LayerSelection on both sides.
    """
    return MayaSubmitterSettings(
        job_name=ui_settings.name,
        description=ui_settings.description,
        frame_list=ui_settings.frame_list,
        project_path=ui_settings.project_path,
        output_path=ui_settings.output_path,
        priority=ui_settings.priority,
        initial_status=ui_settings.initial_status,
        max_failed_tasks_count=ui_settings.max_failed_tasks_count,
        max_retries_per_task=ui_settings.max_retries_per_task,
        max_worker_count=ui_settings.max_worker_count,
        override_frame_range=ui_settings.override_frame_range,
        input_filenames=list(ui_settings.input_filenames),
        input_directories=list(ui_settings.input_directories),
        output_directories=list(ui_settings.output_directories),
        render_layer_selection=ui_settings.render_layer_selection,
        camera_selection=ui_settings.camera_selection,
        include_adaptor_wheels=ui_settings.include_adaptor_wheels,
        timeouts=ui_settings.timeouts,
    )


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


def on_create_job_bundle_callback(
    widget: SubmitJobToDeadlineDialog,
    job_bundle_dir: str,
    settings: RenderSubmitterUISettings,
    queue_parameters: list[JobParameter],
    asset_references: AssetReferences,
    host_requirements: Optional[dict[str, Any]] = None,
    purpose: JobBundlePurpose = JobBundlePurpose.SUBMISSION,
) -> dict[str, Any]:
    # Build the submitter once so get_job_template() and get_parameter_values()
    # below share a single cached scene context (one expensive scene scan per
    # submission instead of two). The submitter dialog was already populated with
    # selectable cameras when it was created in show_maya_render_submitter(); this
    # callback only needs to emit the job bundle.
    submitter = MayaSubmitter()

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

    # Reuse the same submitter (and its cached context) — no redundant scene scan
    maya_settings = _ui_settings_to_submitter_settings(settings)
    job_template = submitter.get_job_template(maya_settings, host_requirements)
    parameter_values = submitter.get_parameter_values(
        maya_settings, cast(list[dict[str, Any]], queue_parameters)
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


def _pre_gui_hook_confirm_callback(parent):
    """Choose the confirmation callback for pre-GUI hooks based on the auto_accept setting.

    Returns ``None`` (run hooks without prompting) when ``settings.auto_accept`` is enabled,
    otherwise the standard Qt confirmation dialog from ``qt_hook_confirmation``. Kept as a small
    helper so the auto_accept branch can be unit-tested headlessly.
    """
    if str2bool(get_setting("settings.auto_accept")):
        return None

    from deadline.client.ui.pre_gui_hooks import qt_hook_confirmation

    return qt_hook_confirmation(parent)


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
    render_layers: list[RenderLayerData] = _get_render_layer_data()
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

    shared_parameter_values = {
        "RezPackages": rez_packages,
        "CondaPackages": conda_packages,
    }

    # Run pre-GUI hooks so studios can pre-populate dialog fields before it opens. Maya has no
    # on-disk job bundle at this point, so hooks are sourced from DEADLINE_HOOKS_DIR only
    # (bundle_dir=None), gated by settings.allow_environment_hooks. The confirmation prompt is
    # skipped when auto_accept is set; otherwise the standard dialog is shown.
    #
    # Imported lazily (like qtpy above) rather than at module top: this ships in deadline-cloud
    # 0.60.1+, and a top-level import would break importing this module — and every unit test that
    # collects it — against older deadline-cloud releases.
    from deadline.client.ui.pre_gui_hooks import (
        PreGuiHookContext,
        apply_pre_gui_output,
        run_pre_gui_hooks,
    )

    try:
        pre_gui_output = run_pre_gui_hooks(
            PreGuiHookContext(
                bundle_dir=None,
                job_name=render_settings.name,
                submitter_name="maya",
                parameters=dict(shared_parameter_values),
            ),
            confirm_callback=_pre_gui_hook_confirm_callback(parent),
        )
    except DeadlineOperationCanceled:
        # The user declined the hook confirmation prompt. This is a normal cancellation, not a
        # failure, so abort opening the submitter silently rather than letting the exception reach
        # the caller's gui_error_handler (which would show a spurious "Error opening..." dialog).
        # Mirrors the check_and_show_update_dialog() early-return; both callers handle None.
        return None
    # RenderSubmitterUISettings has no `.parameters` list, so apply_pre_gui_output routes
    # name/description onto it and every hook parameter into shared_parameter_values. Guard with
    # `or {}` defensively: run_pre_gui_hooks returns {} when no hooks run, but this keeps the call
    # safe if a future release returns None instead.
    apply_pre_gui_output(pre_gui_output or {}, render_settings, shared_parameter_values)

    submitter_dialog = SubmitJobToDeadlineDialog(
        job_setup_widget_type=SceneSettingsWidget,
        initial_job_settings=render_settings,
        initial_shared_parameter_values=shared_parameter_values,
        auto_detected_attachments=auto_detected_attachments,
        attachments=attachments,
        on_create_job_bundle_callback=on_create_job_bundle_callback,
        parent=parent,
        f=f,
        show_host_requirements_tab=True,
        use_deadline_cloud_v2_channel=True,
    )
    submitter_dialog.show()
    return submitter_dialog
