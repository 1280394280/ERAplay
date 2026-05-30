import os
from pathlib import Path

import pytest

from eraplay.compat import build_compatibility_report
from eraplay.project import load_project
from eraplay.runtime import MiniRuntime
from eraplay.ui import OutputChannel, OutputKind

DEFAULT_REAL_PROJECT = Path(r"D:\新建文件夹\ERA\emuera\erAV-master")


def _real_project_path() -> Path:
    return Path(os.environ.get("ERAPLAY_REAL_PROJECT", DEFAULT_REAL_PROJECT))


def _load_real_project():
    path = _real_project_path()
    if not path.exists():
        pytest.skip(f"real ERA project not found: {path}")
    return load_project(path)


def test_real_project_loads_erav_data_summary() -> None:
    project = _load_real_project()
    report = build_compatibility_report(project)

    assert len(project.erb_files) == 468
    assert len(project.erh_files) == 3
    assert len(project.csv_files) == 133
    assert project.data.variable_sizes["FLAG"] == 10000
    assert project.data.variable_sizes["ITEM"] == 1000
    assert len(project.data.chara_files) == 120
    assert report.to_dict(top=5)["data"]["name_tables"]["TALENTNAME"] == 263


def test_real_project_eventfirst_reaches_name_confirmation_after_normal_input() -> None:
    project = _load_real_project()
    runtime = MiniRuntime(project)

    runtime.run("EVENTFIRST")
    first_actions = _action_ids(runtime)
    assert first_actions == [0, 1, 9]

    runtime.resume(1)

    assert runtime.state.waiting_for_input
    assert _action_ids(runtime)[-6:] == [1, 2, 3, 4, 5, 0]
    assert "主人公" in runtime.console.visible_text()


def _action_ids(runtime: MiniRuntime) -> list[int]:
    return [
        int(event.choice_id)
        for event in runtime.console.to_events()
        if event.channel is OutputChannel.ACTIONS
        and event.kind is OutputKind.ACTION
        and event.choice_id is not None
    ]
