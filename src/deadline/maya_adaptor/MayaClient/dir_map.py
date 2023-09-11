# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Module contain a wrapper around Maya's dirmap command
"""

from typing import List, Optional, Tuple

import maya.cmds


class DirectoryMappingDict(object):
    """
    Dictionary like object used for accessing and modifying Directory mappings
    """

    def __repr__(self):
        return "%s" % (self.__class__.__name__)

    def __getitem__(self, source: str):
        dest = maya.cmds.dirmap(getMappedDirectory=source)
        if dest is None:
            raise KeyError(f"KeyError: {source}")
        return dest

    def __setitem__(self, source: str, dest: str):
        maya.cmds.dirmap(mapDirectory=(source, dest))

    def __delitem__(self, source: str):
        maya.cmds.dirmap(unmapDirectory=source)

    def __contains__(self, source: str):
        return maya.cmds.dirmap(getMappedDirectory=source) is not None

    def items(self) -> List[Tuple[str, str]]:
        """
        Returns a list containing all mapping pairs
        """
        all_mappings = maya.cmds.dirmap(getAllMappings=True)
        return list(zip(all_mappings[::2], all_mappings[1::]))

    def keys(self) -> List[str]:
        """
        Returns a list containing all source paths.
        """
        return maya.cmds.dirmap(getAllMappings=True)[::2]

    def values(self) -> List[str]:
        """
        Returns a list of all output paths
        """
        return maya.cmds.dirmap(getAllMappings=True)[1::2]

    def get(self, item, default=None) -> Optional[str]:
        try:
            return self.__getitem__(item)
        except KeyError:
            return default

    def __iter__(self):
        return iter(self.keys())

    has_key = __contains__


class DirectoryMapping:
    mappings = DirectoryMappingDict()

    @classmethod
    def get_activated(self) -> bool:
        return maya.cmds.dirmap(query=True, enable=True)

    @classmethod
    def set_activated(self, val: bool) -> None:
        maya.cmds.dirmap(enable=val)

    @classmethod
    def convert(self, val: str) -> str:
        return maya.cmds.dirmap(convertDirectory=val)
