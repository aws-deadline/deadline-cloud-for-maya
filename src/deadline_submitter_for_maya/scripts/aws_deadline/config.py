# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
A module that contains the configuration and settings for Amazon Deadline Cloud's submitter dialog.
"""
import os

__all__ = [
    "root_dir",
    "config_dir",
    "icons_dir",
]


def _root_directory():
    """
    Returns the path to the base directory from which this plugin is run.
    """
    import inspect

    try:
        this_file_path = __file__
    except NameError:
        # inside an interpreter, we can use the stack to find the file
        # path.
        this_file_path = os.path.abspath(inspect.stack()[0][1])
    return os.path.dirname(os.path.dirname(os.path.dirname(this_file_path)))


root_dir = _root_directory()
config_dir = os.path.join(root_dir, "config")
icons_dir = os.path.join(root_dir, "icons")
