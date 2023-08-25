# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Generator, Iterable

from .pymel_additions import FilePathEditor
from .scene import Animation, RendererNames, Scene
from .utils import findAllFilesForPattern

_FRAME_RE = re.compile("#+")


class AssetIntrospector:
    def parse_scene_assets(self) -> set[Path]:
        """
        Searches the scene for assets, and filters out assets that are not needed for Rendering.

        Returns:
            set[Path]: A set containing filepaths of assets needed for Rendering
        """
        # clear filesystem cache from last run
        self._expand_path.cache_clear()
        # Grab tx files (if we need to)
        assets: set[Path] = self._get_tx_files()

        for ref in FilePathEditor.fileRefs():
            normalized_path = os.path.normpath(ref.path)
            # Files without tokens may already have been checked, if so, skip
            if normalized_path in assets:
                continue
            # Files with tokens may have already been checked when grabbing arnold's tx files.
            # Since the expand path returns a generator, it'll actually skip rechecking
            # these files since it returns the original generator which is exhausted.
            for path in self._expand_path(normalized_path):
                assets.add(path)

        assets.add(Path(Scene.name()))

        return assets

    def _get_tx_files(self) -> set[Path]:
        """
        If the renderer is Arnold, searches for both source and tx files

        Returns:
            set[Path]: A set of original asset paths and their associated tx files.
        """

        arnold_textures_files: set[Path] = set()
        if not Scene.renderer() == RendererNames.arnold.value or not (
            Scene.autotx() or Scene.use_existing_tiled_textures()
        ):
            return arnold_textures_files

        for img_path in self._get_arnold_texture_files():
            for expanded_path in self._expand_path(img_path):
                arnold_textures_files.add(expanded_path)
                # expanded files are guaranteed to exist, but we haven't checked the associated .tx file yet
                if os.path.isfile(expanded_path.with_suffix(".tx")):
                    arnold_textures_files.add(expanded_path.with_suffix(".tx"))

        return arnold_textures_files

    def _get_arnold_texture_files(self):
        """
        Imports inner Arnold functions to get list of textures.

        Returns:
            dict[str, texture_info]: A mapping of original absolute texture paths to their properties.
        """
        import mtoa.txManager.lib as _mtoa  # type: ignore

        return _mtoa.get_scanned_files(_mtoa.scene_default_texture_scan)

    @lru_cache(maxsize=None)
    def _expand_path(self, path: str) -> Generator[Path, None, None]:
        """
        Some animated textures are padded with multiple '#' characters to indicate the current frame
        number, while others such as animated multi-tiled UV textures will have tokens such as <f>,
        or <UDIM> which are replaced at render time.

        This function expands these tokens and characters to find all the assets which will be
        required at render time.

        This function gets called for a varierty of file groupings (ie. Arnold's txmanager, Maya's FilePathEditor)
        Since this func has an lru cache and returns a generator, it'll actually skip rechecking these files since
        it returns the original generator which is exhausted. You can, however, force it to recheck
        these files by performing asset_introspector._expand_path.cache_clear() call.

        Args:
            path (str): A path with tokens to replace

        Yields:
            Generator[str, None, None]: A series of paths that match the pattern provided.
        """
        frame_re_matches = _FRAME_RE.findall(path)

        frame_list: Iterable[int] = [0]
        if frame_re_matches or "<f>" in path:
            frame_list = Animation.frame_list()

        for frame in frame_list:
            working_path = path
            for group in frame_re_matches:
                working_path = working_path.replace(group, str(frame).zfill(len(group)))
            paths = findAllFilesForPattern(working_path, frame)
            for p in paths:
                if not p.endswith(":Zone.Identifier"):  # Metadata files that erroneously match
                    yield Path(p)
