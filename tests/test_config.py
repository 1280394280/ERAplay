from pathlib import Path

from eraplay.config import ProjectConfig, load_project_config
from eraplay.translation import TranslationDisplayMode
from eraplay.ui import OutputChannel


def test_project_config_from_dict() -> None:
    config = ProjectConfig.from_dict(
        {
            "project": {"source_encoding": "cp950"},
            "translation": {
                "enabled": True,
                "source_language": "ja",
                "target_language": "zh-Hans",
                "display_mode": "bilingual",
                "translate_channels": ["main", "actions"],
            },
        }
    )

    assert config.source_encoding == "cp950"
    assert config.translation.enabled is True
    assert config.translation.display_mode is TranslationDisplayMode.BILINGUAL
    assert config.translation.translate_channels == (
        OutputChannel.MAIN,
        OutputChannel.ACTIONS,
    )


def test_load_missing_project_config_returns_defaults(tmp_path: Path) -> None:
    config = load_project_config(tmp_path)

    assert config.source_encoding is None
    assert config.translation.enabled is False


def test_load_project_config_file(tmp_path: Path) -> None:
    (tmp_path / "eraplay.toml").write_text(
        "[project]\nsource_encoding = \"cp932\"\n",
        encoding="utf-8",
    )

    config = load_project_config(tmp_path)

    assert config.source_encoding == "cp932"
