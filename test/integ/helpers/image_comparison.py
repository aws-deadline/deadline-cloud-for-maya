# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from pathlib import Path

import PIL.Image

import numpy as np


# Function to compare if the render output from the adaptor match what we expected
def are_images_similar(
    expected_image_directory: Path, actual_image_directory: Path, tolerance: int
) -> bool:
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
