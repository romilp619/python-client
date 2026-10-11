import re
from types import UnionType
from typing import Annotated, Any, TypeVar, Union, get_args, get_origin

import inflection
from pydantic import ConfigDict, BaseModel

T = TypeVar("T")  # Declare type variable


def to_camel(s: str) -> str:
    s = re.sub("_(url)$", lambda m: f"_{m.group(1).upper()}", s)
    return inflection.camelize(s, uppercase_first_letter=False)


def _admits_none(annotation) -> bool:
    """Return True if a field annotation accepts None (Optional[X], Union[..., None], Any)."""
    if annotation is None or annotation is type(None) or annotation is Any:
        return True
    origin = get_origin(annotation)
    if origin is Annotated:
        args = get_args(annotation)
        return bool(args) and _admits_none(args[0])
    if origin is Union or origin is UnionType:
        return any(_admits_none(arg) for arg in get_args(annotation))
    return False


class CamelModel(BaseModel):
    def __init__(self, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        # v1 behaviour: Optional[X] fields without a default were optional (defaulting to None).
        # Restore that here so callers that omit them keep working.
        for name, field_info in type(self).model_fields.items():
            if not field_info.is_required():
                continue
            if not _admits_none(field_info.annotation):
                continue
            alias = field_info.alias
            if name in kwargs or (alias is not None and alias in kwargs):
                continue
            kwargs[name] = None
        super().__init__(**kwargs)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, use_enum_values=True)


class GenericCamelModel(CamelModel, BaseModel):
    pass
