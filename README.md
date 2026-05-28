# ERAplay

ERAplay is a modern experimental engine for ERA/Emuera-style text games.

The first goal is not full Emuera compatibility. The first goal is to build a
clean parser and runtime core that can grow toward compatibility with real ERB,
ERH, and CSV projects.

## Current Focus

- Parse a practical ERB subset into a typed AST.
- Keep Emuera behavior visible through compatibility notes and tests.
- Separate core execution from UI so the engine can target CLI, desktop, web,
  or mobile frontends.

## Local Development

```powershell
python -m pytest
```

## Reference Sources

The local sibling projects are used as references only:

- `D:\work\py\emuera-source`: canonical behavior reference.
- `D:\work\py\uEmuera-source`: Unity/mobile port reference.
- `D:\work\py\era-electron-source`: modern Electron/UI/API reference.
