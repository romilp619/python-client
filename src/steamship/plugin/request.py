from __future__ import annotations

from typing import Generic, Optional, TypeVar

# Note!
# =====
#
# This the files in this package are for Plugin Implementors.
# If you are using the Steamship Client, you probably are looking for either steamship.client or steamship.data
#
from steamship.base import Task
from steamship.base.model import CamelModel, to_camel
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")
U = TypeVar("U")


class PluginRequestContext(CamelModel):
    """Contains the context in which"""

    plugin_id: str = None
    plugin_handle: str = None
    plugin_version_id: str = None
    plugin_version_handle: str = None
    plugin_instance_id: str = None
    plugin_instance_handle: str = None


class PluginRequest(BaseModel, Generic[T]):
    # The primary payload of the request. E.g. RawDataPluginInput, BlockAndTagPluginInput
    data: Optional[T] = None

    # The context in which this request is occurring
    context: Optional[PluginRequestContext] = None

    # The status of the request as perceived by the requester.
    status: Optional[Task] = None

    # Whether this plugin request is a status check against ongoing work. If True, status must be not None
    is_status_check: bool = False
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
