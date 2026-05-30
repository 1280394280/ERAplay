from __future__ import annotations

import re

from eraplay.ast import (
    Assignment,
    Call,
    Case,
    CaseElse,
    Command,
    ElseBlock,
    ElseIfBlock,
    EndIf,
    EndSelect,
    Goto,
    IfBlock,
    Label,
    Node,
    Program,
    Return,
    SelectCase,
    SourceSpan,
)
from eraplay.diagnostics import Diagnostic, EraPlaySyntaxError
from eraplay.lexer import LogicalLine, iter_logical_lines

_ASSIGN_RE = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*(?:\s*:\s*[A-Za-z0-9_]+)*(?:\s*\([^)]*\))?)\s*'?\s*(=|\+=|-=)\s*(.+)$"
)


def parse_source(source: str, filename: str = "<memory>") -> Program:
    return parse_lines(iter_logical_lines(source, filename))


def parse_lines(lines: list[LogicalLine]) -> Program:
    nodes: list[Node] = []
    for line in lines:
        nodes.append(parse_line(line))
    return Program(tuple(nodes))


def parse_line(line: LogicalLine) -> Node:
    text = line.text
    upper = text.upper()

    if text.startswith("@") or text.startswith("$"):
        name, args = _split_label_name_args(text[1:].strip())
        return Label(line.span, name, name.upper().startswith("EVENT"), text.startswith("$"), args)

    if upper == "ELSE":
        return ElseBlock(line.span)

    if upper.startswith("ELSEIF "):
        return ElseIfBlock(line.span, text[7:].strip())

    if upper == "ENDIF":
        return EndIf(line.span)

    if upper == "CASEELSE":
        return CaseElse(line.span)

    if upper == "ENDSELECT":
        return EndSelect(line.span)

    if upper.startswith("IF "):
        return IfBlock(line.span, text[3:].strip())

    if upper.startswith("SELECTCASE "):
        return SelectCase(line.span, text[11:].strip())

    if upper.startswith("CASE "):
        values = tuple(part.strip() for part in _split_csv_like(text[5:].strip()) if part.strip())
        return Case(line.span, values)

    if upper.startswith("#DIM "):
        return Command(line.span, "#DIM", (text[5:].strip(),))

    if upper.startswith("#DIMS "):
        return Command(line.span, "#DIMS", (text[6:].strip(),))

    print_command = _match_raw_text_command(text)
    if print_command is not None:
        return Command(line.span, print_command[0], (print_command[1],))

    if upper.startswith("CALL "):
        target, args = _split_head_args(text[5:].strip(), line.span)
        return Call(line.span, target, args)

    if upper.startswith("GOTO "):
        target, _ = _split_head_args(text[5:].strip(), line.span)
        return Goto(line.span, target)

    if upper.startswith("JUMP "):
        target, _ = _split_head_args(text[5:].strip(), line.span)
        return Goto(line.span, target)

    if upper == "RETURN":
        return Return(line.span)

    if upper.startswith("RETURN "):
        return Return(line.span, text[7:].strip())

    assignment = _ASSIGN_RE.match(text)
    if assignment:
        target = _compact(assignment.group(1))
        operator = assignment.group(2)
        expression = assignment.group(3).strip()
        if operator == "+=":
            expression = f"{target} + ({expression})"
        elif operator == "-=":
            expression = f"{target} - ({expression})"
        return Assignment(line.span, target, expression)

    name, args = _split_head_args(text, line.span)
    return Command(line.span, name.upper(), args)


def _split_head_args(text: str, span: SourceSpan) -> tuple[str, tuple[str, ...]]:
    if not text:
        raise EraPlaySyntaxError(Diagnostic("expected command or label content", span))

    paren_args = _split_parenthesized_head_args(text)
    if paren_args is not None:
        return paren_args

    split_at = _find_head_end(text)
    if split_at is None:
        return text.strip(), ()
    head = text[:split_at].strip()
    tail = text[split_at:].strip()
    if tail.startswith(","):
        tail = tail[1:].strip()
    if not tail:
        return head, ()
    return head, tuple(part.strip() for part in _split_csv_like(tail) if part.strip())


def _split_label_name_args(text: str) -> tuple[str, tuple[str, ...]]:
    split = _split_parenthesized_head_args(text)
    if split is not None:
        return split
    return text, ()


def _find_head_end(text: str) -> int | None:
    for index, char in enumerate(text):
        if char.isspace() or char == ",":
            return index
    return None


def _match_raw_text_command(text: str) -> tuple[str, str] | None:
    upper = text.upper()
    for name in (
        "PRINTPLAINFORM",
        "PRINTFORML",
        "PRINTFORMW",
        "PRINTFORM",
        "PRINTL",
        "PRINT",
    ):
        if upper == name:
            return name, ""
        prefix = f"{name} "
        if upper.startswith(prefix):
            return name, text[len(prefix) :]
    return None


def _split_parenthesized_head_args(text: str) -> tuple[str, tuple[str, ...]] | None:
    head_end = text.find("(")
    if head_end <= 0:
        return None
    head = text[:head_end].strip()
    if not head or any(char.isspace() or char == "," for char in head):
        return None
    close = _find_matching_paren(text, head_end)
    if close is None:
        return None
    tail = text[close + 1 :].strip()
    if tail and not tail.startswith(","):
        return None
    arg_text = text[head_end + 1 : close]
    if tail.startswith(","):
        arg_text = f"{arg_text},{tail[1:].strip()}"
    args = tuple(part.strip() for part in _split_csv_like(arg_text) if part.strip())
    return head, args


def _find_matching_paren(text: str, open_index: int) -> int | None:
    depth = 0
    in_string = False
    escaped = False
    for index in range(open_index, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    return None


def _split_csv_like(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(depth - 1, 0)
        elif char == "," and depth == 0:
            parts.append(text[start:index])
            start = index + 1
    parts.append(text[start:])
    return parts


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)
