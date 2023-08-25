# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import sys
from collections import namedtuple
from os.path import normpath, split
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

import deadline_submitter_for_maya.scripts.aws_deadline.assets as assets_module
import deadline_submitter_for_maya.scripts.aws_deadline.scene as scene_module
import deadline_submitter_for_maya.scripts.aws_deadline.utils as utils_module
from deadline_submitter_for_maya.scripts.aws_deadline.assets import AssetIntrospector
from deadline_submitter_for_maya.scripts.aws_deadline.pymel_additions import FileRef

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

    @pytest.mark.parametrize(
        "arnold_config",
        [
            ArnoldConfig(currentRenderer="arnold", autotx=True, use_existing_tiled_textures=True),
            ArnoldConfig(currentRenderer="arnold", autotx=True, use_existing_tiled_textures=False),
            ArnoldConfig(currentRenderer="arnold", autotx=False, use_existing_tiled_textures=True),
        ],
    )
    @patch.object(AssetIntrospector, "_get_arnold_texture_files")
    @patch.object(assets_module, "FilePathEditor")
    @patch.object(scene_module, "SCENE_REF")
    @patch.object(scene_module, "pmc")
    @patch.object(utils_module, "_patternToRegex")
    @patch("os.path.isdir")
    @patch("os.path.isfile")
    @patch("os.listdir")
    def test_parse_scene_assets(
        self,
        mock_listdir: Mock,
        mock_isfile: Mock,
        mock_isdir: Mock,
        mock_pattern_to_regex: Mock,
        mock_pmc: Mock,
        mock_scene: Mock,
        mock_file_path_editor: Mock,
        mock_get_arnold_texture_files: Mock,
        arnold_config: ArnoldConfig,
    ):
        # GIVEN
        scene_name = "my_scene.mb"
        expected_files = {
            # We added the scene name
            Path(scene_name),
            # absolute paths exists
            Path(f"{self.project_path}/file1.png"),
            Path(f"{self.project_path}/file1.tx"),
            # rooted path wit relative elements in maya, absolute in arnold
            Path(f"{self.project_path}/file2.png"),
            Path(f"{self.project_path}/file2.tx"),
            Path(f"{self.project_path}/file3.png"),  # source exists, tx is missing
            # Next 3 pairs are for the frame range of the render
            # frame 3 is not included since it's not in the frame range
            Path(f"{self.project_path}/file4.0000.png"),
            Path(f"{self.project_path}/file4.0000.tx"),
            Path(f"{self.project_path}/file4.0001.png"),
            Path(f"{self.project_path}/file4.0001.tx"),
            Path(f"{self.project_path}/file4.0002.png"),
            Path(f"{self.project_path}/file4.0002.tx"),
            # udim files
            Path(f"{self.project_path}/file5.1001.png"),
            Path(f"{self.project_path}/file5.1001.tx"),
            Path(f"{self.project_path}/file5.1010.png"),
            Path(f"{self.project_path}/file5.1010.tx"),
            Path(f"{self.project_path}/file5.1011.png"),  # udim file missing tx variant
        }

        mock_pattern_to_regex.side_effect = self.pattern_to_regex
        mock_listdir.side_effect = self.listdir
        mock_isfile.side_effect = self.isfile
        mock_isdir.side_effect = self.isdir

        # Set-up references in the Scene
        mock_pmc.sceneName.return_value = scene_name
        file_refs = [
            FileRef(f"{self.project_path}/file1.png", True, "file1.fileTextureName", None),
            FileRef(
                f"{self.project_path}/relative/../file2.png", True, "file2.fileTextureName", None
            ),
            FileRef(f"{self.project_path}/file3.png", True, "file3.fileTextureName", None),
            FileRef(f"{self.project_path}/file4.<f>.png", True, "file4.fileTextureName", None),
            FileRef(f"{self.project_path}/file5.<UDIM>.png", True, "file5.fileTextureName", None),
        ]
        mock_file_path_editor.fileRefs.return_value = file_refs

        arnold_textures = {
            f"{self.project_path}/file1.png": {"txpath": f"{self.project_path}/file1.tx"},
            # Arnold gives absolute paths for paths with relative components
            f"{self.project_path}/file2.png": {"txpath": f"{self.project_path}/file2.tx"},
            f"{self.project_path}/file3.png": {"txpath": f"{self.project_path}/file3.tx"},
            f"{self.project_path}/file4.<f>.png": {"txpath": f"{self.project_path}/file4.<f>.tx"},
            f"{self.project_path}/file5.<UDIM>.png": {
                "txpath": f"{self.project_path}/file5.<UDIM>.tx"
            },
        }
        mock_get_arnold_texture_files.return_value = arnold_textures

        # Set-up render settings
        mock_scene.defaultRenderGlobals.currentRenderer.get.return_value = (
            arnold_config.currentRenderer
        )
        mock_scene.defaultArnoldRenderOptions.autotx.get.return_value = arnold_config.autotx
        mock_scene.defaultArnoldRenderOptions.use_existing_tiled_textures.get.return_value = (
            arnold_config.use_existing_tiled_textures
        )

        mock_scene.defaultRenderGlobals.startFrame.get.return_value = 0
        mock_scene.defaultRenderGlobals.endFrame.get.return_value = 2
        mock_scene.defaultRenderGlobals.byFrameStep.get.return_value = 1

        # WHEN
        actual_files = AssetIntrospector().parse_scene_assets()

        # THEN
        assert actual_files == expected_files

        # WHEN
        # Run it again to verify we can run it multiple times in a row
        # and get the same result.
        actual_files = AssetIntrospector().parse_scene_assets()

        # THEN
        assert actual_files == expected_files

    @pytest.mark.parametrize(
        "arnold_config",
        [
            ArnoldConfig(currentRenderer="arnold", autotx=False, use_existing_tiled_textures=False),
            ArnoldConfig(
                currentRenderer="mayaSoftware", autotx=True, use_existing_tiled_textures=True
            ),
            ArnoldConfig(
                currentRenderer="mayaSoftware", autotx=True, use_existing_tiled_textures=False
            ),
            ArnoldConfig(
                currentRenderer="mayaSoftware", autotx=False, use_existing_tiled_textures=True
            ),
            ArnoldConfig(
                currentRenderer="mayaSoftware", autotx=False, use_existing_tiled_textures=False
            ),
        ],
    )
    @patch.object(assets_module, "FilePathEditor")
    @patch.object(scene_module, "SCENE_REF")
    @patch.object(scene_module, "pmc")
    @patch.object(utils_module, "_patternToRegex")
    @patch("os.path.isdir")
    @patch("os.path.isfile")
    @patch("os.listdir")
    def test_parse_scene_assets_no_tx(
        self,
        mock_listdir: Mock,
        mock_isfile: Mock,
        mock_isdir: Mock,
        mock_pattern_to_regex: Mock,
        mock_pmc: Mock,
        mock_scene: Mock,
        mock_file_path_editor: Mock,
        arnold_config: ArnoldConfig,
    ):
        # GIVEN
        scene_name = "TestScene.mb"
        expected_files = {
            Path(scene_name),
            Path(f"{self.project_path}/file1.png"),
            Path(f"{self.project_path}/file2.png"),
            Path(f"{self.project_path}/file3.png"),
            Path(f"{self.project_path}/file4.0000.png"),
            Path(f"{self.project_path}/file4.0001.png"),
            Path(f"{self.project_path}/file4.0002.png"),
            Path(f"{self.project_path}/file5.1001.png"),
            Path(f"{self.project_path}/file5.1010.png"),
            Path(f"{self.project_path}/file5.1011.png"),
        }
        mock_pattern_to_regex.side_effect = self.pattern_to_regex
        mock_listdir.side_effect = self.listdir
        mock_isfile.side_effect = self.isfile
        mock_isdir.side_effect = self.isdir

        mock_pmc.sceneName.return_value = scene_name
        file_refs = [
            FileRef(f"{self.project_path}/file1.png", True, "file1.fileTextureName", None),
            FileRef(
                f"{self.project_path}/relative/../file2.png", True, "file2.fileTextureName", None
            ),
            FileRef(f"{self.project_path}/file3.png", True, "file3.fileTextureName", None),
            FileRef(f"{self.project_path}/file4.<f>.png", True, "file4.fileTextureName", None),
            FileRef(f"{self.project_path}/file5.<UDIM>.png", True, "file5.fileTextureName", None),
        ]
        mock_file_path_editor.fileRefs.return_value = file_refs

        mock_scene.defaultRenderGlobals.currentRenderer.get.return_value = (
            arnold_config.currentRenderer
        )
        mock_scene.defaultArnoldRenderOptions.autotx.get.return_value = arnold_config.autotx
        mock_scene.defaultArnoldRenderOptions.use_existing_tiled_textures.get.return_value = (
            arnold_config.use_existing_tiled_textures
        )
        mock_scene.defaultRenderGlobals.startFrame.get.return_value = 0
        mock_scene.defaultRenderGlobals.endFrame.get.return_value = 2
        mock_scene.defaultRenderGlobals.byFrameStep.get.return_value = 1

        # WHEN
        actual_files = AssetIntrospector().parse_scene_assets()

        # THEN
        assert actual_files == expected_files
        assert all(f.suffix != ".tx" for f in actual_files)


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
    asset_introspector = AssetIntrospector()

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
