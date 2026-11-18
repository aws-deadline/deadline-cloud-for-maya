# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Maya startup preference for the software-rendered Linux test desktop."""

from maya import cmds

try:
    from PySide6.QtGui import QSurfaceFormat
except ImportError:
    from PySide2.QtGui import QSurfaceFormat

# Xvfb has no multisampled GLX visuals. Maya's legacy viewport context must
# share Qt's non-multisampled format rather than requesting a missing visual.
surface_format = QSurfaceFormat.defaultFormat()
surface_format.setSamples(0)
QSurfaceFormat.setDefaultFormat(surface_format)
print("Linux GUI test desktop: Qt multisampling disabled")

# These tests inspect and export small scenes, without rendering. Keep Maya's
# worker pool within the same budget as Mesa on the shared CI desktop.
cmds.threadCount(numberOfThreads=2)
print("Linux GUI test desktop: Maya worker threads limited to 2")
