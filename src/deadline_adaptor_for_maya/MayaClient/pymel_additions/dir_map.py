# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Module contain a wrapper around Maya's dirmap command
"""

from itertools import zip_longest as _zip_longest
from typing import Any, Iterable, List, Optional, Tuple

try:
    import pymel.core as _pmc  # pylint: disable=import-error # noqa

    # Leaving this here in case we upstream this
    # import pymel.util as _pm_util  # pylint: disable=import-error
except ModuleNotFoundError:  # pragma: no cover
    raise OSError("Could not find the pymel module. Are you running this inside of MayaPy?")


def _grouper(iterable: Iterable, size: int, fillvalue: Optional[Any] = None) -> Iterable:
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * size
    return _zip_longest(*args, fillvalue=fillvalue)


class DirectoryMappingDict(object):
    """
    Dictionary like object used for accessing and modifying Directory mappings
    """

    def __repr__(self):
        return "%s" % (self.__class__.__name__)

    def __getitem__(self, source: str):
        dest = _pmc.dirmap(getMappedDirectory=source)
        if dest is None:
            raise KeyError(f"KeyError: {source}")
        return dest

    def __setitem__(self, source: str, dest: str):
        return _pmc.dirmap(mapDirectory=(source, dest))

    def __delitem__(self, source: str):
        _pmc.dirmap(unmapDirectory=source),

    def __contains__(self, source: str):
        return _pmc.dirmap(getMappedDirectory=source) is not None

    def items(self) -> List[Tuple[str, str]]:
        """
        Returns a list containing all mapping pairs
        """
        return list(_grouper(_pmc.dirmap(getAllMappings=True), 2))

    def keys(self) -> List[str]:
        """
        Returns a list containing all source paths.
        """
        return _pmc.dirmap(getAllMappings=True)[::2]

    def values(self) -> List[str]:
        """
        Returns a list of all output paths
        """
        return _pmc.dirmap(getAllMappings=True)[1::2]

    def get(self, item, default=None) -> Optional[str]:
        try:
            return self.__getitem__(item)
        except KeyError:
            return default

    def __iter__(self):
        return iter(self.keys())

    has_key = __contains__


# If/when we decide to upstream this we will want to switch this to use the pymel singleton
# Until then we can ignore it since we are just using the classmethods and mocking messes up testing
# class DirectoryMapping(metaclass=_pm_util.Singleton):
class DirectoryMapping:
    mappings = DirectoryMappingDict()

    @classmethod
    def get_activated(self) -> bool:
        return _pmc.dirmap(query=True, enable=True)

    @classmethod
    def set_activated(self, val: bool) -> None:
        _pmc.dirmap(enable=val)

    @classmethod
    def convert(self, val: str) -> str:
        return _pmc.dirmap(convertDirectory=val)
