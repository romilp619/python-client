import re
from typing import Any, TypeVar, get_args

import inflection
from pydantic import ConfigDict, BaseModel

T = TypeVar("T")  # Declare type variable


def to_camel(s: str) -> str:
    s = re.sub("_(url)$", lambda m: f"_{m.group(1).upper()}", s)
    return inflection.camelize(s, uppercase_first_letter=False)


def _allows_none(annotation) -> bool:
    if annotation is None or annotation is type(None) or annotation is Any:
        return True
    return type(None) in get_args(annotation)


class CamelModel(BaseModel):
    def __init__(self, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        # v1 treated an Optional field with no default as None when it was unset or passed as None.
        # v2 requires such fields, so restore the v1 default for required fields that accept None.
        for name, field in type(self).model_fields.items():
            if not field.is_required() or not _allows_none(field.annotation):
                continue
            if name in kwargs or (field.alias is not None and field.alias in kwargs):
                continue
            kwargs[name] = None
        super().__init__(**kwargs)
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, use_enum_values=True)


class GenericCamelModel(CamelModel, BaseModel):
    pass
