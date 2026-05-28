# ERAplay UI Model

Traditional ERA/Emuera games write almost everything into one console-like text
surface. ERAplay should preserve that command-line history feeling, but split the
visible output into structured areas.

## Target Layout

```text
┌──────────────────────────────────────────────────────────────┐
│ info                                                         │
│ short menu lists, alerts, help, compact command summaries     │
├──────────────────────────────────────────────┬───────────────┤
│ main                                         │ side/status   │
│ current scene, narration, character status,  │ optional      │
│ persistent state blocks                      │ inspectors    │
├──────────────────────────────────────────────┴───────────────┤
│ actions                                                      │
│ selectable command buttons and numeric choices               │
├──────────────────────────────────────────────────────────────┤
│ history                                                      │
│ old output, like a terminal scrollback                       │
└──────────────────────────────────────────────────────────────┘
```

The user-provided reference image marks three important areas:

- `info`: top menu and compact informational text.
- `main`: current scene and state, including character and world values.
- `actions`: selectable options and input prompts.

ERAplay adds a fourth conceptual area:

- `history`: old output remains available like a command-line scrollback.

## Design Goals

- Keep old information instead of clearing it permanently.
- Let the runtime emit semantic output events instead of raw screen mutations.
- Allow a compatibility renderer to reproduce classic Emuera output.
- Allow modern renderers to place the same events into separate UI regions.
- Keep button choices as data, not just styled text, so mouse/touch/keyboard can
  use the same command source.

## Output Channels

| Channel | Purpose | Examples |
| --- | --- | --- |
| `info` | compact current menus and notices | daily menu, help, warnings |
| `main` | main scene and state | narration, status blocks, character panels |
| `actions` | current input choices | `[95] 思考一下`, `[97] 首先是诊察！` |
| `history` | scrollback of previous output | prior scenes, prior choices, logs |
| `debug` | developer diagnostics | parser/runtime traces |

## Runtime Event Flow

```text
ERB command
  PRINT / PRINTL / INPUT / CLEARLINE / DRAWLINE
        |
        v
runtime output event
        |
        v
layout classifier
        |
        +--> info channel
        +--> main channel
        +--> actions channel
        +--> history channel
```

In modern mode, ERAplay should prefer explicit channel events. In Emuera
compatibility mode, a classifier can infer channels from the classic text stream.

## Compatibility Notes

Many existing ERB games rely on `CLEARLINE`, repeated `PRINT`, and menu text
layout. ERAplay should not require old games to be rewritten immediately.

The compatibility renderer can maintain a virtual classic console:

1. Execute output commands against a virtual line buffer.
2. Snapshot changed lines into semantic regions when possible.
3. Preserve previous snapshots in `history`.
4. Expose current numeric choices as `actions`.

ERAplay currently starts this idea with a `ClassicConsoleBuffer`: a small virtual
console that keeps `current_lines` and `history_lines` separate. This gives the
runtime a compatibility path before smarter UI classification exists.

New ERAplay-native scripts can use explicit APIs later, for example:

```erb
PRINT_INFO "今天的头版新闻"
PRINT_MAIN "患者请进！"
PRINT_ACTION 95, "思考一下"
```

Those APIs are illustrative only; exact names should be decided after the
compatibility layer is working.
