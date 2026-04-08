# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import maya.cmds


def get_width() -> int:
    """
    Retrieves the width as currently specified
    """
    return maya.cmds.getAttr("defaultResolution.width")


def get_height() -> int:
    """
    Retrieves the height as currently specified.
    """
    return maya.cmds.getAttr("defaultResolution.height")


def get_base_output_prefix() -> str:
    """
    Retrieves the output prefix as specified in the scene.
    """
    prefix: str = maya.cmds.getAttr("defaultRenderGlobals.imageFilePrefix") or ""
    if prefix:
        return prefix
    return "<Scene>"


def get_output_prefix_with_tokens() -> str:
    """
    Retrieves the output prefix as specified in the scene.
    WYSIWYG — returns the prefix exactly as set, no auto-prepend of tokens.
    """
    return get_base_output_prefix()
