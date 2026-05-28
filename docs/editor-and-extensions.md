# ERAplay Editor and Extensions

ERAplay should grow as a platform, not only as a player. The long-term shape is:

```text
ERAplay
├─ engine
│  ├─ parser/compiler/runtime
│  ├─ compatibility layer
│  └─ frontend adapters
├─ editor
│  ├─ project explorer
│  ├─ ERB/ERH/CSV editors
│  ├─ diagnostics
│  ├─ preview runner
│  └─ asset/resource tools
└─ extensions
   ├─ engine plugins
   ├─ editor plugins
   ├─ custom commands
   ├─ custom data tables
   └─ custom UI panels
```

## Editor Goals

The editor should help people make ERA games without forcing them to memorize
every Emuera quirk.

Core editor features:

- project creation from templates,
- ERB/ERH syntax highlighting,
- diagnostics with file, line, and column,
- autocomplete for labels, variables, functions, CSV names, and commands,
- jump to definition for labels, variables, macros, and resources,
- rename support for project-local symbols,
- CSV table editor with schema hints,
- visual action/menu editor for common command layouts,
- live preview runner using the same runtime as the player,
- output-channel preview for `info`, `main`, `actions`, and `history`,
- save data inspector for debugging.

## Language Tooling

The parser should be built so it can power both runtime and editor tooling.

```text
source text
  |
  +--> lexer/parser
  |      |
  |      +--> AST
  |      +--> syntax diagnostics
  |
  +--> symbol index
  |      |
  |      +--> labels
  |      +--> variables
  |      +--> macros
  |      +--> CSV entries
  |
  +--> LSP/editor services
         |
         +--> completion
         +--> hover
         +--> go to definition
         +--> references
         +--> rename
```

The editor should ideally talk to the core through a stable API instead of
duplicating parser logic in the frontend.

## Extension Goals

Extensions should be possible without modifying the ERAplay core.

Potential extension points:

- add built-in ERB commands,
- add callable functions,
- add CSV/static-data schemas,
- add resource loaders,
- add save-data serializers,
- add UI panels,
- add editor commands,
- add project templates,
- add diagnostics or lint rules,
- add import/export tools.

## Plugin Boundaries

Extensions should be split by capability. A plugin can request one or more
capabilities:

| Capability | Purpose |
| --- | --- |
| `engine.command` | registers runtime commands |
| `engine.function` | registers callable functions |
| `engine.data_schema` | registers CSV/static-data schemas |
| `engine.resource_loader` | registers image/audio/custom loaders |
| `editor.panel` | adds editor UI panels |
| `editor.command` | adds editor actions |
| `editor.diagnostic` | adds lint/analysis rules |
| `template.project` | adds project templates |

## Safety Model

Plugins should not get unlimited access by default. The manifest should declare
capabilities and permissions explicitly.

Possible permission groups:

- `project.read`
- `project.write`
- `network`
- `process`
- `native`

For early development, plugins can be trusted local Python modules. Later,
ERAplay can add sandboxed JavaScript/WebAssembly plugins for safer distribution.

## Suggested Manifest

```json
{
  "id": "example.status-panel",
  "name": "Status Panel",
  "version": "0.1.0",
  "entry": "plugin.py",
  "capabilities": ["editor.panel"],
  "permissions": ["project.read"]
}
```

## Design Constraint

The runtime API, output event model, and parser diagnostics should be designed
as editor-facing APIs from the beginning. If the editor can inspect it, test it,
and preview it, creators will not be trapped inside a black-box interpreter.
