from pathlib import Path

from eraplay.webpreview import (
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


def test_webpreview_input_body_accepts_json() -> None:
    assert _input_value_from_body('{"value": "2"}', "application/json") == "2"


def test_webpreview_compat_state_reports_fixture_ok() -> None:
    server = create_preview_server(ROOT / "fixtures", entry="DEMO_MENU", port=0)
    try:
        state = _compat_state(server.session.current())
    finally:
        server.server_close()

    assert state["status"] == "ok"
    assert state["diagnostics"] == 0
    assert state["files"]["erb"] == 6


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
