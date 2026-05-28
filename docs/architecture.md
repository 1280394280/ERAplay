# ERAplay Architecture

ERAplay is designed as a modern parser/runtime stack for ERA-style games.

It should eventually support three product surfaces:

- player: runs ERA/ERB games,
- editor: creates, validates, previews, and packages games,
- extension host: lets plugins add runtime and editor capabilities.

## Reference Map

| Area | Primary Reference | Notes |
| --- | --- | --- |
| ERB loading | `emuera-source/Emuera/Runtime/Script/Loader/ErbLoader.cs` | File order, labels, preprocessing, syntax checks |
| ERH loading | `emuera-source/Emuera/Runtime/Script/Loader/ErhLoader.cs` | `#DEFINE`, `#DIM`, `#DIMS`, user functions |
| Lexing | `emuera-source/Emuera/Runtime/Script/Parser/LexicalAnalyzer.cs` | Compatibility-sensitive token rules |
| Logical lines | `emuera-source/Emuera/Runtime/Script/Parser/LogicalLineParser.cs` | Labels, sharp lines, commands |
| Expressions | `emuera-source/Emuera/Runtime/Script/Statements/Expression/ExpressionParser.cs` | Operators, calls, term reduction |
| Variables | `emuera-source/Emuera/Runtime/Script/Statements/Variable` | Built-in variables, user variables, character data |
| Runtime process | `emuera-source/Emuera/Runtime/Script/Process.cs` | Initialization, execution state, input/output |
| Mobile/UI port | `uEmuera-source/Assets/Scripts` | Unity frontend and platform adaptation |
| Modern JS UI/API | `era-electron-source/src/era/model` | Electron IPC, resource loading, JS-facing API |
| Encoding/text IO | `emuera-source/Emuera/Runtime/Utils/EncodingHandler.cs` and `EraStreamReader.cs` | Japanese and CJK legacy encoding behavior |

## Target Layers

```text
project files
  CSV / ERH / ERB / assets / saves
        |
        v
loader
  file discovery, encoding, include order
        |
        v
preprocessor
  macros, header declarations, conditional blocks
        |
        v
lexer
  source text -> tokens
        |
        v
parser
  tokens/logical lines -> AST
        |
        v
compiler
  AST -> IR or bytecode
        |
        v
runtime
  VM, call stack, scheduler, input waits
        |
        v
state and adapters
  variables, character data, saves, UI, resource IO
```

## UI Direction

ERAplay should not treat the UI as a single disposable console surface forever.
The runtime should emit output events that can be rendered into separate regions:

- `info`
- `main`
- `actions`
- `history`
- `debug`

See `docs/ui-model.md` for the target interface model.

## Editor and Extension Direction

The parser, diagnostics, symbol tables, output events, and runtime state should
be treated as public internal APIs that an editor can consume. ERAplay should
avoid burying important behavior in UI-specific code.

See `docs/editor-and-extensions.md` for the creator tooling and plugin model.

## Text Compatibility

Old ERA projects may be Japanese, Traditional Chinese, Simplified Chinese, or a
mix of CJK text and full-width symbols. The loader should not assume UTF-8 only.

See `docs/text-compatibility.md` for the encoding and localization strategy.

## Display Translation

ERAplay should optionally translate rendered output through configurable APIs,
without rewriting source files or mutating runtime strings.

See `docs/translation.md` for the display translation strategy.

## Project Loading

The first project-level loader is intentionally small:

- discover `.erb`, `.erh`, and `.csv` files,
- decode text with the configured encoding strategy,
- parse ERB files into AST programs,
- parse ERH files into declarations,
- parse CSV files into key/value rows.

This loader is not yet a full Emuera-compatible load order implementation. It is
the foundation for diagnostics, fixtures, and editor project indexing.

## Project Indexing

After loading, ERAplay builds a lightweight symbol index:

- labels from ERB files,
- assigned variables from ERB files,
- `#DEFINE` macros from ERH files,
- `#DIM` and `#DIMS` declarations from ERH files,
- CSV keys from static data files.

The index is the first step toward editor features like autocomplete, jump to
definition, references, rename, and project-wide diagnostics.

## Compatibility Strategy

ERAplay should keep two modes:

- `modern`: predictable behavior, better diagnostics, stricter project layout.
- `emuera`: behavior follows Emuera where real games rely on quirks.

Each compatibility feature should have:

- a small source sample,
- a parser/runtime test,
- a note pointing to the Emuera source location used as reference.

## Milestones

1. Parse labels, commands, assignments, `IF/ELSE/ENDIF`, and `CALL`.
2. Load ERH declarations and simple `#DEFINE` macros.
3. Load basic CSV tables into structured data.
4. Execute a tiny demo game in a CLI frontend.
5. Add diagnostics with file, line, and column spans.
6. Add save/load for runtime state.
7. Add a web or desktop frontend adapter.
