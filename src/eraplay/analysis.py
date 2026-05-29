from __future__ import annotations

from collections import defaultdict

from eraplay.ast import Call, Goto, Label, SourceSpan
from eraplay.diagnostics import Diagnostic
from eraplay.index import ProjectIndex, SymbolKind, build_project_index
from eraplay.project import EraProject


def analyze_project(project: EraProject, index: ProjectIndex | None = None) -> tuple[Diagnostic, ...]:
    if index is None:
        index = build_project_index(project)

    diagnostics: list[Diagnostic] = []
    diagnostics.extend(_diagnose_duplicate_labels(index))
    diagnostics.extend(_diagnose_unresolved_jumps(project, index))
    diagnostics.extend(_diagnose_erh_declarations(project))
    diagnostics.extend(_diagnose_csv_rows(project))
    return tuple(diagnostics)


def _diagnose_duplicate_labels(index: ProjectIndex) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    labels_by_name: dict[str, list[SourceSpan]] = defaultdict(list)
    for symbol in index.by_kind(SymbolKind.LABEL):
        if symbol.detail == "event":
            continue
        labels_by_name[symbol.name.upper()].append(symbol.span)

    for name, spans in labels_by_name.items():
        if len(spans) <= 1:
            continue
        first = spans[0]
        for duplicate in spans[1:]:
            diagnostics.append(
                Diagnostic(
                    f"duplicate label '{name}' also defined at {first.file}:{first.line}",
                    duplicate,
                    "error",
                )
            )
    return diagnostics


def _diagnose_unresolved_jumps(project: EraProject, index: ProjectIndex) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for loaded in project.erb_files:
        for node in loaded.program.nodes:
            if isinstance(node, Call) and not index.find(node.target, SymbolKind.LABEL):
                diagnostics.append(
                    Diagnostic(f"unresolved CALL target '{node.target}'", node.span, "error")
                )
            elif (
                isinstance(node, Goto)
                and not index.find(node.target, SymbolKind.LABEL)
                and not _has_local_label(loaded.program.nodes, node.target)
            ):
                diagnostics.append(
                    Diagnostic(f"unresolved GOTO/JUMP target '{node.target}'", node.span, "error")
                )
    return diagnostics


def _has_local_label(nodes: tuple[object, ...], target: str) -> bool:
    normalized = target.upper()
    return any(
        isinstance(node, Label) and node.is_local and node.name.upper() == normalized
        for node in nodes
    )


def _diagnose_erh_declarations(project: EraProject) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for loaded in project.erh_files:
        for define in loaded.document.defines:
            if not define.name:
                diagnostics.append(
                    Diagnostic("empty #DEFINE name", SourceSpan(define.file, define.line), "error")
                )
        for dim in loaded.document.dims:
            if not dim.name:
                diagnostics.append(
                    Diagnostic("empty #DIM/#DIMS name", SourceSpan(dim.file, dim.line), "error")
                )
    return diagnostics


def _diagnose_csv_rows(project: EraProject) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for loaded in project.csv_files:
        for row in loaded.document.rows:
            if not row.key:
                diagnostics.append(
                    Diagnostic("empty CSV key", SourceSpan(str(loaded.file.path), row.line), "error")
                )
    return diagnostics
