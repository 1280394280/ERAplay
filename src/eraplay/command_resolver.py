from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from eraplay.ast import Assignment, Call, ElseIfBlock, Goto, IfBlock, Label, Node, Return

if TYPE_CHECKING:
    from eraplay.runtime import MiniRuntime


@dataclass(frozen=True)
class CommandTarget:
    value: str
    detail: str


class CommandResolver:
    def __init__(self, runtime: MiniRuntime) -> None:
        self.runtime = runtime

    def resolve(self) -> dict[str, CommandTarget]:
        context = self.runtime.state.input_context
        if context is None:
            return {}
        if context.kind == "shop":
            return self._resolve_label("USERSHOP")
        if context.kind == "item_shop":
            return {"999": CommandTarget("999", "return to SHOW_SHOP")}
        if context.kind == "input" and self.runtime.stack:
            frame = self.runtime.stack[-1]
            return self._resolve_nodes(frame.nodes, frame.index)
        return {}

    def _resolve_label(self, label: str) -> dict[str, CommandTarget]:
        key = label.upper()
        if key not in self.runtime.labels:
            return {}
        nodes, start = self.runtime.labels[key]
        return self._resolve_nodes(nodes, start + 1)

    def _resolve_nodes(self, nodes: tuple[Node, ...], start: int) -> dict[str, CommandTarget]:
        targets: dict[str, CommandTarget] = {}
        for index in range(start, len(nodes)):
            node = nodes[index]
            if isinstance(node, Label) and not node.is_local:
                break
            value = _condition_result_value(node)
            if value is None:
                continue
            detail = self._summarize_branch(nodes, index + 1)
            if detail:
                targets[value] = CommandTarget(value, detail)
        return targets

    def _summarize_branch(self, nodes: tuple[Node, ...], start: int) -> str:
        parts: list[str] = []
        for index in range(start, len(nodes)):
            node = nodes[index]
            if isinstance(node, (IfBlock, ElseIfBlock, Label)):
                break
            if isinstance(node, Call):
                parts.append(f"CALL {node.target}")
                break
            if isinstance(node, Goto):
                parts.append(f"GOTO {node.target}")
                break
            if isinstance(node, Assignment):
                parts.append(f"{node.target} = {node.expression}")
                continue
            if isinstance(node, Return):
                parts.append("RETURN")
                break
        return " -> ".join(parts)


def _condition_result_value(node: Node) -> str | None:
    if not isinstance(node, (IfBlock, ElseIfBlock)):
        return None
    match = re.search(r"\bRESULT\s*==\s*(-?\d+)\b", node.condition, flags=re.IGNORECASE)
    return match.group(1) if match else None
