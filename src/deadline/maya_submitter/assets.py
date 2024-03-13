# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Generator, Iterable

from .file_path_editor import FilePathEditor
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
        assets: set[Path] = set()

        # Grab any yeti files
        assets.update(self._get_yeti_files())

        if Scene.renderer() == RendererNames.arnold.value:
            assets.update(self._get_tx_files())
        elif Scene.renderer() == RendererNames.renderman.value:
            assets.update(self._get_tex_files())

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

    def _get_yeti_files(self) -> set[Path]:
        """
        If Yeti plugin nodes are in the scene, searches for fur cache files
        Returns:
            set[Path]: A set of yeti files
        """
        yeti_files: set[Path] = set()
        cache_files = Scene.yeti_cache_files()
        for cache_path in cache_files:
            for expanded_path in self._expand_path(cache_path):
                yeti_files.add(expanded_path)

        return yeti_files

    def _get_tex_files(self) -> set[Path]:
        """
        Searches for Renderman .tex files

        Returns:
            set[Path]: A set of tex files associated to scene textures
        """

        from maya.cmds import filePathEditor  # type: ignore
        from rfm2.txmanager_maya import get_texture_by_path  # type: ignore

        # We query Maya's file path editor for all referenced external files
        # And then query RenderMan's Tx Manager to get the name for the .tex files
        # (needed because the filename can include color space information)
        filename_tex_set: set[Path] = set()
        directories = filePathEditor(listDirectories="", query=True)

        for directory in directories:
            files = filePathEditor(listFiles=directory, withAttribute=True, query=True)
            for filename, attribute in zip(files[0::2], files[1::2]):
                full_path = os.path.join(directory, filename)
                # Expand tags if any are present
                for expanded_path in self._expand_path(full_path):
                    # get_texture_by_path expects an attribute, not a node
                    if "." in attribute:
                        # add the original texture
                        filename_tex_set.add(expanded_path)
                        try:
                            # Returns a key error if the resource is not in tx manager
                            filename_tex = get_texture_by_path(str(expanded_path), attribute)
                            filename_tex_set.add(Path(filename_tex))
                        except KeyError:
                            pass

        return filename_tex_set

    def _get_tx_files(self) -> set[Path]:
        """
        Searches for both source and tx files for Arnold

        Returns:
            set[Path]: A set of original asset paths and their associated tx files.
        """

        arnold_textures_files: set[Path] = set()
        if not Scene.autotx() and not Scene.use_existing_tiled_textures():
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
        import mtoa.txManager.lib as mtoa  # type: ignore

        return mtoa.get_scanned_files(mtoa.scene_default_texture_scan)

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
