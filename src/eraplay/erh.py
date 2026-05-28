from __future__ import annotations

from dataclasses import dataclass

from eraplay.lexer import iter_logical_lines


@dataclass(frozen=True)
class ErhDefine:
    name: str
    value: str
    file: str
    line: int


@dataclass(frozen=True)
class ErhDim:
    name: str
    is_string: bool
    args: tuple[str, ...]
    file: str
    line: int


@dataclass(frozen=True)
class ErhDocument:
    defines: tuple[ErhDefine, ...]
    dims: tuple[ErhDim, ...]


def parse_erh_source(source: str, filename: str = "<memory>") -> ErhDocument:
    defines: list[ErhDefine] = []
    dims: list[ErhDim] = []
    for line in iter_logical_lines(source, filename):
        text = line.text
        upper = text.upper()
        if upper.startswith("#DEFINE "):
            name, value = _split_name_value(text[8:].strip())
            defines.append(ErhDefine(name, value, filename, line.span.line))
        elif upper.startswith("#DIM "):
            name, args = _split_dim(text[5:].strip())
            dims.append(ErhDim(name, False, args, filename, line.span.line))
        elif upper.startswith("#DIMS "):
            name, args = _split_dim(text[6:].strip())
            dims.append(ErhDim(name, True, args, filename, line.span.line))
    return ErhDocument(tuple(defines), tuple(dims))


def _split_name_value(text: str) -> tuple[str, str]:
    name, _, value = text.partition(" ")
    return name.strip(), value.strip()


def _split_dim(text: str) -> tuple[str, tuple[str, ...]]:
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts:
        return "", ()
    return parts[0], tuple(parts[1:])
