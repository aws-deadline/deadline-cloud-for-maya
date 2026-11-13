# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Scene preparation and bundle comparison against job_bundle_output_tests/.

These mirror job_bundle_output_test_runner.py, which generated the expected
bundles, so a bundle exported through the GUI compares against the same files.
"""

from __future__ import annotations

import difflib
import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUNDLE_OUTPUT_TESTS = REPO_ROOT / "job_bundle_output_tests"
BUNDLE_FILES = ("template.yaml", "parameter_values.yaml", "asset_references.yaml")
NORMALIZED_DIR = "/normalized/job/bundle/dir"


def copy_case_scene(case: str, dest_dir: Path) -> Path:
    """Copy a case's scene folder to dest_dir, rewriting the paths inside the scene.

    Like the runner's _copy_dcc_scene_file: each scene references a file named
    scene_file_to_reference.m[ab], which reveals the directory the scene was saved
    in, and every occurrence of that directory is replaced with dest_dir.
    """
    source_scene = BUNDLE_OUTPUT_TESTS / case / "scene" / f"{case}.ma"
    shutil.copytree(source_scene.parent, dest_dir, dirs_exist_ok=True)
    contents = source_scene.read_text(encoding="utf8")
    original_dir = None
    for line in contents.splitlines():
        match = re.match(r'.*"(.*)[/\\]scene_file_to_reference.m[ab]".*', line)
        if match:
            original_dir = match.group(1)
            break
    if not original_dir:
        raise ValueError(f"{source_scene} does not reference scene_file_to_reference.m[ab]")
    dest_scene = dest_dir / source_scene.name
    dest_scene.write_text(contents.replace(original_dir, dest_dir.as_posix()), encoding="utf8")
    return dest_scene


def normalize_bundle(bundle_dir: Path, scene_dir: Path) -> dict[str, str]:
    """Read the bundle's files with scene_dir replaced as the runner does."""
    native = str(scene_dir)
    posix = scene_dir.as_posix()
    normalized = {}
    for name in BUNDLE_FILES:
        text = (bundle_dir / name).read_text(encoding="utf8")
        for prefix in (native + "\\", posix + "/"):
            text = text.replace(prefix, NORMALIZED_DIR + "/")
        for prefix in (native, posix):
            text = text.replace(prefix, NORMALIZED_DIR)
        normalized[name] = text
    return normalized


def expected_bundle(case: str) -> dict[str, str]:
    expected_dir = BUNDLE_OUTPUT_TESTS / case / "expected_job_bundle"
    return {name: (expected_dir / name).read_text(encoding="utf8") for name in BUNDLE_FILES}


def assert_bundles_equal(expected: dict[str, str], actual: dict[str, str]) -> None:
    differences = []
    for name in BUNDLE_FILES:
        if expected[name] != actual[name]:
            differences.append(
                "".join(
                    difflib.unified_diff(
                        expected[name].splitlines(keepends=True),
                        actual[name].splitlines(keepends=True),
                        f"expected/{name}",
                        f"actual/{name}",
                    )
                )
            )
    assert not differences, "Job bundle differs from the expected bundle:\n" + "\n".join(
        differences
    )
