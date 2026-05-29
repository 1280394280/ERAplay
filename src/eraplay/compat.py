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
