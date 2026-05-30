from __future__ import annotations

import re
from dataclasses import dataclass, field

from eraplay.ui import OutputChannel, OutputEvent, OutputKind, make_action


@dataclass
class ClassicConsoleBuffer:
    """A small virtual console for classic ERA-style output.

    The buffer keeps the current visible lines separate from scrollback history.
    Later renderers can classify the current lines into ERAplay UI channels while
    still preserving the old command-line feeling.
    """

    current_lines: list[str] = field(default_factory=lambda: [""])
    history_lines: list[str] = field(default_factory=list)

    def print(self, text: str) -> None:
        if not self.current_lines:
            self.current_lines.append("")
        parts = text.split("\n")
        self.current_lines[-1] += parts[0]
        for part in parts[1:]:
            self.current_lines.append(part)

    def print_line(self, text: str = "") -> None:
        self.print(text)
        self.current_lines.append("")

    def draw_line(self, char: str = "-", width: int = 80) -> None:
        self.print_line(char * width)

    def clear(self) -> None:
        self._move_current_to_history()
        self.current_lines = [""]

    def clear_lines(self, count: int) -> None:
        if count <= 0:
            return
        while len(self.current_lines) > 1 and self.current_lines[-1] == "":
            self.current_lines.pop()
        removed: list[str] = []
        for _ in range(min(count, len(self.current_lines))):
            removed.append(self.current_lines.pop())
        self.history_lines.extend(reversed(removed))
        if not self.current_lines:
            self.current_lines.append("")

    def visible_text(self) -> str:
        return "\n".join(_trim_trailing_empty(self.current_lines))

    def history_text(self) -> str:
        return "\n".join(_trim_trailing_empty(self.history_lines))

    def to_events(self) -> list[OutputEvent]:
        events: list[OutputEvent] = []
        for line in _trim_trailing_empty(self.current_lines):
            actions = _parse_action_line(line)
            if actions:
                events.extend(actions)
            else:
                events.append(OutputEvent(OutputChannel.MAIN, OutputKind.LINE, line))
        for line in _trim_trailing_empty(self.history_lines):
            events.append(OutputEvent(OutputChannel.HISTORY, OutputKind.LINE, line))
        return events

    def _move_current_to_history(self) -> None:
        self.history_lines.extend(_trim_trailing_empty(self.current_lines))


def _trim_trailing_empty(lines: list[str]) -> list[str]:
    trimmed = list(lines)
    while trimmed and trimmed[-1] == "":
        trimmed.pop()
    return trimmed


def _parse_action_line(line: str) -> list[OutputEvent]:
    brackets = list(re.finditer(r"\[([^\]]+)]", line))
    actions: list[OutputEvent] = []
    for index, match in enumerate(brackets):
        choice_id = match.group(1).strip()
        if not choice_id.isdigit():
            continue
        start = match.end()
        end = brackets[index + 1].start() if index + 1 < len(brackets) else len(line)
        text = line[start:end].strip()
        if text.startswith("-"):
            text = text[1:].strip()
        if text:
            actions.append(make_action(choice_id, text))
    return actions
