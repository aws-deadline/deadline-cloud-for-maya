# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from pathlib import Path
from typing import Any
import base64
import io
import json
import yaml
import re

import PIL.Image

import numpy as np

from test.integ.test_const import ASSET_REFERENCES, PARAMETER_VALUES


def are_images_similar(
    expected_image_directory: Path, actual_image_directory: Path, tolerance: int
) -> bool:
    """
    Helper function that compare if the render output from the adaptor match what we expected
    """
    images = [image for image in expected_image_directory.iterdir() if image.is_file()]
    if not images:
        return False
    for image in images:

        # Open the two image files with Pillow https://pillow.readthedocs.io/en/stable/index.html
        # and put them in numpy arrays. Pillow doesn't have a good built-in way to do image comparison
        # with tolerance.
        with PIL.Image.open(actual_image_directory / image.name) as actual_image:
            actual = np.asarray(actual_image)
            with PIL.Image.open(image) as expected_image:
                expected = np.asarray(expected_image)

                # Keep the comparison strict, but show what differed in CI's captured logs.
                if actual.shape != expected.shape or not np.allclose(
                    actual, expected, atol=tolerance
                ):
                    diagnostic: dict[str, Any] = {
                        "filename": image.name,
                        "actual_mode": actual_image.mode,
                        "expected_mode": expected_image.mode,
                        "actual_shape": actual.shape,
                        "expected_shape": expected.shape,
                        "tolerance": tolerance,
                    }
                    if actual.shape == expected.shape:
                        delta = np.abs(actual.astype(float) - expected.astype(float))
                        diagnostic["max_error"] = float(delta.max())
                        diagnostic["mean_error"] = float(delta.mean())
                        diagnostic["error_percentiles"] = np.percentile(
                            delta, [50, 90, 99, 100]
                        ).tolist()
                        diagnostic["outside_tolerance_fraction"] = float(np.mean(delta > tolerance))
                    preview = actual_image.copy()
                    preview.thumbnail((320, 180))
                    encoded = io.BytesIO()
                    preview.save(encoded, format="PNG")
                    diagnostic["actual_preview_png"] = base64.b64encode(encoded.getvalue()).decode(
                        "ascii"
                    )
                    print("RENDER_IMAGE_DIAGNOSTIC " + json.dumps(diagnostic), flush=True)
                    return False
    return True


def extract_parameter_value(expected_parameter_values, param_name):
    """
    Helper function that extract parameter value for path convert if needed
    """
    for param in expected_parameter_values["parameterValues"]:
        if param["name"] == param_name:
            return param["value"]
    return None


def are_parameter_values_similar(job_history_dir: Path, expected_parameter_values: dict[str, list]):
    """
    Helper function that asserts that parameter values in the job bundle are what's expected.
    """
    with open(job_history_dir / PARAMETER_VALUES) as actual:
        actual_parameter_values = yaml.safe_load(actual)

        # Compare the lengths so that we can cover the case of duplicate parameters.
        assert len(actual_parameter_values["parameterValues"]) == len(
            expected_parameter_values["parameterValues"]
        )

        # The order of the list of parameter values doesn't matter,
        for parameter_value in expected_parameter_values["parameterValues"]:
            name = parameter_value["name"]
            value = parameter_value["value"]

            # Convert to help with Windows path format. Most Maya path
            # queries (cmds.file, cmds.workspace) auto-normalize to
            # forward slashes on Windows, but a few (e.g.
            # cmds.colorManagementPrefs) preserve the input verbatim. To
            # avoid coupling the test to which side normalizes, we
            # canonicalize both expected and actual to forward slashes.
            if not isinstance(value, int):
                value = value.replace("\\", "/")

            actual_value = extract_parameter_value(actual_parameter_values, name)
            if isinstance(actual_value, str):
                actual_value = actual_value.replace("\\", "/")

            assert value == actual_value


def are_asset_references_similar(
    job_history_dir: Path,
    expected_asset_references: dict[str, dict[str, Any]],
    expected_scene_file_paths: list[str] = [],
):
    """
    Helper function that asserts that asset reference values in the job bundle are what's expected.
    """
    with open(job_history_dir / ASSET_REFERENCES) as actual:
        actual_asset_reference = yaml.safe_load(actual)
        actual_filenames = set(actual_asset_reference["assetReferences"]["inputs"]["filenames"])
        expected_filenames = set(
            expected_asset_references["assetReferences"]["inputs"]["filenames"]
        )

        actual_input_directories = set(
            actual_asset_reference["assetReferences"]["inputs"]["directories"]
        )
        expected_input_directories = set(
            expected_asset_references["assetReferences"]["inputs"]["directories"]
        )

        # If we have expected file paths, find matching files in actual and add them to expected
        if expected_scene_file_paths:
            for pattern in expected_scene_file_paths:
                matching_files = [f for f in actual_filenames if re.search(pattern, f)]
                assert (
                    matching_files
                ), f"Expected to find files matching pattern '{pattern}' in asset references, but found none. Actual filenames: {actual_filenames}"
                expected_filenames.update(matching_files)

            # Verify job_history_dir is part of the actual input directories and add it to expected
            job_history_str = str(job_history_dir)
            for actual_dir in actual_input_directories:
                if actual_dir in job_history_str:
                    expected_input_directories.add(actual_dir)

        # We don't care what order the filenames list is in, so turn it into a set for easier comparison.
        # Compare the lengths before we turn it into a set so that we can cover the case of duplicate assets.
        assert len(actual_filenames) == len(expected_filenames)
        assert len(actual_input_directories) == len(expected_input_directories)

        # Update the expected asset references with the matched files and directories
        expected_asset_references["assetReferences"]["inputs"]["filenames"] = expected_filenames
        actual_asset_reference["assetReferences"]["inputs"]["filenames"] = actual_filenames

        expected_asset_references["assetReferences"]["inputs"][
            "directories"
        ] = expected_input_directories
        actual_asset_reference["assetReferences"]["inputs"][
            "directories"
        ] = actual_input_directories

        directories = expected_asset_references["assetReferences"]["outputs"]["directories"]
        expected_asset_references["assetReferences"]["outputs"]["directories"] = [
            d.replace("\\", "/") for d in directories
        ]
        assert actual_asset_reference == expected_asset_references
