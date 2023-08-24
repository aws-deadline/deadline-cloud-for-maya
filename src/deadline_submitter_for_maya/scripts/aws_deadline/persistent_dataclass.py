# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import dataclasses
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


class PersistentDataclassError(Exception):
    """
    Exception raise when saving or loading persistent settings fails.
    """


@dataclass
class PersistentDataclass(ABC):
    @classmethod
    @abstractmethod
    def file_path(cls) -> Path:
        pass

    @classmethod
    @abstractmethod
    def instantiate(cls, data: Dict[str, Any]):
        pass

    @classmethod
    def default(cls):
        return cls.instantiate(dict())

    def to_json_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    def save(self) -> None:
        try:
            with open(self.file_path(), "w", encoding="utf8") as out_file:
                out_file.write(json.dumps(self.to_json_dict()))
        except OSError as exc:
            raise PersistentDataclassError("Failed to write settings file") from exc

    @classmethod
    def from_json_dict(cls, json_dict: Dict[str, Any]):
        return cls.instantiate(json_dict)

    @classmethod
    def from_json(cls, json_str: str):
        json_dict: Dict[str, Any] = json.loads(json_str)
        return cls.from_json_dict(json_dict)

    @classmethod
    def load(cls) -> Optional[Any]:
        if cls.file_path().is_file():
            try:
                with open(cls.file_path(), "r", encoding="utf8") as in_file:
                    contents: str = in_file.read()
                return cls.from_json(contents)
            except OSError as exc:
                raise PersistentDataclassError("Failed to read from settings file") from exc
            except json.JSONDecodeError as exc:
                raise PersistentDataclassError("Failed to parse JSON from settings file") from exc
            except TypeError as exc:
                raise PersistentDataclassError("Failed to deserialize settings data") from exc
        else:
            return None
