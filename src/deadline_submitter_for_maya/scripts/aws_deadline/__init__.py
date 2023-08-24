# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Top level packages for the Deadline Integrated Submitter
"""
from .logging import get_logger
from .scene import Animation, Scene

__all__ = ["logger", "config", "shelf", "Animation", "Scene"]

__log__ = get_logger("Deadline")


def logger():
    """
    Returns an instance of the global Deadline Logger.
    """
    return __log__
