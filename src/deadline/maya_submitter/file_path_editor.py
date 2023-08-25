# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import os

from dataclasses import dataclass
from distutils.util import strtobool
from typing import Optional

import maya.cmds

"""
Module contain a wrapper around Maya's filepatheditor mel command
"""


@dataclass
class FileRef:
    """
    Dataclass containing a reference to a single referenced File.
    """

    path: str
    exists: bool


class FilePathEditor:
    """
    Python wrapper for Maya's filePathEditor command
    """

    @classmethod
    def dirs(cls) -> list[str]:
        """
        Returns a list of directories that contain referenced files
        """
        maya.cmds.filePathEditor(refresh=True)
        return maya.cmds.filePathEditor(query=True, listDirectories="") or []

    @classmethod
    def fileRefs(cls, directories: Optional[list[str]] = None) -> list[FileRef]:
        """
        Returns a list of file references via Maya's file path editor
        """
        maya.cmds.filePathEditor(refresh=True)

        if directories is None:
            directories = cls.dirs()

        refs = []
        for directory in directories:
            # File path editor returns an array of repeated blocks of [path, attribute_name, exists]
            cmd_results: list[str] = maya.cmds.filePathEditor(
                query=True, withAttribute=True, status=True, listFiles=directory
            )

            # if pm_cmd.filePathEditor finds no references it returns None, not an empty array
            if cmd_results is None:
                continue

            filename: str
            attr: str
            exists: str
            for filename, attr, exists in zip(
                cmd_results[0::3], cmd_results[1::3], cmd_results[2::3]
            ):
                pattern_attr = attr.replace("fileTextureName", "computedFileTextureNamePattern")
                if attr != pattern_attr and maya.cmds.getAttr(attr) != maya.cmds.getAttr(
                    pattern_attr
                ):
                    # If the value for the computedFileTextureNamePattern attr is not equal to the
                    # fileTextureName attr, then this was only the first file of a multi-tiled UV
                    # texture or animated texture. We will append the path with the pattern instead
                    # so that all texture files can be resolved later.
                    attr = pattern_attr
                    filename = maya.cmds.getAttr(pattern_attr)  # This is a full path

                refs.append(
                    FileRef(
                        os.path.join(directory, filename),
                        bool(strtobool(exists)),
                    )
                )
        return refs
