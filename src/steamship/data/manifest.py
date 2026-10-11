import json
from enum import Enum
from typing import Dict, List, Optional, Type, Union

from pydantic import BaseModel, StrictBool, StrictFloat, StrictInt, StrictStr

from steamship.base.error import SteamshipError


class ConfigParameterType(str, Enum):
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"

    @staticmethod
    def from_python_type(t: Type):
        if issubclass(t, str):
            return ConfigParameterType.STRING
        elif issubclass(t, bool):  # bool is a subclass of int, so must do this first!
            return ConfigParameterType.BOOLEAN
        elif issubclass(t, float) or issubclass(t, int):
            return ConfigParameterType.NUMBER
        else:
            raise SteamshipError(f"Unknown value type in Config: {t}")


class ConfigParameter(BaseModel):
    type: ConfigParameterType
    description: Optional[str] = None
    # optional: Optional[bool] = None

    # Use strict so that Pydantic doesn't coerce values into the first one that fits
    default: Optional[Union[StrictStr, StrictBool, StrictFloat, StrictInt]] = None


class DeployableType(str, Enum):
    PLUGIN = "plugin"
    PACKAGE = "package"


class SteamshipRegistry(BaseModel):
    tagline: Optional[str] = None  # noqa: N815
    tagline2: Optional[str] = None  # noqa: N815
    usefulFor: Optional[str] = None  # noqa: N815
    videoUrl: Optional[str] = None  # noqa: N815
    githubUrl: Optional[str] = None  # noqa: N815
    demoUrl: Optional[str] = None  # noqa: N815
    blogUrl: Optional[str] = None  # noqa: N815
    jupyterUrl: Optional[str] = None  # noqa: N815
    authorGithub: Optional[str] = None  # noqa: N815
    authorName: Optional[str] = None  # noqa: N815
    authorEmail: Optional[str] = None  # noqa: N815
    authorTwitter: Optional[str] = None  # noqa: N815
    authorUrl: Optional[str] = None  # noqa: N815
    tags: List[str]


class PluginConfig(BaseModel):
    isTrainable: Optional[bool] = False  # noqa: N815
    transport: str = "jsonOverHttp"
    type: str  # Does not use PluginType due to circular import
    streaming: bool = False


class Manifest(BaseModel):
    type: DeployableType
    handle: str
    version: str
    description: Optional[str] = None
    author: Optional[str] = None
    entrypoint: str = "Unused"
    public: bool
    plugin: Optional[PluginConfig] = None
    build_config: Dict[str, List[str]] = {"ignore": []}
    configTemplate: Optional[Dict[str, ConfigParameter]] = None  # noqa: N815
    steamshipRegistry: SteamshipRegistry  # noqa: N815

    @staticmethod
    def load_manifest() -> "Manifest":
        return Manifest.parse_file("steamship.json", content_type="application/json")

    def save(self):
        with open("steamship.json", "w") as file:
            json.dump(self.dict(), file, indent="\t")

    def config_template_as_dict(self):
        result = {}
        for param, spec in self.configTemplate.items():
            result[param] = {k: v for k, v in spec.dict().items() if v is not None}

        return result
