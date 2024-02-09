# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import sys
from collections import namedtuple
from os.path import normpath, split
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

import deadline.maya_submitter.assets as assets_module
import deadline.maya_submitter.utils as utils_module

ArnoldConfig = namedtuple(
    "ArnoldConfig", ["currentRenderer", "autotx", "use_existing_tiled_textures"]
)


class TestSceneIntrospection:
    project_path = "/mnt/maya/project"
    if sys.platform.startswith("win"):
        project_path = "C:/Maya/project"

    # Set-up the filesystem for the test in a {dirname: filename} mapping
    # includes files that wouldn't be in the file result
    filesystem = {
        # All "filesystem" calls normalize the directory,
        # so normpath works for both Linux and Windows
        normpath(project_path): [
            "file1.png",
            "file1.tx",
            "file1.png:Zone.Identifier",
            "file2.png",
            "file2.tx",
            "file3.png",
            "file4.0000.png",
            "file4.0000.tx",
            "file4.0001.png",
            "file4.0001.tx",
            "file4.0002.png",
            "file4.0002.tx",
            "file4.0003.png",
            "file4.0003.tx",
            "file5.1001.png",
            "file5.1001.tx",
            "file5.1010.png",
            "file5.1010.tx",
            "file5.1011.png",
        ],
    }

    @classmethod
    def listdir(cls, directory) -> list[str]:
        return cls.filesystem.get(normpath(directory), [])

    @classmethod
    def isfile(cls, path) -> bool:
        dirname, filename = split(path)
        return filename in cls.filesystem.get(normpath(dirname), [])

    @classmethod
    def isdir(cls, path) -> bool:
        return normpath(path) in cls.filesystem

    @classmethod
    def pattern_to_regex(cls, pattern) -> str:
        """mimics maya.app.general.fileTexturePathResolver._patternToRegex for our known test cases"""
        return pattern.replace("<f>", r"\d+").replace("<UDIM>", r"(?:1001|1010|1011)")

    @classmethod
    def get_texture_by_path(cls, path) -> str:
        return "/my/texture.tex"


@patch.object(utils_module, "_patternToRegex")
@patch("os.path.isdir")
@patch("os.path.isfile")
@patch("os.listdir")
def test_expand_path_caching(
    mock_listdir: Mock,
    mock_isfile: Mock,
    mock_isdir: Mock,
    mock_pattern_to_regex: Mock,
):
    """A test that verifies the lru cache returns an exhausted generator
    if we've already expanded the input path.

    This behaviour gives us performance improvements since subsequent work
    that would check if the cached files exist is completely skipped"""
    # GIVEN
    path = Path("/test/file/path.png")
    mock_isfile.return_value = True
    mock_isdir.return_value = True
    mock_listdir.return_value = [path.name]
    mock_pattern_to_regex.return_value = path.name
    asset_introspector = assets_module.AssetIntrospector()

    # WHEN
    first_result = asset_introspector._expand_path(str(path))

    # THEN
    assert next(first_result) == path
    with pytest.raises(StopIteration):
        next(first_result)

    # WHEN
    second_result = asset_introspector._expand_path(str(path))

    # THEN
    with pytest.raises(StopIteration):
        next(second_result)
    assert first_result is second_result

    # WHEN
    asset_introspector._expand_path.cache_clear()
    third_result = asset_introspector._expand_path(str(path))

    # THEN
    assert next(third_result) == path


@patch.object(utils_module, "_patternToRegex")
@patch("os.path.isdir")
@patch("os.path.isfile")
@patch("os.listdir")
@patch("maya.cmds.filePathEditor")
def test_get_tex_files(
    mock_filePathEditor: Mock,
    mock_listdir: Mock,
    mock_isfile: Mock,
    mock_isdir: Mock,
    mock_pattern_to_regex: Mock,
):

    # A test that verifies the logic for renderman tex file discovery

    # GIVEN
    path = "/tmp/"
    basename = "mytexture1.exr"
    tex_suffix = ".srgb_acescg.tex"
    mock_pattern_to_regex.return_value = path + basename
    mock_isfile.return_value = True
    mock_isdir.return_value = True
    mock_listdir.return_value = [path + basename]

    mock_filePathEditor.side_effect = [
        [path],
        [basename, "skydome_light.map"],
    ]

    mocked_rfm2_txmanager = MagicMock()
    # mock the import of a non existent library (renderman for maya)
    sys.modules["rfm2.txmanager_maya"] = mocked_rfm2_txmanager
    mocked_rfm2_txmanager.get_texture_by_path.return_value = path + basename + tex_suffix

    # WHEN
    asset_introspector = assets_module.AssetIntrospector()
    result = asset_introspector._get_tex_files()

    # THEN
    assert result == set([path + basename + tex_suffix])
