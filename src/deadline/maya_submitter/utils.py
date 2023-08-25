# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Minor utility functions
"""
from __future__ import annotations

import os
import re
import time
from functools import wraps
from typing import Callable

from maya.app.general.fileTexturePathResolver import _patternToRegex


def join_paths(first: str, *remainder: str) -> str:
    """
    Wrapper for os.path.join which replaces all backslashes (maya only uses forward slashes.)
    """
    return os.path.join(first, *remainder).replace("\\", "/")


def timed_func(func: Callable):
    """Decorator that wraps a function gives performance timing"""

    @wraps(func)
    def wrapped(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        elapsed = end - start
        print(
            f"func: {func.__name__} with args: {args}, kwargs: {kwargs}, took {elapsed:.3f} seconds"
        )
        return result

    return wrapped


def findAllFilesForPattern(pattern: str, frameNumber: int) -> list[str]:
    """
    As of Maya 2023, a replacement for maya.app.general.fileTexturePathResolver.findAllFilesForPattern

    This is a faster version of the function provided by Maya, since it
    only does the file existence check after it verifies the regex matches.

    We've also removed a _split_path function call that found the result of os.path.split and
    the original path separator between directory and filename. We don't care about the
    original path separator since we immediately turn this into Path objects. We do not
    return a list of Paths here so that we can keep the same interface as the original
    function.

    Original Doc string:
            Given a path, possibly containing tags in the file name, find all files in
            the same directory that match the tags. If none found, just return pattern
            that we looked for.
    """
    dirname, basename = os.path.split(pattern)
    result: list[str] = []
    # Have to keep this existence check since listdir will error out if the dir doesn't exist
    if dirname and basename and os.path.isdir(dirname):
        if frameNumber is not None:
            # _patternToRegex handles frame tokens, but this is for only finding files for a specific frame
            basename = basename.replace("<f>", "0*" + str(frameNumber))
        regex = _patternToRegex(basename)
        result = [
            os.path.join(dirname, f)
            for f in os.listdir(dirname)
            if re.match(regex, f, flags=re.IGNORECASE) and os.path.isfile(os.path.join(dirname, f))
        ]

    return result
