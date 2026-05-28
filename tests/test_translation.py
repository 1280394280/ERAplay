from eraplay.translation import (
    TranslationConfig,
    TranslationDisplayMode,
    TranslationProvider,
    render_translated_text,
)
from eraplay.ui import OutputChannel, OutputEvent, OutputKind


def test_translation_config_from_dict() -> None:
    config = TranslationConfig.from_dict(
        {
            "enabled": True,
            "source_language": "ja",
            "target_language": "zh-Hans",
            "provider": "openai-compatible",
            "endpoint": "https://api.example.com/v1/chat/completions",
            "model": "translation-model",
            "api_key_env": "ERAPLAY_TRANSLATION_API_KEY",
            "translate_channels": ["info", "main"],
        }
    )

    assert config.enabled is True
    assert config.provider is TranslationProvider.OPENAI_COMPATIBLE
    assert config.translate_channels == (OutputChannel.INFO, OutputChannel.MAIN)


def test_should_translate_configured_channels() -> None:
    config = TranslationConfig.from_dict(
        {"enabled": True, "translate_channels": ["main"]}
    )

    main_event = OutputEvent(OutputChannel.MAIN, OutputKind.LINE, "\u901a\u5e38\u696d\u52d9")
    debug_event = OutputEvent(OutputChannel.DEBUG, OutputKind.LINE, "trace")

    assert config.should_translate(main_event) is True
    assert config.should_translate(debug_event) is False


def test_render_bilingual_text() -> None:
    rendered = render_translated_text(
        "\u901a\u5e38\u696d\u52d9",
        "\u666e\u901a\u4e1a\u52a1",
        TranslationDisplayMode.BILINGUAL,
    )

    assert rendered == "\u901a\u5e38\u696d\u52d9\n\u666e\u901a\u4e1a\u52a1"
