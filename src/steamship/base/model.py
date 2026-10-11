import re
import types
import typing
from typing import Any, TypeVar, Union

import inflection
from pydantic import ConfigDict, BaseModel

T = TypeVar("T")  # Declare type variable


def to_camel(s: str) -> str:
    s = re.sub("_(url)$", lambda m: f"_{m.group(1).upper()}", s)
    return inflection.camelize(s, uppercase_first_letter=False)


def _admits_none(annotation) -> bool:
    """Return True if a field annotation accepts None (v1 implicit-optional semantics)."""
    if annotation is None or annotation is type(None) or annotation is Any:
        return True
    origin = typing.get_origin(annotation)
    if origin is typing.Annotated:
        args = typing.get_args(annotation)
        return bool(args) and _admits_none(args[0])
    union_type = getattr(types, "UnionType", None)
    if origin is Union or (union_type is not None and origin is union_type):
        return any(_admits_none(arg) for arg in typing.get_args(annotation))
    return False


class CamelModel(BaseModel):
    def __init__(self, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        # v1 treated Optional[X] fields without a default as optional (default None).
        # v2 makes them required, so restore the v1 default for those fields.
        for name, field in type(self).model_fields.items():
            if not field.is_required() or not _admits_none(field.annotation):
                continue
            alias = field.alias or name
            if name in kwargs or alias in kwargs:
                continue
            kwargs[name] = None
        super().__init__(**kwargs)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, use_enum_values=True)


class GenericCamelModel(CamelModel, BaseModel):
    pass
