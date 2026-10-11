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
    # v1 kept declared fields as ordinary class attributes, so a @staticmethod
    # sharing a field's name stayed reachable on the class. v2's metaclass
    # removes field names from the class namespace and raises AttributeError
    # for anything that is not a private attribute, so the method disappears.
    # Capture the colliding descriptors while the namespace still holds them,
    # and put them back once field processing has finished. The field itself is
    # untouched: it stays in model_fields, and instance access still finds the
    # per-instance value in __dict__ first.
    def __init_subclass__(cls, **kwargs):
        annotations = cls.__dict__.get("__annotations__", {}) or {}
        cls.__field_name_descriptors__ = {
            name: value
            for name, value in cls.__dict__.items()
            if name in annotations and isinstance(value, (staticmethod, classmethod))
        }
        super().__init_subclass__(**kwargs)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs):
        super().__pydantic_init_subclass__(**kwargs)
        for name, descriptor in cls.__dict__.get("__field_name_descriptors__", {}).items():
            setattr(cls, name, descriptor)

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
