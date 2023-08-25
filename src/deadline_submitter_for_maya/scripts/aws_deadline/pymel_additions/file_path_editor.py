# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Module contain a wrapper around Maya's filepatheditor mel command
"""

from dataclasses import dataclass as _dataclass
from distutils.util import strtobool as _strtobool
from itertools import zip_longest as _zip_longest
from typing import Any, Iterable, List, Optional

import pymel.core as _pmc  # pylint: disable=import-error
import pymel.internal.pmcmds as _pm_cmd  # pylint: disable=import-error
import pymel.util as _pm_util  # pylint: disable=import-error
from pymel.core.general import Attribute as _pm_attr  # pylint: disable=import-error
from pymel.core.nodetypes import Reference as _pm_ref  # pylint: disable=import-error


# Taken from https://docs.python.org/3.7/library/itertools.html
def _grouper(iterable: Iterable, size: int, fillvalue: Optional[Any] = None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * size
    return _zip_longest(*args, fillvalue=fillvalue)


@_dataclass
class FileRef:
    """
    Dataclass containing a reference to a single referenced File.
    """

    path: _pmc.Path
    exists: bool
    attribute: Optional[_pm_attr] = None
    reference: Optional[_pm_ref] = None


class FilePathEditor(metaclass=_pm_util.Singleton):
    """
    Python wrapper for Maya's filePathEditor command
    """

    @classmethod
    def dirs(cls) -> "List[_pmc.Path]":
        """
        Returns a list of directories that contain referenced files
        """
        cls.refresh()
        raw_dirs = _pm_cmd.filePathEditor(query=True, listDirectories="")

        # If no directories then _pm_cmd.filePathEditor returns None instead of an empty array
        if raw_dirs is None:
            return []

        return [_pmc.Path(dir) for dir in raw_dirs]

    @classmethod
    def fileRefs(cls, directories: Optional[List[str]] = None) -> List[FileRef]:
        """
        Returns a list of file references via Maya's file path editor
        """
        cls.refresh()

        if directories is None:
            directories = cls.dirs()

        refs = []
        for directory in directories:
            # File path editor returns an array of repeated blocks of [path, attribute_name, exists]
            cmd_results: List[str] = _pm_cmd.filePathEditor(
                query=True, withAttribute=True, status=True, listFiles=directory
            )

            # if _pm_cmd.filePathEditor finds no references it returns None, not an empty array
            if cmd_results is None:
                continue

            filename: str
            attr: str
            exists: str
            for filename, attr, exists in _grouper(cmd_results, 3):
                filename_pattern = ""
                pattern_attr = attr.replace("fileTextureName", "computedFileTextureNamePattern")
                if attr != pattern_attr and _pmc.getAttr(attr) != _pmc.getAttr(pattern_attr):
                    # If the value for the computedFileTextureNamePattern attr is not equal to the
                    # fileTextureName attr, then this was only the first file of a multi-tiled UV
                    # texture or animated texture. We will append the path with the pattern instead
                    # so that all texture files can be resolved later.
                    attr = pattern_attr
                    filename_pattern = _pmc.getAttr(pattern_attr)  # This is a full path
                node = _pmc.PyNode(attr)

                refs.append(
                    FileRef(
                        _pmc.Path(filename_pattern) or _pmc.Path(directory) / _pmc.Path(filename),
                        bool(_strtobool(exists)),
                        attribute=node if isinstance(node, _pm_attr) else None,
                        reference=node if isinstance(node, _pm_ref) else None,
                    )
                )
        return refs

    @classmethod
    def refresh(cls):
        """
        Refreshes maya's filePathEditor to ensure it has all of the current references.
        """
        _pm_cmd.filePathEditor(refresh=True)
