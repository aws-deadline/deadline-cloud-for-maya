# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
from unittest.mock import MagicMock

# we must mock pymel before importing client code
pymel_modules = ["pymel", "pymel.core", "pymel.util", "mtoa", "mtoa.core"]

for module in pymel_modules:
    sys.modules[module] = MagicMock()
