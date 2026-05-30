from pathlib import Path

from eraplay.webpreview import (
    PAGE_HTML,
    _body_value,
    _combined_log,
    _compat_state,
    _entry_state,
    _input_value_from_body,
    _query_int,
    _runtime_state,
    create_preview_server,
)
from eraplay.webpreview import _translation_with_mode

ROOT = Path(__file__).resolve().parents[1]


def test_webpreview_initial_state_has_actions() -> None:
    server = create_preview_server(ROOT / "fixtures", entry="DEMO_MENU", port=0)
    try:
        runtime = server.session.current()
        state = _runtime_state(runtime, runtime.project.config.translation, server.session.log)
    finally:
        server.server_close()

    assert state["waiting"] is True
    assert state["status"]["waiting"] is True
    assert state["status"]["steps"] > 0
    assert state["info"][0].startswith("state=waiting")
    assert {"id": "1", "text": "\u901a\u5e38\u696d\u52d9\n\u666e\u901a\u4e1a\u52a1"} in state["actions"]
    assert {"id": "2", "text": "\u8a3a\u5bdf\n\u8bca\u5bdf"} in state["actions"]


def test_webpreview_page_uses_fixed_viewport_layout() -> None:
    assert "height: 100dvh" in PAGE_HTML
    assert "overflow: hidden" in PAGE_HTML
    assert "grid-template-rows: minmax(0, 1fr) 120px 120px 160px" in PAGE_HTML


def test_webpreview_input_moves_previous_screen_to_history() -> None:
    server = create_preview_server(ROOT / "fixtures", entry="DEMO_MENU", port=0)
    runtime = server.session.current()
    try:
        runtime.console.clear()
        runtime.resume(2)
        server.session.add_log("input value=2")
        state = _runtime_state(runtime, runtime.project.config.translation, server.session.log)
    finally:
        server.server_close()

    assert state["waiting"] is False
    assert state["status"]["waiting"] is False
    assert state["status"]["result"] == 2
    assert state["info"][0].startswith("state=running")
    assert "\u8a3a\u5bdf\u3092\u9078\u629e\u3057\u307e\u3057\u305f\u3002\n\u5df2\u9009\u62e9\u8bca\u5bdf\u3002" in state["main"]
    assert "ERAplay demo\nERAplay \u6f14\u793a" in state["history"]
    assert "[2] \u8a3a\u5bdf\n[2] \u8bca\u5bdf" in state["history"]


def test_webpreview_continue_wait_has_continue_action(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text('@EVENTFIRST\nPRINTW "story"\nPRINTL "after"\n', encoding="utf-8")
    server = create_preview_server(tmp_path, entry="EVENTFIRST", port=0)
    try:
        runtime = server.session.current()
        state = _runtime_state(runtime, runtime.project.config.translation, server.session.log)
    finally:
        server.server_close()

    assert state["waiting"] is True
    assert state["status"]["waiting_reason"] == "continue"
    assert state["actions"] == [{"id": "", "text": "\u7ee7\u7eed"}]


def test_webpreview_shop_wait_keeps_menu_actions(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
BEGIN SHOP
@SHOW_SHOP
PRINTL "[105] 什么都不做"
""",
        encoding="utf-8",
    )
    server = create_preview_server(tmp_path, entry="EVENTFIRST", port=0)
    try:
        runtime = server.session.current()
        state = _runtime_state(runtime, runtime.project.config.translation, server.session.log)
    finally:
        server.server_close()

    assert state["waiting"] is True
    assert state["status"]["waiting_reason"] == "shop"
    assert {"id": "105", "text": "什么都不做"} in state["actions"]


def test_webpreview_translation_mode_override() -> None:
    server = create_preview_server(ROOT / "fixtures", entry="DEMO_MENU", port=0)
    try:
        runtime = server.session.current()
        config = runtime.project.config.translation
        original = _runtime_state(runtime, _translation_with_mode(config, "original"), server.session.log)
        translated = _runtime_state(runtime, _translation_with_mode(config, "translated"), server.session.log)
        bilingual = _runtime_state(runtime, _translation_with_mode(config, "bilingual"), server.session.log)
    finally:
        server.server_close()

    assert {"id": "1", "text": "\u901a\u5e38\u696d\u52d9"} in original["actions"]
    assert {"id": "1", "text": "\u666e\u901a\u4e1a\u52a1"} in translated["actions"]
    assert {"id": "1", "text": "\u901a\u5e38\u696d\u52d9\n\u666e\u901a\u4e1a\u52a1"} in bilingual["actions"]
    assert original["translation_mode"] == "original"
    assert translated["translation_mode"] == "translated"


def test_webpreview_session_restart() -> None:
    server = create_preview_server(ROOT / "fixtures", entry="DEMO_MENU", port=0)
    try:
        runtime = server.session.current()
        runtime.console.clear()
        runtime.resume(2)
        server.session.add_log("input value=2")
        finished = _runtime_state(runtime, runtime.project.config.translation, server.session.log)
        restarted = server.session.restart()
        fresh = _runtime_state(restarted, restarted.project.config.translation, server.session.log)
    finally:
        server.server_close()

    assert finished["waiting"] is False
    assert fresh["waiting"] is True
    assert fresh["history"] == []
    assert {"id": "2", "text": "\u8a3a\u5bdf\n\u8bca\u5bdf"} in fresh["actions"]
    assert fresh["log"][-1] == "restarted"


def test_webpreview_state_includes_event_log() -> None:
    server = create_preview_server(ROOT / "fixtures", entry="DEMO_MENU", port=0)
    try:
        state = _runtime_state(
            server.session.current(),
            server.session.current().project.config.translation,
            server.session.log,
        )
    finally:
        server.server_close()

    assert state["log"] == ["started entry=DEMO_MENU"]


def test_webpreview_combined_log_includes_runtime_trace() -> None:
    server = create_preview_server(ROOT / "fixtures", entry="DEMO_MENU", port=0)
    try:
        runtime = server.session.current()
        log = _combined_log(server.session, runtime)
    finally:
        server.server_close()

    assert "started entry=DEMO_MENU" in log
    assert "call entry=DEMO_MENU" in log
    assert "input waiting" in log


def test_webpreview_missing_entry_keeps_server_usable(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text("@EVENTFIRST\nPRINTL \"ok\"\n", encoding="utf-8")
    server = create_preview_server(tmp_path, entry="MISSING", port=0)
    try:
        runtime = server.session.current()
        state = _runtime_state(
            runtime,
            runtime.project.config.translation,
            server.session.log,
            server.session.error,
        )
        compat = _compat_state(runtime)
    finally:
        server.server_close()

    assert state["status"]["error"] == "missing label: MISSING"
    assert "error=missing label: MISSING" in state["info"]
    assert state["log"] == ["start failed error=missing label: MISSING"]
    assert compat["status"] == "ok"


def test_webpreview_can_switch_entry_after_missing_entry(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text("@EVENTFIRST\nPRINTL \"ok\"\n", encoding="utf-8")
    server = create_preview_server(tmp_path, entry="MISSING", port=0)
    try:
        server.session.switch_entry("EVENTFIRST")
        runtime = server.session.current()
        state = _runtime_state(
            runtime,
            runtime.project.config.translation,
            server.session.log,
            server.session.error,
            server.session.entry,
        )
    finally:
        server.server_close()

    assert state["status"]["entry"] == "EVENTFIRST"
    assert state["status"]["error"] is None
    assert state["main"] == ["ok"]
    assert state["log"][-1] == "entry switched entry=EVENTFIRST"


def test_webpreview_can_switch_to_title_entry(tmp_path: Path) -> None:
    (tmp_path / "CSV").mkdir()
    (tmp_path / "CSV" / "GameBase.csv").write_text("タイトル,Demo\nバージョン,1070\n", encoding="utf-8")
    (tmp_path / "main.erb").write_text("@EVENTFIRST\nPRINTL \"ok\"\n", encoding="utf-8")
    server = create_preview_server(tmp_path, entry="EVENTFIRST", port=0)
    try:
        server.session.switch_entry("__TITLE__")
        runtime = server.session.current()
        state = _runtime_state(
            runtime,
            runtime.project.config.translation,
            server.session.log,
            server.session.error,
            server.session.entry,
        )
    finally:
        server.server_close()

    assert state["status"]["entry"] == "__TITLE__"
    assert state["waiting"] is True
    assert "Demo" in state["main"]
    assert {"id": "0", "text": "新的开始"} in state["actions"]
    assert state["log"][-1] == "entry switched entry=__TITLE__"


def test_webpreview_input_body_accepts_json() -> None:
    assert _input_value_from_body('{"value": "2"}', "application/json") == "2"


def test_webpreview_body_value_accepts_entry_json() -> None:
    assert _body_value('{"entry": "EVENTFIRST"}', "application/json", "entry") == "EVENTFIRST"
    assert _body_value("entry=DEMO_MENU", "application/x-www-form-urlencoded", "entry") == "DEMO_MENU"


def test_webpreview_compat_state_reports_fixture_ok() -> None:
    server = create_preview_server(ROOT / "fixtures", entry="DEMO_MENU", port=0)
    try:
        state = _compat_state(server.session.current())
    finally:
        server.server_close()

    assert state["status"] == "ok"
    assert state["diagnostics"] == 0
    assert state["files"]["erb"] == 6
    assert state["data"]["variable_sizes"] == 0
    assert state["data"]["game_base"]["loaded"] is True


def test_webpreview_entry_state_lists_candidate_entries() -> None:
    server = create_preview_server(ROOT / "fixtures", entry="DEMO_MENU", port=0)
    try:
        state = _entry_state(server.session.current(), top=5)
    finally:
        server.server_close()

    names = [entry["name"] for entry in state["entries"]]
    assert state["count"] >= 3
    assert "DEMO_MENU" in names


def test_webpreview_entry_state_prioritizes_eventfirst(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        "@HELPER\nRETURN 0\n@EVENTFIRST\nPRINTL \"start\"\n",
        encoding="utf-8",
    )
    server = create_preview_server(tmp_path, entry="EVENTFIRST", port=0)
    try:
        state = _entry_state(server.session.current(), top=2)
    finally:
        server.server_close()

    assert state["entries"][0]["name"] == "EVENTFIRST"


def test_webpreview_query_int_uses_default_for_bad_values() -> None:
    assert _query_int({"top": ["3"]}, "top", 5) == 3
    assert _query_int({"top": ["bad"]}, "top", 5) == 5
