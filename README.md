# ERAplay

ERAplay is a modern experimental engine for ERA/Emuera-style text games.

The first goal is not full Emuera compatibility. The first goal is to build a
clean parser and runtime core that can grow toward compatibility with real ERB,
ERH, and CSV projects.

The long-term goal is a creator-friendly ERA platform: player, runtime, editor,
and extension system.

## Current Focus

- Parse a practical ERB subset into a typed AST.
- Keep Emuera behavior visible through compatibility notes and tests.
- Separate core execution from UI so the engine can target CLI, desktop, web,
  or mobile frontends.

## Local Development

```powershell
python -m pytest
```

Check a project directory:

```powershell
eraplay check D:\work\py\ERAplay\fixtures
```

List indexed symbols:

```powershell
eraplay symbols D:\work\py\ERAplay\fixtures
```

Project configuration lives in `eraplay.toml`:

```toml
[project]
source_encoding = "utf-8"

[translation]
enabled = false
target_language = "zh-Hans"
```

Create a project config:

```powershell
eraplay init D:\path\to\era-game --encoding cp932
```

Run the current minimal runtime:

```powershell
eraplay run D:\work\py\ERAplay\fixtures --entry EVENTFIRST
```

Play interactively in the terminal:

```powershell
eraplay play D:\work\py\ERAplay\fixtures --entry EVENTFIRST
```

## Reference Sources

The local sibling projects are used as references only:

- `D:\work\py\emuera-source`: canonical behavior reference.
- `D:\work\py\uEmuera-source`: Unity/mobile port reference.
- `D:\work\py\era-electron-source`: modern Electron/UI/API reference.
