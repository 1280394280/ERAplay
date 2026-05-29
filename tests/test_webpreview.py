from pathlib import Path

from eraplay.webpreview import create_preview_server, _input_value_from_body, _runtime_state
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


def test_webpreview_input_body_accepts_json() -> None:
    assert _input_value_from_body('{"value": "2"}', "application/json") == "2"
