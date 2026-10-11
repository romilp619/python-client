import json
import types
import typing
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Union

from pydantic_core import PydanticUndefined

from steamship.base.error import SteamshipError
from steamship.base.model import CamelModel
from steamship.data.manifest import ConfigParameter, ConfigParameterType

_UnionType = getattr(types, "UnionType", None)


def _v1_field_type(annotation: Any) -> Any:
    """Approximate the v1 `ModelField.type_`: strip Optional and take the inner type of simple containers."""
    origin = typing.get_origin(annotation)
    if origin is Union or (_UnionType is not None and origin is _UnionType):
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            annotation = args[0]
            origin = typing.get_origin(annotation)

    if origin in (list, set, frozenset):
        args = typing.get_args(annotation)
        if args:
            return args[0]
    elif origin is dict:
        args = typing.get_args(annotation)
        if len(args) == 2:
            return args[1]
    return annotation


class Config(CamelModel):
    """Base class Steamship Package and Plugin configuration objects."""

    def __init__(self, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        super().__init__(**kwargs)

    def extend_with_dict(self, d: dict, overwrite: bool = False):
        """Sets the attributes on this object with provided keys and values."""
        for key, val in (d or {}).items():
            if hasattr(self, key) and (overwrite or getattr(self, key) is None):
                setattr(self, key, val)

    def extend_with_json_file(
        self, path: Path, overwrite: bool = False, fail_on_missing_file: bool = True
    ):
        """Extends this config object's values with a JSON file from disk.

        This is useful for applying late-bound defaults, such as API keys added to a deployment bundle."""
        if not path.exists():
            if fail_on_missing_file:
                raise SteamshipError(
                    message=f"Attempted to extend Config object with {path}, but the file was not found."
                )
            return

        with open(path) as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise SteamshipError(
                    message=f"Attempted to extend Config object with {path}, but the file did not contain a JSON `dict` object."
                )
            self.extend_with_dict(data, overwrite)

    @staticmethod
    def strip_enum(default_value):
        if issubclass(type(default_value), Enum):
            return default_value.value
        else:
            return default_value

    @classmethod
    def get_config_parameters(cls) -> Dict[str, ConfigParameter]:
        result = {}
        for field_name, field in cls.model_fields.items():
            description = field.description
            type_ = ConfigParameterType.from_python_type(_v1_field_type(field.annotation))

            # v2 uses PydanticUndefined for "no default"; v1 reported None in that case.
            raw_default = field.default
            if raw_default is PydanticUndefined:
                raw_default = None
            default_ = cls.strip_enum(raw_default)

            # Note: Pydantic treats any field with a default value as being `required == False`, which is not strictly
            # the same thing as being optional. Below we use "required is False and allow_none is True" so that
            # user interface generation code has access to BOTH the status of a default value and also
            # the notion of whether the absense of a value will truly be treated as absence.
            # That way it can provide hints to the user to minimize surprise about how their inputs will be interpreted.

            # optional_ = field.is_required() is False and <annotation admits None>

            result[field_name] = ConfigParameter(
                type=type_,
                default=default_,
                description=description,  # optional=optional_
            )

        return result
