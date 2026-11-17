# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Maya startup preference for the software-rendered Linux test desktop."""

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
