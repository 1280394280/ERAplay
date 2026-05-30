from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from eraplay.analysis import analyze_project
from eraplay.diagnostics import Diagnostic
from eraplay.index import ProjectIndex, build_project_index
from eraplay.project import EraProject

_UNRESOLVED_CALL_RE = re.compile(r"^unresolved CALL target '(.+)'$")


@dataclass(frozen=True)
class CompatibilityReport:
    project: EraProject
    index: ProjectIndex
    diagnostics: tuple[Diagnostic, ...]

    @property
    def unresolved_calls(self) -> Counter[str]:
        calls: Counter[str] = Counter()
        for diagnostic in self.diagnostics:
            match = _UNRESOLVED_CALL_RE.match(diagnostic.message)
            if match:
                calls[match.group(1)] += 1
        return calls

    @property
    def diagnostic_kinds(self) -> Counter[str]:
        return Counter(_diagnostic_kind(diagnostic.message) for diagnostic in self.diagnostics)

    def to_dict(self, top: int = 20, external_calls: tuple[str, ...] = ()) -> dict[str, object]:
        return {
            "project": str(self.project.root),
            "files": {
                "erb": len(self.project.erb_files),
                "erh": len(self.project.erh_files),
                "csv": len(self.project.csv_files),
            },
            "data": {
                "variable_sizes": len(self.project.data.variable_sizes),
                "name_tables": {
                    name: len(table)
                    for name, table in sorted(self.project.data.name_tables.items())
                },
                "chara_files": len(self.project.data.chara_files),
                "game_base": {
                    "loaded": bool(self.project.data.game_base),
                    "title": _first_game_base_value(self.project.data.game_base, "タイトル"),
                    "version": _first_game_base_value(self.project.data.game_base, "バージョン"),
                },
            },
            "diagnostics": len(self.diagnostics),
            "diagnostic_kinds": [
                {"kind": kind, "count": count}
                for kind, count in self.diagnostic_kinds.most_common()
            ],
            "unresolved_calls": [
                {"target": name, "count": count}
                for name, count in self.unresolved_calls.most_common(top)
            ],
            "excluded_dirs": list(self.project.config.exclude_dirs),
            "external_calls": list((*self.project.config.external_calls, *external_calls)),
            "status": "ok" if not self.diagnostics else "issues",
        }


def build_compatibility_report(
    project: EraProject,
    external_calls: tuple[str, ...] = (),
) -> CompatibilityReport:
    index = build_project_index(project)
    diagnostics = analyze_project(project, index, external_calls=external_calls)
    return CompatibilityReport(project, index, diagnostics)


def _diagnostic_kind(message: str) -> str:
    if message.startswith("duplicate label"):
        return "duplicate label"
    if message.startswith("unresolved CALL"):
        return "unresolved CALL"
    if message.startswith("unresolved GOTO/JUMP"):
        return "unresolved GOTO/JUMP"
    if message.startswith("empty #DEFINE"):
        return "empty #DEFINE"
    if message.startswith("empty #DIM/#DIMS"):
        return "empty #DIM/#DIMS"
    if message.startswith("empty CSV key"):
        return "empty CSV key"
    return "other"


def _first_game_base_value(data: dict[str, tuple[str, ...]], key: str) -> str | None:
    values = data.get(key)
    if not values:
        return None
    return values[0]
