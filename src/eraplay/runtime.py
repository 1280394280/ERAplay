from __future__ import annotations

import re
from dataclasses import dataclass, field

from eraplay.ast import Assignment, Call, Command, ElseBlock, EndIf, IfBlock, Label, Node, Return
from eraplay.console import ClassicConsoleBuffer
from eraplay.project import EraProject


@dataclass
class RuntimeState:
    variables: dict[str, int | str] = field(default_factory=dict)
    result: int | str | None = None
    waiting_for_input: bool = False


@dataclass
class RuntimeResult:
    console: ClassicConsoleBuffer
    state: RuntimeState


@dataclass
class RuntimeFrame:
    nodes: tuple[Node, ...]
    index: int


class RuntimeError(Exception):
    pass


class MiniRuntime:
    def __init__(self, project: EraProject) -> None:
        self.project = project
        self.console = ClassicConsoleBuffer()
        self.state = RuntimeState()
        self.labels = self._collect_labels(project)
        self.stack: list[RuntimeFrame] = []

    def run(self, entry: str = "EVENTFIRST") -> RuntimeResult:
        self.call(entry)
        return RuntimeResult(self.console, self.state)

    def resume(self, value: int | str) -> RuntimeResult:
        if not self.state.waiting_for_input:
            raise RuntimeError("runtime is not waiting for input")
        self.state.result = value
        self.state.variables["RESULT"] = value
        self.state.waiting_for_input = False
        self._run_until_wait()
        return RuntimeResult(self.console, self.state)

    def call(self, label: str) -> int | str | None:
        key = label.upper()
        if key not in self.labels:
            raise RuntimeError(f"missing label: {label}")
        nodes, start = self.labels[key]
        self.stack.append(RuntimeFrame(nodes, start + 1))
        self._run_until_wait()
        return self.state.result

    def _run_until_wait(self) -> None:
        while self.stack and not self.state.waiting_for_input:
            frame = self.stack[-1]
            if frame.index >= len(frame.nodes):
                self.stack.pop()
                continue
            node = frame.nodes[frame.index]
            if isinstance(node, Label):
                self.stack.pop()
                continue
            if isinstance(node, Return):
                self.state.result = self._eval_value(node.expression) if node.expression else None
                self.stack.pop()
                continue
            frame.index = self._execute_at(frame.nodes, frame.index)

    def _execute_at(self, nodes: tuple[Node, ...], index: int) -> int:
        node = nodes[index]
        if isinstance(node, IfBlock):
            if self._eval_condition(node.condition):
                return index + 1
            return self._find_else_or_endif(nodes, index) + 1
        if isinstance(node, ElseBlock):
            return self._find_matching_endif(nodes, index) + 1
        if isinstance(node, EndIf):
            return index + 1
        if isinstance(node, Call):
            self._push_call(node.target)
            return index + 1
        self._execute_node(node)
        return index + 1

    def _execute_node(self, node: Node) -> None:
        if isinstance(node, Command):
            self._execute_command(node)
        elif isinstance(node, Assignment):
            self.state.variables[node.target.upper()] = self._eval_value(node.expression)

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
            self.state.waiting_for_input = True
            return

    def _push_call(self, label: str) -> None:
        key = label.upper()
        if key not in self.labels:
            raise RuntimeError(f"missing label: {label}")
        nodes, start = self.labels[key]
        self.stack.append(RuntimeFrame(nodes, start + 1))

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

    def _eval_condition(self, expression: str) -> bool:
        for operator in (">=", "<=", "==", "!=", ">", "<"):
            if operator in expression:
                left, right = expression.split(operator, 1)
                left_value = self._eval_value(left)
                right_value = self._eval_value(right)
                return _compare_values(left_value, right_value, operator)
        return bool(self._eval_value(expression))

    @staticmethod
    def _find_else_or_endif(nodes: tuple[Node, ...], index: int) -> int:
        depth = 0
        for cursor in range(index + 1, len(nodes)):
            node = nodes[cursor]
            if isinstance(node, IfBlock):
                depth += 1
            elif isinstance(node, EndIf):
                if depth == 0:
                    return cursor
                depth -= 1
            elif isinstance(node, ElseBlock) and depth == 0:
                return cursor
        return len(nodes) - 1

    @staticmethod
    def _find_matching_endif(nodes: tuple[Node, ...], index: int) -> int:
        depth = 0
        for cursor in range(index + 1, len(nodes)):
            node = nodes[cursor]
            if isinstance(node, IfBlock):
                depth += 1
            elif isinstance(node, EndIf):
                if depth == 0:
                    return cursor
                depth -= 1
        return len(nodes) - 1

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


def _compare_values(left: int | str, right: int | str, operator: str) -> bool:
    if isinstance(left, int) and isinstance(right, int):
        left_value: int | str = left
        right_value: int | str = right
    else:
        left_value = str(left)
        right_value = str(right)

    if operator == ">=":
        return left_value >= right_value
    if operator == "<=":
        return left_value <= right_value
    if operator == "==":
        return left_value == right_value
    if operator == "!=":
        return left_value != right_value
    if operator == ">":
        return left_value > right_value
    if operator == "<":
        return left_value < right_value
    raise RuntimeError(f"unsupported operator: {operator}")
