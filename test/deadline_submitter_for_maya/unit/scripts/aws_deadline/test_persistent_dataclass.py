# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import Mock, mock_open, patch

from pytest import raises

import deadline.maya_submitter.persistent_dataclass as persistent_dataclass  # type: ignore
from deadline.maya_submitter.persistent_dataclass import (
    PersistentDataclass,
    PersistentDataclassError,
)


@dataclass
class Concrete(PersistentDataclass):
    cement_type: str
    color: int

    @classmethod
    def instantiate(cls, data: Dict[str, Any]):
        return Concrete(**data)

    @classmethod
    def file_path(cls) -> Path:
        return Path("concrete.json")


class TestPersistentDataClass:
    @patch.object(persistent_dataclass.Path, "is_file", return_value=True)
    @patch("builtins.open", mock_open())
    def test_load_fail_os(self, _mock_is_file: Mock) -> None:
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = OSError()
            with raises(PersistentDataclassError):
                Concrete.load()

    @patch.object(persistent_dataclass.Path, "is_file", return_value=True)
    def test_load_fail_json(self, _mock_is_file: Mock) -> None:
        with patch("builtins.open", mock_open(read_data="}not json{")):
            with raises(PersistentDataclassError):
                Concrete.load()

    @patch.object(persistent_dataclass.Path, "is_file", return_value=True)
    def test_load_happy_path(self, _mock_is_file: Mock) -> None:
        with patch(
            "builtins.open", mock_open(read_data='{"cement_type": "Portland", "color": 16777215}')
        ):
            concrete: Optional[Concrete] = Concrete.load()
            assert concrete is not None
            assert concrete.cement_type == "Portland"
            assert concrete.color == 0xFFFFFF

    @patch.object(persistent_dataclass.Path, "is_file", return_value=True)
    def test_load_missing_field(self, _mock_is_file: Mock) -> None:
        with patch("builtins.open", mock_open(read_data='{"cement_type": "Portland"}')):
            with raises(PersistentDataclassError):
                Concrete.load()

    @patch.object(persistent_dataclass.Path, "is_file", return_value=True)
    def test_load_extra_field(self, _mock_is_file: Mock) -> None:
        with patch(
            "builtins.open",
            mock_open(
                read_data='{"cement_type": "Portland", "color": 16777215, "water_permeable": False}'
            ),
        ):
            with raises(PersistentDataclassError):
                Concrete.load()

    def test_save_fail_os(self) -> None:
        concrete = Concrete(cement_type="Portland", color=0xFFFFFF)
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = OSError()
            with raises(PersistentDataclassError):
                concrete.save()

    def test_save_happy_path(self) -> None:
        concrete = Concrete(cement_type="Portland", color=0xFFFFFF)
        with patch("builtins.open", mock_open()) as mock_file:
            concrete.save()
        handle = mock_file()
        handle.write.assert_called_once_with('{"cement_type": "Portland", "color": 16777215}')
