from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from eraplay.translation import TranslationConfig

CONFIG_FILE_NAME = "eraplay.toml"


@dataclass(frozen=True)
class ProjectConfig:
    source_encoding: str | None = None
    translation: TranslationConfig = field(default_factory=TranslationConfig)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ProjectConfig":
        project_data = _table(data, "project")
        translation_data = _table(data, "translation")
        return cls(
            source_encoding=_optional_str(project_data, "source_encoding"),
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
