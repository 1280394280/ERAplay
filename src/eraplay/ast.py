from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True)
class SourceSpan:
    file: str
    line: int
    column: int = 1


class NodeKind(str, Enum):
    LABEL = "label"
    COMMAND = "command"
    ASSIGNMENT = "assignment"
    RETURN = "return"
    IF = "if"
    ELSEIF = "elseif"
    ELSE = "else"
    ENDIF = "endif"
    SELECTCASE = "selectcase"
    CASE = "case"
    CASEELSE = "caseelse"
    ENDSELECT = "endselect"
    CALL = "call"
    GOTO = "goto"


@dataclass(frozen=True)
class Node:
    kind: NodeKind
    span: SourceSpan


@dataclass(frozen=True)
class Label(Node):
    name: str
    is_event: bool
    is_local: bool
    args: tuple[str, ...] = field(default_factory=tuple)

    def __init__(
        self,
        span: SourceSpan,
        name: str,
        is_event: bool,
        is_local: bool = False,
        args: tuple[str, ...] = (),
    ) -> None:
        object.__setattr__(self, "kind", NodeKind.LABEL)
        object.__setattr__(self, "span", span)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "is_event", is_event)
        object.__setattr__(self, "is_local", is_local)
        object.__setattr__(self, "args", args)


@dataclass(frozen=True)
class Command(Node):
    name: str
    args: tuple[str, ...] = field(default_factory=tuple)

    def __init__(self, span: SourceSpan, name: str, args: tuple[str, ...] = ()) -> None:
        object.__setattr__(self, "kind", NodeKind.COMMAND)
        object.__setattr__(self, "span", span)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "args", args)


@dataclass(frozen=True)
class Assignment(Node):
    target: str
    expression: str

    def __init__(self, span: SourceSpan, target: str, expression: str) -> None:
        object.__setattr__(self, "kind", NodeKind.ASSIGNMENT)
        object.__setattr__(self, "span", span)
        object.__setattr__(self, "target", target)
        object.__setattr__(self, "expression", expression)


@dataclass(frozen=True)
class Return(Node):
    expression: str | None = None

    def __init__(self, span: SourceSpan, expression: str | None = None) -> None:
        object.__setattr__(self, "kind", NodeKind.RETURN)
        object.__setattr__(self, "span", span)
        object.__setattr__(self, "expression", expression)


@dataclass(frozen=True)
class IfBlock(Node):
    condition: str

    def __init__(self, span: SourceSpan, condition: str) -> None:
        object.__setattr__(self, "kind", NodeKind.IF)
        object.__setattr__(self, "span", span)
        object.__setattr__(self, "condition", condition)


@dataclass(frozen=True)
class ElseIfBlock(Node):
    condition: str

    def __init__(self, span: SourceSpan, condition: str) -> None:
        object.__setattr__(self, "kind", NodeKind.ELSEIF)
        object.__setattr__(self, "span", span)
        object.__setattr__(self, "condition", condition)


@dataclass(frozen=True)
class ElseBlock(Node):
    def __init__(self, span: SourceSpan) -> None:
        object.__setattr__(self, "kind", NodeKind.ELSE)
        object.__setattr__(self, "span", span)


@dataclass(frozen=True)
class EndIf(Node):
    def __init__(self, span: SourceSpan) -> None:
        object.__setattr__(self, "kind", NodeKind.ENDIF)
        object.__setattr__(self, "span", span)


@dataclass(frozen=True)
class SelectCase(Node):
    expression: str

    def __init__(self, span: SourceSpan, expression: str) -> None:
        object.__setattr__(self, "kind", NodeKind.SELECTCASE)
        object.__setattr__(self, "span", span)
        object.__setattr__(self, "expression", expression)


@dataclass(frozen=True)
class Case(Node):
    values: tuple[str, ...]

    def __init__(self, span: SourceSpan, values: tuple[str, ...]) -> None:
        object.__setattr__(self, "kind", NodeKind.CASE)
        object.__setattr__(self, "span", span)
        object.__setattr__(self, "values", values)


@dataclass(frozen=True)
class CaseElse(Node):
    def __init__(self, span: SourceSpan) -> None:
        object.__setattr__(self, "kind", NodeKind.CASEELSE)
        object.__setattr__(self, "span", span)


@dataclass(frozen=True)
class EndSelect(Node):
    def __init__(self, span: SourceSpan) -> None:
        object.__setattr__(self, "kind", NodeKind.ENDSELECT)
        object.__setattr__(self, "span", span)


@dataclass(frozen=True)
class Call(Node):
    target: str
    args: tuple[str, ...] = field(default_factory=tuple)

    def __init__(self, span: SourceSpan, target: str, args: tuple[str, ...] = ()) -> None:
        object.__setattr__(self, "kind", NodeKind.CALL)
        object.__setattr__(self, "span", span)
        object.__setattr__(self, "target", target)
        object.__setattr__(self, "args", args)


@dataclass(frozen=True)
class Goto(Node):
    target: str

    def __init__(self, span: SourceSpan, target: str) -> None:
        object.__setattr__(self, "kind", NodeKind.GOTO)
        object.__setattr__(self, "span", span)
        object.__setattr__(self, "target", target)


@dataclass(frozen=True)
class Program:
    nodes: tuple[Node, ...]
