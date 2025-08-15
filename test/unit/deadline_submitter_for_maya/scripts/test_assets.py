# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import os
import re
from pathlib import Path
from unittest.mock import MagicMock, call, patch
from typing import Generator, List, Optional

import pytest

import deadline.maya_submitter.assets as assets_module
from deadline.maya_submitter.file_path_editor import FileRef
from deadline.maya_submitter.scene import RendererNames


class TestParseSceneAssets:
    """Tests for AssetIntrospector.parse_scene_assets"""

    @pytest.fixture(autouse=True)
    def mock_expand_path(self) -> Generator[MagicMock, None, None]:
        with patch.object(assets_module.AssetIntrospector, "_expand_path") as m:
            m.side_effect = lambda p: [Path(p)]
            yield m

    @pytest.fixture
    def yeti_files(self) -> List[Path]:
        return [Path(f"/path/to/yeti/file{i}") for i in range(10)]

    @pytest.fixture(autouse=True)
    def mock_get_yeti_files(self, yeti_files: List[Path]) -> Generator[MagicMock, None, None]:
        with patch.object(assets_module.AssetIntrospector, "_get_yeti_files") as m:
            m.return_value = yeti_files
            yield m

    @pytest.fixture(autouse=True)
    def mock_renderer(self) -> Generator[MagicMock, None, None]:
        with patch.object(assets_module.Scene, "renderer") as m:
            yield m

    @pytest.fixture
    def fileRefs(self) -> List[FileRef]:
        return [FileRef(path=f"/path/to/file/ref{i}", exists=True) for i in range(10)]

    @pytest.fixture(autouse=True)
    def mock_fileRefs(self, fileRefs: List[FileRef]) -> Generator[MagicMock, None, None]:
        with patch.object(assets_module.FilePathEditor, "fileRefs") as m:
            m.return_value = fileRefs
            yield m

    @pytest.fixture
    def scene_name(self) -> str:
        return "/path/to/scene"

    @pytest.fixture(autouse=True)
    def mock_scene_name(self, scene_name: str) -> Generator[MagicMock, None, None]:
        with patch.object(assets_module.Scene, "name") as m:
            m.return_value = scene_name
            yield m

    def test_parses_scene_assets(
        self,
        yeti_files: List[Path],
        fileRefs: List[FileRef],
        scene_name: str,
    ) -> None:
        # GIVEN
        progress_callback = MagicMock()

        # WHEN
        results = assets_module.AssetIntrospector().parse_scene_assets(progress_callback)

        # THEN
        assert len(results) == len(yeti_files) + len(fileRefs) + 1  # +1 is the scene file
        for f in yeti_files:
            assert f in results
        for fileRef in fileRefs:
            assert Path(fileRef.path) in results
        assert Path(scene_name) in results
        progress_callback.assert_has_calls(
            [
                call("Searching for Yeti cache files..."),
                call("Processing 10 file references..."),
                call("Found 21 assets in total"),
            ],
            any_order=True,
        )

    @patch.object(assets_module.AssetIntrospector, "_get_tx_files")
    def test_gets_arnold_texture_files(
        self,
        mock_get_tx_files: MagicMock,
        mock_renderer: MagicMock,
    ) -> None:
        # GIVEN
        tx_files = {Path(f"/path/to/file{i}.tx") for i in range(10)}
        mock_get_tx_files.return_value = tx_files
        mock_renderer.return_value = RendererNames.arnold.value
        progress_callback = MagicMock()

        # WHEN
        results = assets_module.AssetIntrospector().parse_scene_assets(progress_callback)

        # THEN
        for f in tx_files:
            assert f in results
        progress_callback.assert_has_calls(
            [
                call("Searching for Arnold texture files..."),
            ],
            any_order=True,
        )

    @patch.object(assets_module.AssetIntrospector, "_get_tex_files")
    def test_gets_renderman_texture_files(
        self,
        mock_get_tex_files: MagicMock,
        mock_renderer: MagicMock,
    ) -> None:
        # GIVEN
        tex_files = {Path(f"/path/to/file{i}.tex") for i in range(10)}
        mock_get_tex_files.return_value = tex_files
        mock_renderer.return_value = RendererNames.renderman.value
        progress_callback = MagicMock()

        # WHEN
        results = assets_module.AssetIntrospector().parse_scene_assets(progress_callback)

        # THEN
        for f in tex_files:
            assert f in results
        progress_callback.assert_has_calls(
            [
                call("Searching for Renderman texture files..."),
            ],
            any_order=True,
        )


@patch.object(assets_module.AssetIntrospector, "_expand_path")
@patch.object(assets_module.Scene, "yeti_cache_files")
def test_gets_yeti_files(
    mock_yeti_cache_files: MagicMock,
    mock_expand_path: MagicMock,
) -> None:
    # GIVEN
    yeti_cache_files = [f"/path/to/yeti/cache/file{i}" for i in range(200)]
    mock_yeti_cache_files.return_value = yeti_cache_files
    mock_expand_path.side_effect = lambda p: [Path(p), Path(p).with_suffix(".extra")]
    progress_callback = MagicMock()

    # WHEN
    results = assets_module.AssetIntrospector()._get_yeti_files(progress_callback)

    # THEN
    assert len(results) == len(yeti_cache_files) * 2
    for f in yeti_cache_files:
        assert Path(f) in results
        assert Path(f).with_suffix(".extra") in results
    progress_callback.assert_has_calls(
        [
            call("Processing 200 Yeti cache files..."),
            call("Processed 100/200 Yeti cache files..."),
            call("Completed processing all 200 Yeti cache files"),
        ],
        any_order=True,
    )


@patch.object(assets_module.AssetIntrospector, "_expand_path")
def test_get_tex_files(mock_expand_path: MagicMock) -> None:
    # GIVEN
    mock_expand_path.side_effect = lambda x: [Path(x)]
    mock_maya = MagicMock()
    mock_rfm2 = MagicMock()
    with patch.dict(
        "sys.modules",
        {
            "maya": mock_maya,
            "maya.cmds": mock_maya.cmds,
            "rfm2": mock_rfm2,
            "rfm2.txmanager_maya": mock_rfm2.txmanager_maya,
        },
    ):
        texture_directory = "/path/to/directory"
        maya_referenced_files = [
            item for i in range(200) for item in (f"file{i}", f"this.is.an.attr{i}")
        ]
        renderman_tex_files = {
            os.path.join(texture_directory, f): os.path.join(
                texture_directory, f"{f}.additional.file"
            )
            for f in maya_referenced_files[::4]
        }
        mock_maya.cmds.filePathEditor.side_effect = [
            # Call 1: listDirectories=""
            [texture_directory],
            # Call 2: listFiles=/path/to/directory
            maya_referenced_files,
            # Call 3: listFiles=/path/to/directory
            maya_referenced_files,
        ]
        # Simulate half of the texture files not being in tx manager
        mock_rfm2.txmanager_maya.get_texture_by_path.side_effect = lambda p, _: renderman_tex_files[
            p
        ]
        progress_callback = MagicMock()

        # WHEN
        result = assets_module.AssetIntrospector()._get_tex_files(progress_callback)

    # THEN
    assert len(result) == len(maya_referenced_files) // 2 + len(renderman_tex_files)
    for f in maya_referenced_files[::2]:
        assert Path(os.path.join(texture_directory, f)) in result
    for f in renderman_tex_files.values():
        assert Path(f) in result
    progress_callback.assert_has_calls(
        [
            call("Processing 200 Renderman texture files..."),
            call("Processed 100/200 Renderman texture files..."),
            call("Processed 200/200 Renderman texture files..."),
            call("Completed processing all 200 Renderman texture files"),
        ],
        any_order=True,
    )


class TestGetTxFiles:
    """Tests for AssetIntrospector._get_tx_files (Arnold texture files)"""

    @pytest.fixture(autouse=True)
    def mock_Scene(self) -> Generator[MagicMock, None, None]:
        with patch.object(assets_module, "Scene") as m:
            # Default to actually getting arnold texures
            m.autotx.return_value = True
            m.use_existing_tiled_textures.return_value = True
            yield m

    def test_returns_empty_when_not_arnold(self, mock_Scene: MagicMock) -> None:
        # GIVEN
        mock_Scene.autotx.return_value = False
        mock_Scene.use_existing_tiled_textures.return_value = False

        # WHEN
        result = assets_module.AssetIntrospector()._get_tx_files()

        # THEN
        assert result == set()
        mock_Scene.get_arnold_texture_files.assert_not_called()

    @patch.object(assets_module.os.path, "isfile")
    @patch.object(assets_module.AssetIntrospector, "_expand_path")
    @patch.object(assets_module.AssetIntrospector, "_get_arnold_texture_files")
    def test_gets_tx_files(
        self,
        mock_get_arnold_texture_files: MagicMock,
        mock_expand_path: MagicMock,
        mock_isfile: MagicMock,
    ) -> None:
        # GIVEN
        # 200 texture files
        arnold_texture_files = {
            f"/path/to/texture/file{i}.png": {"texture": "info"} for i in range(200)
        }
        # 100 associated tx files (every other texture file)
        associated_tx_files = {
            f"/path/to/texture/file{i}.tx" for i in range(0, len(arnold_texture_files), 2)
        }

        mock_get_arnold_texture_files.return_value = arnold_texture_files
        mock_expand_path.side_effect = [[Path(path)] for path in arnold_texture_files]
        mock_isfile.side_effect = lambda p: str(p) in associated_tx_files
        progress_callback = MagicMock()

        # WHEN
        result = assets_module.AssetIntrospector()._get_tx_files(progress_callback)

        # THEN
        assert len(result) == len(arnold_texture_files) + len(associated_tx_files)
        for arnold_texture_file in arnold_texture_files:
            assert Path(arnold_texture_file) in result
        for associated_tx_file in associated_tx_files:
            assert Path(associated_tx_file) in result
        progress_callback.assert_has_calls(
            [
                call("Processing 200 Arnold texture files..."),
                call("Processed 100/200 Arnold texture files..."),
                call("Completed processing all 200 Arnold texture files"),
            ],
            # Required because Python implicitly calls progress_callback.__bool__()
            # for all the "if progress_callback" checks
            any_order=True,
        )


class TestGetArnoldTextureFiles:
    """Tests for AssetIntrospector._get_arnold_texture_files"""

    @pytest.fixture(autouse=True)
    def mock_mtoa(self) -> Generator[MagicMock, None, None]:
        mock_mtoa = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "mtoa": mock_mtoa,
                "mtoa.txManager": mock_mtoa.txManager,
                "mtoa.txManager.lib": mock_mtoa.txManager.lib,
            },
        ):
            yield mock_mtoa

    @pytest.fixture(autouse=True)
    def mock_maya(self) -> Generator[MagicMock, None, None]:
        mock_maya = MagicMock()
        with patch.dict("sys.modules", {"maya": mock_maya, "maya.cmds": mock_maya.cmds}):
            yield mock_maya

    def test_gets_arnold_texture_files(self, mock_mtoa: MagicMock) -> None:
        # GIVEN
        mock_mtoa.txManager.lib.get_scanned_files.return_value = {
            "/path/to/texture": {"texture": "info"}
        }

        # WHEN
        result = assets_module.AssetIntrospector()._get_arnold_texture_files()

        # THEN
        assert result == {"/path/to/texture": {"texture": "info"}}
        mock_mtoa.txManager.lib.get_scanned_files.assert_called_once_with(
            mock_mtoa.txManager.lib.scene_default_texture_scan
        )

    @pytest.mark.parametrize(
        argnames="mtoa_version",
        argvalues=["1.2.3", None],
        ids=["mtoa version lookup succeess", "mtoa version lookup failed"],
    )
    def test_handles_bad_escape_error(
        self,
        mtoa_version: Optional[str],
        mock_mtoa: MagicMock,
        mock_maya: MagicMock,
    ) -> None:
        # GIVEN
        mock_mtoa.txManager.lib.get_scanned_files.side_effect = re.error(
            r"bad escape %F at position 0"
        )
        if mtoa_version:
            mock_maya.cmds.pluginInfo.return_value = mtoa_version
        else:
            mock_maya.cmds.pluginInfo.side_effect = Exception()

        # WHEN
        with pytest.raises(Exception) as raised_exc:
            assets_module.AssetIntrospector()._get_arnold_texture_files()

        # THEN
        expected_mtoa_version_str = (
            mtoa_version if mtoa_version else "UNKNOWN - Please check 'Arnold' > 'About'"
        )
        assert (
            "This error may be caused by a known bug in Arnold for Maya (MtoA) versions less than 5.3.5 (MTOA-1424). "
            "If the installed version of Arnold for Maya is less than 5.3.5, please upgrade to MtoA 5.3.5 or newer and try again. "
            f"Detected MtoA Version: {expected_mtoa_version_str}"
        ) in str(raised_exc.value)
        mock_maya.cmds.pluginInfo.assert_called_once_with("mtoa", query=True, version=True)


class TestExpandPath:
    """Tests for AssetIntrospector._expand_path"""

    @pytest.fixture(autouse=True)
    def mock_frame_list(self) -> Generator[List[int]]:
        with patch.object(assets_module.Animation, "frame_list", return_value=[0]) as m:
            yield m

    @pytest.fixture(autouse=True)
    def mock_findAllFilesForPattern(self) -> Generator[MagicMock, None, None]:
        with patch.object(assets_module, "findAllFilesForPattern", return_value=[]) as m:
            yield m

    def test_expands_f_token(self, mock_findAllFilesForPattern: MagicMock) -> None:
        # GIVEN
        path = "/test/file/path.<f>.png"
        mock_findAllFilesForPattern.return_value = [path.replace("<f>", "0")]

        # WHEN
        result = assets_module.AssetIntrospector()._expand_path(path)

        # THEN
        assert list(result) == [Path("/test/file/path.0.png")]
        mock_findAllFilesForPattern.assert_called_once_with(path, 0)

    def test_expands_number_sign_token(self, mock_findAllFilesForPattern: MagicMock) -> None:
        # GIVEN
        path = "/test/file/path.####.png"
        mock_findAllFilesForPattern.return_value = [path.replace("####", "0000")]

        # WHEN
        result = assets_module.AssetIntrospector()._expand_path(path)

        # THEN
        assert list(result) == [Path("/test/file/path.0000.png")]
        mock_findAllFilesForPattern.assert_called_once_with("/test/file/path.0000.png", 0)

    def test_excludes_metadata_files(self, mock_findAllFilesForPattern: MagicMock) -> None:
        # GIVEN
        path = "/test/file/path.png"
        mock_findAllFilesForPattern.return_value = [
            "Test:Zone.Identifier",
            path,
            f"{path}:Zone.Identifier",
        ]

        # WHEN
        result = assets_module.AssetIntrospector()._expand_path(path)

        # THEN
        assert list(result) == [Path(path)]

    def test_expand_path_caching(self, mock_findAllFilesForPattern: MagicMock) -> None:
        """A test that verifies the lru cache returns an exhausted generator
        if we've already expanded the input path.

        This behaviour gives us performance improvements since subsequent work
        that would check if the cached files exist is completely skipped"""
        # GIVEN
        path = Path("/test/file/path.png")
        mock_findAllFilesForPattern.return_value = [str(path)]
        asset_introspector = assets_module.AssetIntrospector()

        # WHEN
        first_result = asset_introspector._expand_path(str(path))

        # THEN
        assert next(first_result) == path
        with pytest.raises(StopIteration):
            next(first_result)
        assert mock_findAllFilesForPattern.call_count == 1

        # WHEN
        second_result = asset_introspector._expand_path(str(path))
        assert mock_findAllFilesForPattern.call_count == 1

        # THEN
        with pytest.raises(StopIteration):
            next(second_result)
        assert first_result is second_result

        # WHEN
        asset_introspector._expand_path.cache_clear()
        third_result = asset_introspector._expand_path(str(path))

        # THEN
        assert next(third_result) == path
        assert mock_findAllFilesForPattern.call_count == 2
