# Text Compatibility

Old ERA projects often contain Japanese, Traditional Chinese, Simplified
Chinese, full-width symbols, and files saved with legacy encodings. ERAplay must
treat text compatibility as a core engine feature, not as a UI afterthought.

## Common Text Cases

| Case | Notes |
| --- | --- |
| UTF-8 with BOM | common in newer edited projects |
| UTF-8 without BOM | preferred for new ERAplay projects |
| Shift_JIS / CP932 | common in older Japanese ERA games |
| Big5 / CP950 | possible in Traditional Chinese projects |
| GBK / CP936 | possible in Simplified Chinese projects |
| mixed full-width text | command text may contain `　`, `：`, `，`, `！`, etc. |

## Design Goals

- Preserve source text exactly after decoding.
- Keep diagnostics useful for non-ASCII text.
- Avoid assuming all project files are UTF-8.
- Let users configure preferred encodings per project.
- Normalize only where the language requires it; do not silently rewrite game
  text between Japanese, Traditional Chinese, and Simplified Chinese.
- Keep output rendering font-aware so CJK glyphs, full-width punctuation, and
  monospaced alignment display correctly.

## Loading Strategy

ERAplay should use this order when reading text files:

1. Project-configured encoding, if present.
2. BOM detection.
3. UTF-8.
4. Compatibility fallbacks: CP932, CP950, CP936.

If a fallback is used, diagnostics should report it so the editor can offer to
convert the file to UTF-8.

Automatic legacy encoding detection is inherently unreliable. Some Big5/GBK
byte sequences can decode as CP932 without throwing an error, but produce wrong
text. Real projects should therefore store an explicit `source_encoding` in
project configuration whenever they are not UTF-8.

## New Project Recommendation

New ERAplay-native projects should use:

- UTF-8 without BOM,
- Unicode filenames,
- explicit project language metadata,
- optional font preferences.

## Editor Requirements

The editor should show:

- detected encoding,
- line/column diagnostics that work with CJK text,
- optional conversion to UTF-8,
- missing glyph warnings when the selected UI font cannot render text,
- search that works across Japanese, Traditional Chinese, and Simplified Chinese
  without destructive conversion.
