import json
import types
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Union, get_args, get_origin

from steamship.base.error import SteamshipError
from steamship.base.model import CamelModel
from steamship.data.manifest import ConfigParameter, ConfigParameterType

_UnionType = getattr(types, "UnionType", None)


def _is_union(annotation) -> bool:
    origin = get_origin(annotation)
    return origin is Union or (_UnionType is not None and origin is _UnionType)


def _admits_none(annotation) -> bool:
    """Returns True if a field annotation accepts None (v1 implicit-optional semantics)."""
    if annotation is None or annotation is type(None) or annotation is Any:
        return True
    if _is_union(annotation):
        return type(None) in get_args(annotation)
    return False


def _strip_optional(annotation):
    """Returns the inner type of Optional[X] (v1 `type_` behaviour), otherwise the annotation itself."""
    if _is_union(annotation):
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


class Config(CamelModel):
    """Base class Steamship Package and Plugin configuration objects."""

    def __init__(self, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        # v1 treated Optional[X] fields without a default as optional (default None).
        # v2 makes them required, so restore the v1 default before validation.
        for name, field in type(self).model_fields.items():
            if field.is_required() and _admits_none(field.annotation):
                key = field.alias or name
                if key not in kwargs and name not in kwargs:
                    kwargs[key] = None
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
            type_ = ConfigParameterType.from_python_type(_strip_optional(field.annotation))
            # v1 reported None for fields without a default (and for default_factory fields).
            if field.is_required() or field.default_factory is not None:
                default_source = None
            else:
                default_source = field.default
            default_ = cls.strip_enum(default_source)

            # Note: Pydantic treats any field with a default value as being `required == False`, which is not strictly
            # the same thing as being optional. Below we use "required is False and allow_none is True" so that
            # user interface generation code has access to BOTH the status of a default value and also
            # the notion of whether the absense of a value will truly be treated as absence.
            # That way it can provide hints to the user to minimize surprise about how their inputs will be interpreted.

            # optional_ = field.required is False and field.allow_none is True

            result[field_name] = ConfigParameter(
                type=type_,
                default=default_,
                description=description,  # optional=optional_
            )

        return result
