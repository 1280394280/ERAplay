from __future__ import annotations

import re
from dataclasses import dataclass, field

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
    Return,
    SelectCase,
)
from eraplay.console import ClassicConsoleBuffer
from eraplay.project import EraProject


@dataclass
class RuntimeState:
    variables: dict[str, int | str] = field(default_factory=dict)
    result: int | str | None = None
    waiting_for_input: bool = False
    waiting_reason: str | None = None
    steps: int = 0


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
    def __init__(self, project: EraProject, max_steps: int = 10000, max_trace: int = 200) -> None:
        self.project = project
        self.console = ClassicConsoleBuffer()
        self.state = RuntimeState()
        self.labels = self._collect_labels(project)
        self.stack: list[RuntimeFrame] = []
        self.max_steps = max_steps
        self.max_trace = max_trace
        self.trace: list[str] = []
        self._startup_waiting = False

    def run(self, entry: str = "EVENTFIRST") -> RuntimeResult:
        if _is_startup_entry(entry):
            self._show_startup_screen()
            return RuntimeResult(self.console, self.state)
        self.call(entry)
        return RuntimeResult(self.console, self.state)

    def resume(self, value: int | str) -> RuntimeResult:
        if not self.state.waiting_for_input:
            raise RuntimeError("runtime is not waiting for input")
        self.state.result = value
        self.state.variables["RESULT"] = value
        self.state.waiting_for_input = False
        self.state.waiting_reason = None
        if self._startup_waiting:
            self._startup_waiting = False
            self._resume_startup(value)
            return RuntimeResult(self.console, self.state)
        self._run_until_wait()
        return RuntimeResult(self.console, self.state)

    def call(self, label: str) -> int | str | None:
        key = label.upper()
        if key not in self.labels:
            raise RuntimeError(f"missing label: {label}")
        nodes, start = self.labels[key]
        self._trace(f"call entry={key}")
        self.stack.append(RuntimeFrame(nodes, start + 1))
        self._run_until_wait()
        return self.state.result

    def _run_until_wait(self) -> None:
        while self.stack and not self.state.waiting_for_input:
            self.state.steps += 1
            if self.state.steps > self.max_steps:
                raise RuntimeError(f"runtime step limit exceeded: {self.max_steps}")
            frame = self.stack[-1]
            if frame.index >= len(frame.nodes):
                self.stack.pop()
                continue
            node = frame.nodes[frame.index]
            if isinstance(node, Label):
                if node.is_local:
                    frame.index += 1
                    continue
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
            return self._find_next_if_branch(nodes, index)
        if isinstance(node, ElseIfBlock):
            return self._find_matching_endif(nodes, index) + 1
        if isinstance(node, ElseBlock):
            return self._find_matching_endif(nodes, index) + 1
        if isinstance(node, EndIf):
            return index + 1
        if isinstance(node, SelectCase):
            return self._select_case_target(nodes, index)
        if isinstance(node, (Case, CaseElse)):
            return self._find_matching_endselect(nodes, index) + 1
        if isinstance(node, EndSelect):
            return index + 1
        if isinstance(node, Call):
            self._trace(f"call target={node.target}")
            self._push_call(node.target)
            return index + 1
        if isinstance(node, Goto):
            self._trace(f"goto target={node.target}")
            self._replace_current_frame(node.target)
            return self.stack[-1].index
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
            self.console.print(self._format_text(text))
        elif command.name == "PRINTL":
            self.console.print_line(self._format_text(text))
        elif command.name in {"PRINTFORM", "PRINTPLAINFORM"}:
            self.console.print(self._format_text(text))
        elif command.name in {"PRINTFORML", "PRINTFORMW"}:
            self.console.print_line(self._format_text(text))
        elif command.name == "DRAWLINE":
            self.console.draw_line()
        elif command.name == "CLEAR":
            self.console.clear()
        elif command.name in {"#DIM", "#DIMS"}:
            self._execute_dim(command)
        elif command.name == "INPUT":
            self._trace("input waiting")
            self.state.waiting_for_input = True
            self.state.waiting_reason = "input"
            return
        else:
            self._trace(f"ignored command={command.name}")

    def _push_call(self, label: str) -> None:
        key = label.upper()
        if key not in self.labels:
            raise RuntimeError(f"missing label: {label}")
        nodes, start = self.labels[key]
        self.stack.append(RuntimeFrame(nodes, start + 1))

    def _replace_current_frame(self, label: str) -> None:
        local_index = self._find_local_label(self.stack[-1].nodes, label)
        if local_index is not None:
            self.stack[-1].index = local_index + 1
            return
        key = label.upper()
        if key not in self.labels:
            raise RuntimeError(f"missing label: {label}")
        nodes, start = self.labels[key]
        self.stack[-1] = RuntimeFrame(nodes, start + 1)

    def _eval_value(self, expression: str | None) -> int | str:
        if expression is None:
            return 0
        expression = expression.strip()
        if _is_percent_wrapped(expression):
            return self._eval_value(expression[1:-1])
        if _is_quoted(expression):
            return self._unquote(expression)
        if re.fullmatch(r"-?\d+", expression):
            return int(expression)
        if "+" in expression:
            values: list[int | str] = []
            for part in expression.split("+"):
                values.append(self._eval_value(part))
            if all(isinstance(value, int) for value in values):
                return sum(int(value) for value in values)
            return "".join(str(value) for value in values)
        return self.state.variables.get(expression.upper(), 0)

    def _execute_dim(self, command: Command) -> None:
        if not command.args:
            return
        declaration = command.args[0]
        left, separator, right = declaration.partition("=")
        target = left.split(",", 1)[0].strip().upper()
        if not target:
            return
        if not separator:
            self.state.variables.setdefault(target, "")
            return
        values = [_strip_optional_percent(part.strip()) for part in _split_csv_like(right)]
        for index, value in enumerate(values):
            key = target if index == 0 else f"{target}:{index}"
            self.state.variables[key] = self._eval_value(value)

    def _format_text(self, text: str) -> str:
        unquoted = _unquote_print_text(text)

        def replace_percent(match: re.Match[str]) -> str:
            return str(self._eval_value(match.group(1)))

        def replace_brace(match: re.Match[str]) -> str:
            return str(self._eval_value(match.group(1)))

        formatted = re.sub(r"%([^%]+)%", replace_percent, unquoted)
        return re.sub(r"\{([^{}]+)\}", replace_brace, formatted)

    def _show_startup_screen(self) -> None:
        self._trace("startup screen")
        game_base = self.project.data.game_base
        self.console.draw_line(width=213)
        title = _first_game_base_value(game_base, "タイトル")
        version = _first_game_base_value(game_base, "バージョン")
        author = _first_game_base_value(game_base, "作者")
        year = _first_game_base_value(game_base, "製作年")
        detail = _first_game_base_value(game_base, "追加情報")
        if title:
            self.console.print_line(title)
        if version:
            self.console.print_line(_format_gamebase_version(version))
        if author:
            self.console.print_line(author)
        if year:
            self.console.print_line(f"({year})")
        if detail:
            self.console.print_line(detail)
        self.console.print_line(" ")
        self.console.draw_line(width=213)
        self.console.print_line("[0] 新的开始")
        self.console.print_line("[1] 载入存档")
        self.state.waiting_for_input = True
        self.state.waiting_reason = "startup"
        self._startup_waiting = True

    def _resume_startup(self, value: int | str) -> None:
        if value == 0 or value == "0":
            self.console.clear()
            self.call("EVENTFIRST")
            return
        if value == 1 or value == "1":
            self.console.print_line("载入存档尚未实现。")
            self.state.waiting_for_input = True
            self.state.waiting_reason = "startup"
            self._startup_waiting = True
            self._trace("loadgame unsupported")
            return
        self.state.waiting_for_input = True
        self.state.waiting_reason = "startup"
        self._startup_waiting = True

    def _eval_condition(self, expression: str) -> bool:
        for operator in (">=", "<=", "==", "!=", ">", "<"):
            if operator in expression:
                left, right = expression.split(operator, 1)
                left_value = self._eval_value(left)
                right_value = self._eval_value(right)
                return _compare_values(left_value, right_value, operator)
        return bool(self._eval_value(expression))

    def _find_next_if_branch(self, nodes: tuple[Node, ...], index: int) -> int:
        depth = 0
        for cursor in range(index + 1, len(nodes)):
            node = nodes[cursor]
            if isinstance(node, IfBlock):
                depth += 1
            elif isinstance(node, EndIf):
                if depth == 0:
                    return cursor + 1
                depth -= 1
            elif depth == 0 and isinstance(node, ElseIfBlock):
                if self._eval_condition(node.condition):
                    return cursor + 1
            elif depth == 0 and isinstance(node, ElseBlock):
                return cursor + 1
        return len(nodes)

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

    def _select_case_target(self, nodes: tuple[Node, ...], index: int) -> int:
        select = nodes[index]
        if not isinstance(select, SelectCase):
            return index + 1
        selected_value = self._eval_value(select.expression)
        case_else_index: int | None = None
        depth = 0
        for cursor in range(index + 1, len(nodes)):
            node = nodes[cursor]
            if isinstance(node, SelectCase):
                depth += 1
            elif isinstance(node, EndSelect):
                if depth == 0:
                    if case_else_index is not None:
                        return case_else_index + 1
                    return cursor + 1
                depth -= 1
            elif depth == 0 and isinstance(node, Case):
                if any(self._eval_value(value) == selected_value for value in node.values):
                    return cursor + 1
            elif depth == 0 and isinstance(node, CaseElse):
                case_else_index = cursor
        return len(nodes)

    @staticmethod
    def _find_matching_endselect(nodes: tuple[Node, ...], index: int) -> int:
        depth = 0
        for cursor in range(index + 1, len(nodes)):
            node = nodes[cursor]
            if isinstance(node, SelectCase):
                depth += 1
            elif isinstance(node, EndSelect):
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
                if isinstance(node, Label) and not node.is_local:
                    labels.setdefault(node.name.upper(), (nodes, index))
        return labels

    @staticmethod
    def _find_local_label(nodes: tuple[Node, ...], label: str) -> int | None:
        normalized = label.upper()
        for index, node in enumerate(nodes):
            if isinstance(node, Label) and node.is_local and node.name.upper() == normalized:
                return index
        return None

    def _trace(self, message: str) -> None:
        self.trace.append(message)
        if len(self.trace) > self.max_trace:
            del self.trace[: len(self.trace) - self.max_trace]


def run_project(project: EraProject, entry: str = "EVENTFIRST") -> RuntimeResult:
    return MiniRuntime(project).run(entry)


def _is_startup_entry(entry: str) -> bool:
    return entry.upper() in {"__TITLE__", "__STARTUP__"}


def _first_game_base_value(data: dict[str, tuple[str, ...]], key: str) -> str | None:
    values = data.get(key)
    if not values:
        return None
    return values[0]


def _format_gamebase_version(version: str) -> str:
    if version.isdigit() and len(version) == 4:
        major = version[0].lstrip("0") or "0"
        minor = version[1:3]
        return f"{major}.{minor}"
    if version.isdigit() and len(version) == 3:
        return f"0.{version[:2]}"
    return version


def _is_quoted(text: str) -> bool:
    return len(text) >= 2 and text[0] == '"' and text[-1] == '"'


def _unquote_print_text(text: str) -> str:
    stripped = text.strip()
    if _is_quoted(stripped):
        return stripped[1:-1]
    return text


def _is_percent_wrapped(text: str) -> bool:
    return len(text) >= 2 and text[0] == "%" and text[-1] == "%"


def _strip_optional_percent(text: str) -> str:
    if _is_percent_wrapped(text):
        return text[1:-1]
    return text


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
