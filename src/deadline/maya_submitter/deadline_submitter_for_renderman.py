import os
import yaml
from pathlib import Path

from deadline.client.ui.dialogs.submit_job_to_deadline_dialog import (  # pylint: disable=import-error
    SubmitJobToDeadlineDialog,
)
from deadline.client.job_bundle.submission import AssetReferences
from deadline.client.job_bundle import deadline_yaml_dump

from PySide2.QtCore import Qt

from .ui.components.scene_settings_tab_renderman import SceneSettingsWidget

from .data_classes_renderman.render_submitter_settings import (
    INSTALLATION_REQUIREMENTS_DEFAULT,
    RenderSubmitterUISettings,
)

from .assets_renderman import RibFileProcessor
from typing import Any

g_submitter_dialog = None


def _get_job_template(settings: RenderSubmitterUISettings) -> dict[str, Any]:
    # Load the default Nuke job template, and then fill in scene-specific
    # values it needs.
    with open(Path(__file__).parent / "default_renderman_job_template.yaml") as f:
        job_template = yaml.safe_load(f)

    # Set the job's name
    job_template["name"] = settings.name

    # Get a map of the parameter definitions for easier lookup
    parameter_def_map = {param["name"]: param for param in job_template["parameterDefinitions"]}

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
            "deadline_cloud_for_renderman",}:
            raise RuntimeError(
                "The Developer Option 'Include Adaptor Wheels' is enabled, but the wheels directory contains the wrong wheels:\n"
                + "Expected: deadline_cloud_for_renderman\n"
                + f"Actual: {wheels_path_package_names}"
            )

        override_adaptor_wheels_param = [
            param
            for param in override_environment["parameterDefinitions"]
            if param["name"] == "OverrideAdaptorWheels"
        ][0]
        override_adaptor_wheels_param["default"] = str(wheels_path)
        override_adaptor_name_param = [
            param
            for param in override_environment["parameterDefinitions"]
            if param["name"] == "OverrideAdaptorName"
        ][0]
        override_adaptor_name_param["default"] = "RenderManAdaptor"

        # There are no parameter conflicts between these two templates, so this works
        job_template["parameterDefinitions"].extend(override_environment["parameterDefinitions"])

        # Add the environment to the end of the template's job environments
        if "jobEnvironments" not in job_template:
            job_template["jobEnvironments"] = []
        job_template["jobEnvironments"].append(override_environment["environment"])

    return job_template


def submission_callback(
    widget: SubmitJobToDeadlineDialog,
    job_bundle_dir: str,
    settings: RenderSubmitterUISettings,
    queue_parameters: list[dict[str, Any]],
    asset_references: dict[str, Any]
) -> None:
    print("-----------------------------------------------------")
    job_bundle_path = Path(job_bundle_dir)
    print(settings.rib_file_paths)
    parameter_values = [{"name": "RibFile", "value": settings.rib_file_paths},
                        {"name": "ContinueOnError", "value": settings.continue_on_error}]

    job_template = _get_job_template(settings)

    # If we're overriding the adaptor with wheels, remove deadline_cloud_for_renderman from the RezPackages
    if settings.include_adaptor_wheels:
        rez_param = {}
        # Find the RezPackages parameter definition
        for param in queue_parameters:
            if param["name"] == "RezPackages":
                rez_param = param
                break
        # Remove the deadline_cloud_for_renderman rez package
        if rez_param:
            rez_param["value"] = " ".join(
                pkg
                for pkg in rez_param["value"].split()
                if not pkg.startswith("deadline_cloud_for_renderman")
            )

    parameter_values.extend(
        {"name": param["name"], "value": param["value"]} for param in queue_parameters
    )

    with open(job_bundle_path / "template.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump(job_template, f, indent=1)

    with open(job_bundle_path / "parameter_values.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump({"parameterValues": parameter_values}, f, indent=1)

    with open(job_bundle_path / "asset_references.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump(asset_references.to_dict(), f, indent=1)


def show_renderman_submitter(rib_filenames) -> "SubmitJobToDeadlineDialog":
    global g_submitter_dialog

    processor = RibFileProcessor()
    asset_refs = AssetReferences()

    for rib_filename in rib_filenames:
        asset_refs = processor.read(rib_filename, asset_refs)

    # TEMP - upload dependency libs - TODO: remove.
    asset_refs.input_directories.add("C:\\Users\\sphrose\\lib")
    # END TEMP

    render_settings: RenderSubmitterUISettings = RenderSubmitterUISettings()
    render_settings.rib_file_paths = ','.join(rib_filenames)
    render_settings.name = processor.output_file

    g_submitter_dialog = SubmitJobToDeadlineDialog(
        job_setup_widget_type=SceneSettingsWidget,
        initial_shared_parameter_values={"RezPackages": "renderman deadline_cloud_for_renderman"},
        initial_job_settings=render_settings,
        auto_detected_attachments=asset_refs,
        attachments=AssetReferences(),
        on_create_job_bundle_callback=submission_callback,
        parent=None,
        f=Qt.WindowFlags()
    )

    g_submitter_dialog.show()
    return g_submitter_dialog

