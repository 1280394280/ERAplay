# Display Translation

ERAplay should support optional translation for displayed text. Translation must
be a rendering-layer feature, not a source-rewriting feature.

## Core Rule

Never mutate original ERB, ERH, CSV, save data, or runtime string values just
because display translation is enabled.

The source language text remains the canonical game state. Translation happens
after runtime output events are produced and before the UI renders them.

```text
ERB runtime
  |
  v
OutputEvent(text="通常業務")
  |
  v
translation layer
  |
  v
Rendered text: "普通业务"
```

## Why Display-Layer Translation

ERA games often use displayed strings as part of formatting, menus, or debugging.
Changing source files or runtime strings can break:

- menu command alignment,
- save compatibility,
- string comparisons,
- macro expansion,
- user patches,
- mixed Japanese/Traditional Chinese projects.

Display translation keeps compatibility safer.

## Configuration Goals

Project or user config should be able to define:

- enabled or disabled,
- source language,
- target language,
- provider,
- API endpoint,
- model name,
- API key environment variable,
- cache location,
- whether to translate actions/buttons,
- whether to translate debug text.

Example shape:

```json
{
  "translation": {
    "enabled": true,
    "source_language": "ja",
    "target_language": "zh-Hans",
    "provider": "openai-compatible",
    "endpoint": "https://api.example.com/v1/chat/completions",
    "model": "translation-model",
    "api_key_env": "ERAPLAY_TRANSLATION_API_KEY",
    "cache": true,
    "translate_channels": ["info", "main", "actions"]
  }
}
```

## Cache Strategy

Translation should be cached by stable keys:

```text
hash(provider, model, source_language, target_language, original_text)
```

Caching matters because ERA games repeatedly print the same menu options and
status labels.

## Channel Behavior

| Channel | Default Translation |
| --- | --- |
| `info` | yes |
| `main` | yes |
| `actions` | yes |
| `history` | use already translated rendered text when possible |
| `debug` | no |

The UI should allow users to toggle original/translated/bilingual display.

## Bilingual Display

For old Japanese and Traditional Chinese games, bilingual display is useful:

```text
通常業務
普通业务
```

This should be a renderer choice, not a runtime state change.

## Provider Boundary

The engine core should not depend on one translation vendor. It should define a
small interface:

```text
translate(text, source_language, target_language, context) -> translated_text
```

Providers can be implemented as plugins later.
