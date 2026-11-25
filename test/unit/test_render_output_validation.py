# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import pytest
from PIL import Image

from test.integ.helpers.output_comparison import are_images_similar
from test.integ import test_maya_adaptors


@pytest.mark.parametrize(
    "method",
    [
        "test_minimal_scene_adaptor",
        "test_redshift_scene_adaptor",
        "test_mtoa_scene_adaptor",
        "test_vray_scene_adaptor",
    ],
)
def test_render_mismatch_fails_each_adaptor_case(monkeypatch, tmp_path, method):
    monkeypatch.setattr(test_maya_adaptors, "run_adaptor_test", lambda *args: None)
    monkeypatch.setattr(test_maya_adaptors, "run_native_reference", lambda *args: tmp_path)
    monkeypatch.setattr(test_maya_adaptors, "are_images_similar", lambda *args, **kwargs: False)

    with pytest.raises(AssertionError):
        getattr(test_maya_adaptors.TestAdaptors(), method)(tmp_path, tmp_path)


@pytest.mark.parametrize(
    "pixel,size,similar",
    [(100, (2, 2), True), (102, (2, 2), True), (255, (2, 2), False), (100, (3, 3), False)],
)
def test_image_comparison_checks_pixels_and_dimensions(tmp_path, pixel, size, similar):
    expected, actual = tmp_path / "expected", tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    Image.new("L", (2, 2), 100).save(expected / "frame.png")
    Image.new("L", size, pixel).save(actual / "frame.png")

    assert are_images_similar(expected, actual, tolerance=2) is similar


def test_empty_reference_directory_cannot_pass(tmp_path):
    assert not are_images_similar(tmp_path, tmp_path, tolerance=2)


def test_sampling_comparison_accepts_sparse_noise_but_rejects_a_local_defect(tmp_path):
    expected, actual = tmp_path / "expected", tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    Image.new("L", (256, 256), 100).save(expected / "frame.png")
    frame = Image.new("L", (256, 256), 100)
    frame.putpixel((20, 20), 116)
    frame.save(actual / "frame.png")
    assert are_images_similar(expected, actual, 2, comparison="sampling")

    # Whole-image RMS is below 2, but this localized change must still fail.
    frame.paste(150, (0, 0, 8, 8))
    frame.save(actual / "frame.png")
    assert not are_images_similar(expected, actual, 2, comparison="sampling")


def test_legacy_layout_comparison_rejects_a_changed_scene_color(tmp_path):
    expected, actual = tmp_path / "expected", tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    Image.new("RGB", (960, 540), (100, 100, 100)).save(expected / "frame.png")
    Image.new("RGB", (960, 540), (130, 100, 100)).save(actual / "frame.png")
    assert not are_images_similar(expected, actual, 2, comparison="layout")
