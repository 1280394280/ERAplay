import os
from pathlib import Path

import pytest

from eraplay.compat import build_compatibility_report
from eraplay.project import load_project
from eraplay.reference_log import parse_emuera_log
from eraplay.runtime import MiniRuntime
from eraplay.ui import OutputChannel, OutputKind

DEFAULT_REAL_PROJECT = Path(r"D:\新建文件夹\ERA\emuera\erAV-master")
DEFAULT_EMUERA_LOG = DEFAULT_REAL_PROJECT / "20260530-092446.log"


def _real_project_path() -> Path:
    return Path(os.environ.get("ERAPLAY_REAL_PROJECT", DEFAULT_REAL_PROJECT))


def _load_real_project():
    path = _real_project_path()
    if not path.exists():
        pytest.skip(f"real ERA project not found: {path}")
    return load_project(path)


def _real_log_path() -> Path:
    return Path(os.environ.get("ERAPLAY_EMUERA_LOG", DEFAULT_EMUERA_LOG))


def _load_real_log():
    path = _real_log_path()
    if not path.exists():
        pytest.skip(f"Emuera startup log not found: {path}")
    return parse_emuera_log(path)


def test_real_project_loads_erav_data_summary() -> None:
    project = _load_real_project()
    report = build_compatibility_report(project)

    assert len(project.erb_files) == 468
    assert len(project.erh_files) == 3
    assert len(project.csv_files) == 132
    assert project.data.variable_sizes["FLAG"] == 10000
    assert project.data.variable_sizes["ITEM"] == 1000
    assert project.data.game_base["タイトル"] == ("Erav",)
    assert project.data.game_base["バージョン"] == ("1070",)
    assert len(project.data.chara_files) == 120
    assert report.to_dict(top=5)["data"]["name_tables"]["TALENTNAME"] == 263


def test_real_emuera_log_matches_reference_startup_summary() -> None:
    summary = _load_real_log()
    project = _load_real_project()

    assert summary.macro_loaded is True
    assert len(summary.erb_files) == 468
    assert len(summary.erh_files) == 3
    assert len(summary.csv_files) == 131
    assert len(project.csv_files) == len(summary.csv_files) + 1
    assert project.data.game_base["タイトル"] == ("Erav",)
    assert summary.chara_csv_count == 120
    assert len(summary.warnings) == 28
    assert summary.non_comment_lines == 157951
    assert summary.function_count == 2227
    assert summary.call_count == 1184
    assert summary.startup_screen[-2:] == ("[0] 新的开始", "[1] 载入存档")


def test_real_project_startup_screen_uses_gamebase_like_emuera_log() -> None:
    project = _load_real_project()
    summary = _load_real_log()
    runtime = MiniRuntime(project)

    runtime.run("__TITLE__")

    text_lines = runtime.console.visible_text().splitlines()
    assert runtime.state.waiting_reason == "startup"
    assert "Erav" in text_lines
    assert "1.07" in text_lines
    assert text_lines[-2:] == list(summary.startup_screen[-2:])


def test_real_project_eventfirst_reaches_name_confirmation_after_normal_input() -> None:
    project = _load_real_project()
    runtime = MiniRuntime(project)

    runtime.run("EVENTFIRST")
    assert runtime.state.waiting_reason == "continue"
    runtime.resume()

    first_actions = _action_ids(runtime)
    assert first_actions == [0, 1, 9]

    runtime.resume(1)

    assert runtime.state.waiting_for_input
    assert _action_ids(runtime)[-6:] == [1, 2, 3, 4, 5, 0]
    text = runtime.console.visible_text()
    assert "主人公" in text
    assert "宫间" in text
    assert "响也" in text
    assert "ignored command=PRINTPLAINFORM" not in runtime.trace
    assert "ignored command=CALLNAME:0" not in runtime.trace


def test_real_project_name_decision_advances_to_next_prompt() -> None:
    project = _load_real_project()
    runtime = MiniRuntime(project)

    runtime.run("__TITLE__")
    runtime.resume(0)
    assert runtime.state.waiting_reason == "continue"
    runtime.resume()
    runtime.resume(1)
    runtime.resume(0)

    text = runtime.console.visible_text()
    assert runtime.state.waiting_for_input
    assert "寝取机能要开启吗？" in text
    assert "请重新输入0后回车确认" not in text
    assert _action_ids(runtime)[-3:] == [0, 1, 2]


def _action_ids(runtime: MiniRuntime) -> list[int]:
    return [
        int(event.choice_id)
        for event in runtime.console.to_events()
        if event.channel is OutputChannel.ACTIONS
        and event.kind is OutputKind.ACTION
        and event.choice_id is not None
    ]
