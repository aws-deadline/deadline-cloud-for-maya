# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from pathlib import Path
from typing import Any
import yaml

import PIL.Image

import numpy as np

from test.integ.test_const import ASSET_REFERENCES, PARAMETER_VALUES


def are_images_similar(
    expected_image_directory: Path, actual_image_directory: Path, tolerance: int
) -> bool:
    """
    Helper function that compare if the render output from the adaptor match what we expected
    """
    for image in (expected_image_directory).iterdir():
        if not image.is_file():
            continue

        # Open the two image files with Pillow https://pillow.readthedocs.io/en/stable/index.html
        # and put them in numpy arrays. Pillow doesn't have a good built-in way to do image comparison
        # with tolerance.
        actual = np.asarray(PIL.Image.open(actual_image_directory / image.name))
        expected = np.asarray(PIL.Image.open(image))

        # Check that the two images are the same within a tolerance.
        # It's normal for there to be noise in an output image, so it is unlikely that two
        # renders will be exactly the same.
        if not np.allclose(actual, expected, atol=tolerance):
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

            # Convert to help with Windows path format
            if not isinstance(value, int):
                value = value.replace("\\", "/")

            assert value == extract_parameter_value(actual_parameter_values, name)


def are_asset_references_similar(
    job_history_dir: Path, expected_asset_references: dict[str, dict[str, Any]]
):
    """
    Helper function that asserts that asset reference values in the job bundle are what's expected.
    """
    with open(job_history_dir / ASSET_REFERENCES) as actual:
        actual_asset_reference = yaml.safe_load(actual)
        # We don't care what order the filenames list is in, so turn it into a set for easier comparison.
        # Compare the lengths before we turn it into a set so that we can cover the case of duplicate assets.
        assert len(actual_asset_reference["assetReferences"]["inputs"]["filenames"]) == len(
            expected_asset_references["assetReferences"]["inputs"]["filenames"]
        )
        actual_asset_reference["assetReferences"]["inputs"]["filenames"] = set(
            actual_asset_reference["assetReferences"]["inputs"]["filenames"]
        )
        directories = expected_asset_references["assetReferences"]["outputs"]["directories"]
        expected_asset_references["assetReferences"]["outputs"]["directories"] = [
            d.replace("\\", "/") for d in directories
        ]
        assert actual_asset_reference == expected_asset_references
