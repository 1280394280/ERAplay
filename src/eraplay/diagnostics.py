from __future__ import annotations

from dataclasses import dataclass

from eraplay.ast import SourceSpan


@dataclass(frozen=True)
class Diagnostic:
    message: str
    span: SourceSpan
    severity: str = "error"


class EraPlaySyntaxError(Exception):
    def __init__(self, diagnostic: Diagnostic) -> None:
        self.diagnostic = diagnostic
        super().__init__(
            f"{diagnostic.span.file}:{diagnostic.span.line}:"
            f"{diagnostic.span.column}: {diagnostic.message}"
        )
