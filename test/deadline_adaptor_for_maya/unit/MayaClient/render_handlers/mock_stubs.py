# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from typing import Any


class MockProperty:
    """Mock pymel property"""

    def __init__(self, value: Any):
        self.value = value

    def get(self):
        return self.value


class MockCamera:
    """
    Mock Camera class which imitates the Camera type in pymel
    """

    name: str
    renderable: MockProperty

    def __init__(self, name: str, renderable: bool = True):
        self.name = name
        self.renderable = MockProperty(renderable)

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return self.name == str(other)

    def getParent(self) -> "MockCamera":
        """
        Pymel Cameras have a parent which excludes the `Shape` in the name.
        e.g. perspShape's parent is a transform named persp.
        """
        return MockCamera(self.name.replace("Shape", ""), False)
