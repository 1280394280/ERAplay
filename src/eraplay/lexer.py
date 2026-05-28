from __future__ import annotations

from dataclasses import dataclass

from eraplay.ast import SourceSpan


@dataclass(frozen=True)
class LogicalLine:
    text: str
    span: SourceSpan


def strip_comment(line: str) -> str:
    in_string = False
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if char == ";" and not in_string:
            return line[:index]
    return line


def iter_logical_lines(source: str, filename: str = "<memory>") -> list[LogicalLine]:
    lines: list[LogicalLine] = []
    for line_no, raw_line in enumerate(source.splitlines(), start=1):
        text = strip_comment(raw_line).strip()
        if not text:
            continue
        lines.append(LogicalLine(text=text, span=SourceSpan(filename, line_no)))
    return lines
