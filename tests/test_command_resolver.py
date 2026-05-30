from pathlib import Path

from eraplay.project import load_project
from eraplay.runtime import MiniRuntime


def test_runtime_command_resolver_reports_input_branches(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
PRINTL "[1] Next"
PRINTL "[9] Exit"
INPUT
IF RESULT == 1
CALL NEXT
ELSEIF RESULT == 9
RETURN 0
ENDIF

@NEXT
PRINTL "next"
""",
        encoding="utf-8",
    )
    runtime = MiniRuntime(load_project(tmp_path))

    runtime.run()

    targets = runtime.command_resolver.resolve()
    assert targets["1"].detail == "CALL NEXT"
    assert targets["9"].detail == "RETURN"


def test_runtime_command_resolver_reports_shop_branches(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
BEGIN SHOP

@SHOW_SHOP
PRINTL "[101] Buy"

@USERSHOP
IF RESULT == 101
CALL BUY
ELSEIF RESULT == 102
BOUGHT = 1
ENDIF

@BUY
PRINTL "buy"
""",
        encoding="utf-8",
    )
    runtime = MiniRuntime(load_project(tmp_path))

    runtime.run()

    targets = runtime.command_resolver.resolve()
    assert targets["101"].detail == "CALL BUY"
    assert targets["102"].detail == "BOUGHT = 1"
