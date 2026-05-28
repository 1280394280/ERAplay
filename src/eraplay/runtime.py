from __future__ import annotations

import re
from dataclasses import dataclass, field

from eraplay.ast import Assignment, Call, Command, Label, Node, Return
from eraplay.console import ClassicConsoleBuffer
from eraplay.project import EraProject


@dataclass
class RuntimeState:
    variables: dict[str, int | str] = field(default_factory=dict)
    result: int | str | None = None


@dataclass
class RuntimeResult:
    console: ClassicConsoleBuffer
    state: RuntimeState


class RuntimeError(Exception):
    pass


class MiniRuntime:
    def __init__(self, project: EraProject) -> None:
        self.project = project
        self.console = ClassicConsoleBuffer()
        self.state = RuntimeState()
        self.labels = self._collect_labels(project)

    def run(self, entry: str = "EVENTFIRST") -> RuntimeResult:
        self.call(entry)
        return RuntimeResult(self.console, self.state)

    def call(self, label: str) -> int | str | None:
        key = label.upper()
        if key not in self.labels:
            raise RuntimeError(f"missing label: {label}")
        nodes, start = self.labels[key]
        index = start + 1
        while index < len(nodes):
            node = nodes[index]
            if isinstance(node, Label):
                break
            if isinstance(node, Return):
                self.state.result = self._eval_value(node.expression) if node.expression else None
                return self.state.result
            self._execute_node(node)
            index += 1
        return None

    def _execute_node(self, node: Node) -> None:
        if isinstance(node, Command):
            self._execute_command(node)
        elif isinstance(node, Assignment):
            self.state.variables[node.target.upper()] = self._eval_value(node.expression)
        elif isinstance(node, Call):
            self.call(node.target)

    def _execute_command(self, command: Command) -> None:
        text = " ".join(command.args)
        if command.name == "PRINT":
            self.console.print(self._unquote(text))
        elif command.name == "PRINTL":
            self.console.print_line(self._unquote(text))
        elif command.name == "DRAWLINE":
            self.console.draw_line()
        elif command.name == "CLEAR":
            self.console.clear()
        elif command.name == "INPUT":
            return

    def _eval_value(self, expression: str | None) -> int | str:
        if expression is None:
            return 0
        expression = expression.strip()
        if _is_quoted(expression):
            return self._unquote(expression)
        if re.fullmatch(r"-?\d+", expression):
            return int(expression)
        if "+" in expression:
            total = 0
            for part in expression.split("+"):
                value = self._eval_value(part)
                total += int(value)
            return total
        return self.state.variables.get(expression.upper(), 0)

    @staticmethod
    def _unquote(text: str) -> str:
        text = text.strip()
        if _is_quoted(text):
            return text[1:-1]
        return text

    @staticmethod
    def _collect_labels(project: EraProject) -> dict[str, tuple[tuple[Node, ...], int]]:
        labels: dict[str, tuple[tuple[Node, ...], int]] = {}
        for loaded in project.erb_files:
            nodes = loaded.program.nodes
            for index, node in enumerate(nodes):
                if isinstance(node, Label):
                    labels.setdefault(node.name.upper(), (nodes, index))
        return labels


def run_project(project: EraProject, entry: str = "EVENTFIRST") -> RuntimeResult:
    return MiniRuntime(project).run(entry)


def _is_quoted(text: str) -> bool:
    return len(text) >= 2 and text[0] == '"' and text[-1] == '"'
