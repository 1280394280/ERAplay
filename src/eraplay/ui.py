from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from eraplay.ast import SourceSpan


class OutputChannel(str, Enum):
    INFO = "info"
    MAIN = "main"
    ACTIONS = "actions"
    HISTORY = "history"
    DEBUG = "debug"


class OutputKind(str, Enum):
    TEXT = "text"
    LINE = "line"
    CLEAR = "clear"
    ACTION = "action"


@dataclass(frozen=True)
class OutputEvent:
    channel: OutputChannel
    kind: OutputKind
    text: str = ""
    choice_id: str | None = None
    span: SourceSpan | None = None


def make_line(
    text: str,
    channel: OutputChannel = OutputChannel.MAIN,
    span: SourceSpan | None = None,
) -> OutputEvent:
    return OutputEvent(channel=channel, kind=OutputKind.LINE, text=text, span=span)


def make_action(
    choice_id: str,
    text: str,
    span: SourceSpan | None = None,
) -> OutputEvent:
    return OutputEvent(
        channel=OutputChannel.ACTIONS,
        kind=OutputKind.ACTION,
        text=text,
        choice_id=choice_id,
        span=span,
    )
