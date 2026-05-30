from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from eraplay.translation import TranslationConfig

CONFIG_FILE_NAME = "eraplay.toml"
DEFAULT_EXCLUDE_DIRS = (
    ".git",
    "__pycache__",
    "sav",
    "save",
    "debug",
    "resources",
    "\u8cc7\u6599",
    "\u9644\u4ef6",
    "HO\u7248\u8cc7\u6599\uff08\u4f5c\u6210\u4e2d\u9014\uff09",
)
DEFAULT_EXTERNAL_CALLS: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProjectConfig:
    source_encoding: str | None = None
    exclude_dirs: tuple[str, ...] = DEFAULT_EXCLUDE_DIRS
    external_calls: tuple[str, ...] = DEFAULT_EXTERNAL_CALLS
    translation: TranslationConfig = field(default_factory=TranslationConfig)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ProjectConfig":
        project_data = _table(data, "project")
        translation_data = _table(data, "translation")
        return cls(
            source_encoding=_optional_str(project_data, "source_encoding"),
            exclude_dirs=_optional_str_tuple(project_data, "exclude_dirs", DEFAULT_EXCLUDE_DIRS),
            external_calls=_optional_str_tuple(
                project_data,
                "external_calls",
                DEFAULT_EXTERNAL_CALLS,
            ),
            translation=TranslationConfig.from_dict(translation_data),
        )


def load_project_config(root: str | Path) -> ProjectConfig:
    path = Path(root) / CONFIG_FILE_NAME
    if not path.exists():
        return ProjectConfig()
    with path.open("rb") as file:
        return ProjectConfig.from_dict(tomllib.load(file))


def default_config_text(source_encoding: str = "utf-8") -> str:
    return f"""[project]
source_encoding = "{source_encoding}"
exclude_dirs = [".git", "__pycache__", "sav", "save", "debug", "resources", "資料", "附件", "HO版資料（作成中途）"]
external_calls = []

[translation]
enabled = false
source_language = "auto"
target_language = "zh-Hans"
provider = "none"
display_mode = "translated"
translate_channels = ["info", "main", "actions"]
"""


def init_project_config(
    root: str | Path,
    source_encoding: str = "utf-8",
    overwrite: bool = False,
) -> Path:
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    path = root_path / CONFIG_FILE_NAME
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    path.write_text(default_config_text(source_encoding), encoding="utf-8")
    return path


def _table(data: dict[str, object], key: str) -> dict[str, object]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"config section '{key}' must be a table")
    return value


def _optional_str(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"config field '{key}' must be a non-empty string")
    return value


def _optional_str_tuple(
    data: dict[str, object],
    key: str,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    value = data.get(key)
    if value is None:
        return default
    if not isinstance(value, list):
        raise ValueError(f"config field '{key}' must be a list of strings")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"config field '{key}' must be a list of non-empty strings")
        result.append(item)
    return tuple(result)
