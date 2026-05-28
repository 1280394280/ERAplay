from pathlib import Path

from eraplay.config import ProjectConfig, default_config_text, init_project_config, load_project_config
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


def test_default_config_text_contains_encoding() -> None:
    text = default_config_text("cp950")

    assert 'source_encoding = "cp950"' in text
    assert "[translation]" in text


def test_init_project_config_writes_file(tmp_path: Path) -> None:
    path = init_project_config(tmp_path, source_encoding="cp932")

    assert path.name == "eraplay.toml"
    assert load_project_config(tmp_path).source_encoding == "cp932"


def test_init_project_config_refuses_overwrite(tmp_path: Path) -> None:
    init_project_config(tmp_path)

    try:
        init_project_config(tmp_path)
    except FileExistsError:
        pass
    else:
        raise AssertionError("expected FileExistsError")
