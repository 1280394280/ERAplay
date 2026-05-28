from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PluginCapability(str, Enum):
    ENGINE_COMMAND = "engine.command"
    ENGINE_FUNCTION = "engine.function"
    ENGINE_DATA_SCHEMA = "engine.data_schema"
    ENGINE_RESOURCE_LOADER = "engine.resource_loader"
    EDITOR_PANEL = "editor.panel"
    EDITOR_COMMAND = "editor.command"
    EDITOR_DIAGNOSTIC = "editor.diagnostic"
    TEMPLATE_PROJECT = "template.project"


class PluginPermission(str, Enum):
    PROJECT_READ = "project.read"
    PROJECT_WRITE = "project.write"
    NETWORK = "network"
    PROCESS = "process"
    NATIVE = "native"


@dataclass(frozen=True)
class PluginManifest:
    id: str
    name: str
    version: str
    entry: str
    capabilities: tuple[PluginCapability, ...] = field(default_factory=tuple)
    permissions: tuple[PluginPermission, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "PluginManifest":
        return cls(
            id=_required_str(data, "id"),
            name=_required_str(data, "name"),
            version=_required_str(data, "version"),
            entry=_required_str(data, "entry"),
            capabilities=tuple(
                PluginCapability(value)
                for value in _optional_str_list(data, "capabilities")
            ),
            permissions=tuple(
                PluginPermission(value)
                for value in _optional_str_list(data, "permissions")
            ),
        )


def _required_str(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"plugin manifest field '{key}' must be a non-empty string")
    return value


def _optional_str_list(data: dict[str, object], key: str) -> list[str]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"plugin manifest field '{key}' must be a string list")
    return value
