from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from eraplay.ui import OutputChannel, OutputEvent


class TranslationProvider(str, Enum):
    NONE = "none"
    LOCAL_DICT = "local-dict"
    OPENAI_COMPATIBLE = "openai-compatible"
    CUSTOM_HTTP = "custom-http"
    PLUGIN = "plugin"


class TranslationDisplayMode(str, Enum):
    ORIGINAL = "original"
    TRANSLATED = "translated"
    BILINGUAL = "bilingual"


DEFAULT_TRANSLATED_CHANNELS = (
    OutputChannel.INFO,
    OutputChannel.MAIN,
    OutputChannel.ACTIONS,
)


@dataclass(frozen=True)
class TranslationConfig:
    enabled: bool = False
    source_language: str = "auto"
    target_language: str = "zh-Hans"
    provider: TranslationProvider = TranslationProvider.NONE
    endpoint: str | None = None
    model: str | None = None
    api_key_env: str | None = None
    cache: bool = True
    display_mode: TranslationDisplayMode = TranslationDisplayMode.TRANSLATED
    translate_channels: tuple[OutputChannel, ...] = field(
        default_factory=lambda: DEFAULT_TRANSLATED_CHANNELS
    )

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "TranslationConfig":
        return cls(
            enabled=bool(data.get("enabled", False)),
            source_language=_str_value(data, "source_language", "auto"),
            target_language=_str_value(data, "target_language", "zh-Hans"),
            provider=TranslationProvider(_str_value(data, "provider", "none")),
            endpoint=_optional_str(data, "endpoint"),
            model=_optional_str(data, "model"),
            api_key_env=_optional_str(data, "api_key_env"),
            cache=bool(data.get("cache", True)),
            display_mode=TranslationDisplayMode(
                _str_value(data, "display_mode", "translated")
            ),
            translate_channels=tuple(
                OutputChannel(value)
                for value in _optional_str_list(
                    data,
                    "translate_channels",
                    [channel.value for channel in DEFAULT_TRANSLATED_CHANNELS],
                )
            ),
        )

    def should_translate(self, event: OutputEvent) -> bool:
        return self.enabled and event.channel in self.translate_channels and bool(event.text)


def render_translated_text(
    original: str,
    translated: str,
    mode: TranslationDisplayMode,
) -> str:
    if mode is TranslationDisplayMode.ORIGINAL:
        return original
    if mode is TranslationDisplayMode.BILINGUAL:
        if original == translated:
            return original
        return f"{original}\n{translated}"
    return translated


LOCAL_TRANSLATIONS = {
    "ERAplay demo": "ERAplay 演示",
    "通常業務": "普通业务",
    "診察": "诊察",
    "通常業務を選択しました。": "已选择普通业务。",
    "診察を選択しました。": "已选择诊察。",
    "未対応の選択です。": "未支持的选择。",
    "[1] 通常業務": "[1] 普通业务",
    "[2] 診察": "[2] 诊察",
}


def translate_text(text: str, config: TranslationConfig) -> str:
    if not config.enabled:
        return text
    if config.provider is TranslationProvider.LOCAL_DICT:
        translated = LOCAL_TRANSLATIONS.get(text, text)
        return render_translated_text(text, translated, config.display_mode)
    return text


def translate_event_text(event: OutputEvent, config: TranslationConfig) -> str:
    if not config.should_translate(event):
        return event.text
    return translate_text(event.text, config)


def _str_value(data: dict[str, object], key: str, default: str) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ValueError(f"translation config field '{key}' must be a string")
    return value


def _optional_str(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"translation config field '{key}' must be a string")
    return value


def _optional_str_list(
    data: dict[str, object],
    key: str,
    default: list[str],
) -> list[str]:
    value = data.get(key, default)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"translation config field '{key}' must be a string list")
    return value
