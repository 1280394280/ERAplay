from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from eraplay.ast import Assignment, Label, SourceSpan
from eraplay.project import EraProject


class SymbolKind(str, Enum):
    LABEL = "label"
    VARIABLE = "variable"
    DEFINE = "define"
    CSV_KEY = "csv_key"


@dataclass(frozen=True)
class Symbol:
    name: str
    kind: SymbolKind
    span: SourceSpan
    detail: str = ""


@dataclass(frozen=True)
class ProjectIndex:
    symbols: tuple[Symbol, ...]

    def by_kind(self, kind: SymbolKind) -> tuple[Symbol, ...]:
        return tuple(symbol for symbol in self.symbols if symbol.kind is kind)

    def find(self, name: str, kind: SymbolKind | None = None) -> tuple[Symbol, ...]:
        normalized = name.upper()
        return tuple(
            symbol
            for symbol in self.symbols
            if symbol.name.upper() == normalized and (kind is None or symbol.kind is kind)
        )


def build_project_index(project: EraProject) -> ProjectIndex:
    symbols: list[Symbol] = []
    symbols.extend(_index_erb(project))
    symbols.extend(_index_erh(project))
    symbols.extend(_index_csv(project))
    return ProjectIndex(tuple(symbols))


def _index_erb(project: EraProject) -> list[Symbol]:
    symbols: list[Symbol] = []
    seen_variables: set[tuple[str, str]] = set()
    for loaded in project.erb_files:
        for node in loaded.program.nodes:
            if isinstance(node, Label):
                detail = "event" if node.is_event else "function"
                symbols.append(Symbol(node.name, SymbolKind.LABEL, node.span, detail))
            elif isinstance(node, Assignment):
                variable_name = _base_variable_name(node.target)
                key = (node.span.file, variable_name.upper())
                if key not in seen_variables:
                    seen_variables.add(key)
                    symbols.append(
                        Symbol(variable_name, SymbolKind.VARIABLE, node.span, "assignment")
                    )
    return symbols


def _index_erh(project: EraProject) -> list[Symbol]:
    symbols: list[Symbol] = []
    for loaded in project.erh_files:
        for define in loaded.document.defines:
            symbols.append(
                Symbol(
                    define.name,
                    SymbolKind.DEFINE,
                    SourceSpan(define.file, define.line),
                    define.value,
                )
            )
        for dim in loaded.document.dims:
            detail = "string" if dim.is_string else "integer"
            if dim.args:
                detail = f"{detail}[{', '.join(dim.args)}]"
            symbols.append(
                Symbol(
                    dim.name,
                    SymbolKind.VARIABLE,
                    SourceSpan(dim.file, dim.line),
                    detail,
                )
            )
    return symbols


def _index_csv(project: EraProject) -> list[Symbol]:
    symbols: list[Symbol] = []
    for loaded in project.csv_files:
        csv_name = _relative_or_name(project.root, loaded.file.path)
        for row in loaded.document.rows:
            symbols.append(
                Symbol(
                    row.key,
                    SymbolKind.CSV_KEY,
                    SourceSpan(str(loaded.file.path), row.line),
                    csv_name,
                )
            )
    return symbols


def _base_variable_name(target: str) -> str:
    return target.split(":", 1)[0].split("(", 1)[0]


def _relative_or_name(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return path.name
