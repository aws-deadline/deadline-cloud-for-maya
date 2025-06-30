# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import os
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Generator, Iterable

from .file_path_editor import FilePathEditor
from .scene import Animation, RendererNames, Scene
from .utils import findAllFilesForPattern

_FRAME_RE = re.compile("#+")


class AssetIntrospector:
    def parse_scene_assets(self, progress_callback=None) -> set[Path]:
        """
        Searches the scene for assets, and filters out assets that are not needed for Rendering.

        Args:
            progress_callback: Optional callback function that takes a string argument for progress updates

        Returns:
            set[Path]: A set containing filepaths of assets needed for Rendering
        """
        # clear filesystem cache from last run
        self._expand_path.cache_clear()
        # Grab tx files (if we need to)
        assets: set[Path] = set()

        # Grab any yeti files
        if progress_callback:
            progress_callback("Searching for Yeti cache files...")
        assets.update(self._get_yeti_files(progress_callback))

        if Scene.renderer() == RendererNames.arnold.value:
            if progress_callback:
                progress_callback("Searching for Arnold texture files...")
            assets.update(self._get_tx_files(progress_callback))
        elif Scene.renderer() == RendererNames.renderman.value:
            if progress_callback:
                progress_callback("Searching for Renderman texture files...")
            assets.update(self._get_tex_files(progress_callback))

        file_refs = list(FilePathEditor.fileRefs())
        total_refs = len(file_refs)
        print(f"Processing {total_refs} file references")
        if progress_callback:
            progress_callback(f"Processing {total_refs} file references...")

        for i, ref in enumerate(file_refs):
            normalized_path = os.path.normpath(ref.path)
            # Files without tokens may already have been checked, if so, skip
            if normalized_path in assets:
                continue
            # Files with tokens may have already been checked when grabbing arnold's tx files.
            # Since the expand path returns a generator, it'll actually skip rechecking
            # these files since it returns the original generator which is exhausted.
            for path in self._expand_path(normalized_path):
                assets.add(path)
            # Only refresh UI every 100 elements to improve performance
            if i % 100 == 0:
                print(f"Processed {i+1}/{total_refs} file references at {time.time()}")
                if progress_callback:
                    progress_callback(f"Processed {i+1}/{total_refs} file references...")

        assets.add(Path(Scene.name()))

        if progress_callback:
            progress_callback(f"Found {len(assets)} assets in total")

        return assets

    def _get_yeti_files(self, progress_callback=None) -> set[Path]:
        """
        If Yeti plugin nodes are in the scene, searches for fur cache files

        Args:
            progress_callback: Optional callback function for progress updates

        Returns:
            set[Path]: A set of yeti files
        """
        yeti_files: set[Path] = set()
        cache_files = Scene.yeti_cache_files()
        total_files = len(cache_files)

        if total_files > 0:
            print(f"Processing {total_files} Yeti cache files")
            if progress_callback:
                progress_callback(f"Processing {total_files} Yeti cache files...")

        for i, cache_path in enumerate(cache_files):
            for expanded_path in self._expand_path(cache_path):
                yeti_files.add(expanded_path)

            # For every 100 yeti files, update progress
            if i % 100 == 0 and i > 0:
                print(f"Processed {i}/{total_files} Yeti cache files at {time.time()}")
                if progress_callback:
                    progress_callback(f"Processed {i}/{total_files} Yeti cache files...")

        if total_files > 0:
            print(f"Completed processing all {total_files} Yeti cache files at {time.time()}")
            if progress_callback:
                progress_callback(f"Completed processing all {total_files} Yeti cache files")

        return yeti_files

    def _get_tex_files(self, progress_callback=None) -> set[Path]:
        """
        Searches for Renderman .tex files

        Args:
            progress_callback: Optional callback function for progress updates

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

        total_files = 0
        processed = 0

        # First count total files for better progress reporting
        for directory in directories:
            files = filePathEditor(listFiles=directory, withAttribute=True, query=True)
            total_files += len(files) // 2  # files come in pairs (filename, attribute)

        print(f"Processing {total_files} Renderman texture files")
        if progress_callback:
            progress_callback(f"Processing {total_files} Renderman texture files...")

        for directory in directories:
            files = filePathEditor(listFiles=directory, withAttribute=True, query=True)
            for i, (filename, attribute) in enumerate(zip(files[0::2], files[1::2])):
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

                processed += 1
                # For every 100 texture files, update progress
                if processed % 100 == 0:
                    print(
                        f"Processed {processed}/{total_files} Renderman texture files at {time.time()}"
                    )
                    if progress_callback:
                        progress_callback(
                            f"Processed {processed}/{total_files} Renderman texture files..."
                        )

        # Final count
        if total_files > 0:
            print(
                f"Completed processing all {total_files} Renderman texture files at {time.time()}"
            )
            if progress_callback:
                progress_callback(f"Completed processing all {total_files} Renderman texture files")

        return filename_tex_set

    def _get_tx_files(self, progress_callback=None) -> set[Path]:
        """
        Searches for both source and tx files for Arnold

        Args:
            progress_callback: Optional callback function for progress updates

        Returns:
            set[Path]: A set of original asset paths and their associated tx files.
        """

        arnold_textures_files: set[Path] = set()
        if not Scene.autotx() and not Scene.use_existing_tiled_textures():
            return arnold_textures_files

        texture_files = list(self._get_arnold_texture_files())
        total_textures = len(texture_files)
        print(f"Processing {total_textures} Arnold texture files")
        if progress_callback:
            progress_callback(f"Processing {total_textures} Arnold texture files...")

        for i, img_path in enumerate(texture_files):
            for expanded_path in self._expand_path(img_path):
                arnold_textures_files.add(expanded_path)
                # expanded files are guaranteed to exist, but we haven't checked the associated .tx file yet
                if os.path.isfile(expanded_path.with_suffix(".tx")):
                    arnold_textures_files.add(expanded_path.with_suffix(".tx"))

            # For every 100 texture files, update progress
            if i % 100 == 0 and i > 0:
                print(f"Processed {i}/{total_textures} Arnold texture files at {time.time()}")
                if progress_callback:
                    progress_callback(f"Processed {i}/{total_textures} Arnold texture files...")

        # Final count
        if total_textures > 0:
            print(
                f"Completed processing all {total_textures} Arnold texture files at {time.time()}"
            )
            if progress_callback:
                progress_callback(f"Completed processing all {total_textures} Arnold texture files")

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
