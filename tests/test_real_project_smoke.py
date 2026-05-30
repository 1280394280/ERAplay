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


def test_real_project_can_reach_shop_menu_after_opening_choices() -> None:
    project = _load_real_project()
    runtime = MiniRuntime(project, max_steps=20000)

    runtime.run("__TITLE__")
    runtime.resume(0)
    runtime.resume()
    runtime.resume(1)
    runtime.resume(0)
    runtime.resume(0)
    runtime.resume(0)

    text = runtime.console.visible_text()
    assert runtime.state.waiting_for_input
    assert runtime.state.waiting_reason == "shop"
    assert "begin target=SHOP" in runtime.trace
    assert "shop input waiting" in runtime.trace
    assert any(action in text for action in ("[105]", "[200]", "[400]"))

    runtime.resume(0)

    assert runtime.state.waiting_for_input
    assert runtime.state.waiting_reason == "shop"


def test_real_project_shop_choice_101_enters_chara_buy_page_from_menu() -> None:
    project = _load_real_project()
    runtime = MiniRuntime(project, max_steps=20000)

    runtime.run("__TITLE__")
    runtime.resume(0)
    runtime.resume()
    runtime.resume(1)
    runtime.resume(0)
    runtime.resume(0)
    runtime.resume(0)

    assert runtime.state.waiting_reason == "shop"

    runtime.resume(101)

    text = runtime.console.visible_text()
    assert runtime.state.waiting_for_input
    assert runtime.state.waiting_reason == "input"
    assert "shop target=USERSHOP" in runtime.trace
    assert "call target=CHARA_BUY_NEW" in runtime.trace
    assert "call target=CHARA_BUY_SHOW_NEW" in runtime.trace
    assert "物色女优候补人和工作人员" in text
    assert "[100] 宫间奏 (500 P)" in text
    assert "[101] 佐佐木美乃里 (500 P)" in text
    assert "[999] - 返回" in text


def test_real_project_chara_buy_999_returns_to_shop_menu() -> None:
    project = _load_real_project()
    runtime = MiniRuntime(project, max_steps=20000)

    runtime.run("__TITLE__")
    runtime.resume(0)
    runtime.resume()
    runtime.resume(1)
    runtime.resume(0)
    runtime.resume(0)
    runtime.resume(0)
    runtime.resume(101)

    assert runtime.state.waiting_reason == "input"

    runtime.resume(999)

    text = runtime.console.visible_text()
    assert runtime.state.waiting_for_input
    assert runtime.state.waiting_reason == "shop"
    assert "call target=CHARA_BUY_AFTER" in runtime.trace
    assert "shop input waiting" in runtime.trace
    assert "物色女优候补人和工作人员" in text
    assert "[101] - 物色人才" in text
    assert "[105] - 什么都不做" in text


def test_real_project_chara_buy_page_navigation_uses_menu_inputs() -> None:
    project = _load_real_project()
    runtime = MiniRuntime(project, max_steps=30000)

    runtime.run("__TITLE__")
    runtime.resume(0)
    runtime.resume()
    runtime.resume(1)
    runtime.resume(0)
    runtime.resume(0)
    runtime.resume(0)
    runtime.resume(101)

    assert runtime.state.waiting_reason == "input"
    assert runtime.state.variables["TFLAG:100"] == 0
    assert "[100] 宫间奏 (500 P)" in runtime.console.visible_text()

    runtime.resume(9)

    page_1_text = runtime.console.visible_text()
    assert runtime.state.waiting_reason == "input"
    assert runtime.state.variables["TFLAG:100"] == 1
    assert "Page1" in page_1_text
    latest_page_1_text = page_1_text.rsplit("Page1", 1)[-1]
    assert "魔术式跳蛋" not in latest_page_1_text
    assert "[100] 宫间奏 (500 P)" not in latest_page_1_text

    runtime.resume(1)

    page_0_text = runtime.console.visible_text()
    assert runtime.state.waiting_reason == "input"
    assert runtime.state.variables["TFLAG:100"] == 0
    assert "Page0" in page_0_text
    assert "[100] 宫间奏 (500 P)" in page_0_text


def test_real_project_shop_choice_102_enters_item_shop_and_returns() -> None:
    project = _load_real_project()
    runtime = MiniRuntime(project, max_steps=30000)

    runtime.run("__TITLE__")
    runtime.resume(0)
    runtime.resume()
    runtime.resume(1)
    runtime.resume(0)
    runtime.resume(0)
    runtime.resume(0)
    runtime.resume(102)

    text = runtime.console.visible_text()
    assert runtime.state.waiting_for_input
    assert runtime.state.waiting_reason == "input"
    assert "goto target=ITEM_SHOP" in runtime.trace
    assert "call target=SALEITEM_CHECK" in runtime.trace
    assert "item shop input waiting" in runtime.trace
    assert "成人商店『NIGHT LOVE STORE』" in text
    assert "拥有的物品： 摄像机(1)" in text
    assert "[0] 跳蛋($200)" in text
    assert "[1] 按摩棒($500)" in text
    assert "[6] 摄像机" not in text
    assert "[999] - 返回" in text

    runtime.resume(999)

    returned_text = runtime.console.visible_text()
    assert runtime.state.waiting_for_input
    assert runtime.state.waiting_reason == "shop"
    assert runtime.state.variables["BOUGHT"] == -1
    assert "[101] - 物色人才" in returned_text
    assert "[102] - 成人商店" in returned_text


def test_real_project_item_shop_item_choice_opens_purchase_confirmation() -> None:
    project = _load_real_project()
    runtime = MiniRuntime(project, max_steps=50000)

    runtime.run("__TITLE__")
    runtime.resume(0)
    runtime.resume()
    runtime.resume(1)
    runtime.resume(0)
    runtime.resume(0)
    runtime.resume(0)
    runtime.resume(102)
    runtime.resume(0)

    text = runtime.console.visible_text()
    assert runtime.state.waiting_for_input
    assert runtime.state.waiting_reason == "input"
    assert runtime.state.variables["BOUGHT"] == 0
    assert runtime.state.variables["MONEY"] == 800
    assert runtime.state.variables["ITEM:0"] == 1
    assert "购入跳蛋是吗？" in text
    assert "[0] - 是" in text
    assert "[1] - 否" in text


def test_real_project_item_shop_cancel_purchase_restores_money_and_returns() -> None:
    project = _load_real_project()
    runtime = MiniRuntime(project, max_steps=50000)

    runtime.run("__TITLE__")
    runtime.resume(0)
    runtime.resume()
    runtime.resume(1)
    runtime.resume(0)
    runtime.resume(0)
    runtime.resume(0)
    runtime.resume(102)
    runtime.resume(0)
    runtime.resume(1)

    text = runtime.console.visible_text()
    assert runtime.state.waiting_for_input
    assert runtime.state.waiting_reason == "input"
    assert runtime.state.input_context is not None
    assert runtime.state.input_context.kind == "item_shop"
    assert runtime.state.variables["BOUGHT"] == 0
    assert runtime.state.variables["MONEY"] == 1000
    assert runtime.state.variables["ITEM:0"] == 0
    assert "所持金：1000円" in text
    assert "[0] 跳蛋($200)" in text


def test_real_project_item_shop_confirm_purchase_updates_state_and_refreshes() -> None:
    project = _load_real_project()
    runtime = MiniRuntime(project, max_steps=50000)

    runtime.run("__TITLE__")
    runtime.resume(0)
    runtime.resume()
    runtime.resume(1)
    runtime.resume(0)
    runtime.resume(0)
    runtime.resume(0)
    runtime.resume(102)
    runtime.resume(0)
    runtime.resume(0)

    purchase_text = runtime.console.visible_text()
    assert runtime.state.waiting_for_input
    assert runtime.state.waiting_reason == "continue"
    assert runtime.state.variables["MONEY"] == 800
    assert runtime.state.variables["ITEM:0"] == 1
    assert "《跳蛋购入了》" in purchase_text

    runtime.resume()

    refreshed_text = runtime.console.visible_text()
    latest_shop = refreshed_text.rsplit("成人商店", 1)[-1]
    assert runtime.state.waiting_for_input
    assert runtime.state.waiting_reason == "input"
    assert runtime.state.input_context is not None
    assert runtime.state.input_context.kind == "item_shop"
    assert "所持金：800円" in latest_shop
    assert "拥有的物品： 跳蛋(1) 摄像机(1)" in latest_shop
    assert "[0] 跳蛋($200)" not in latest_shop
    assert "[1] 按摩棒($500)" in latest_shop


def _action_ids(runtime: MiniRuntime) -> list[int]:
    return [
        int(event.choice_id)
        for event in runtime.console.to_events()
        if event.channel is OutputChannel.ACTIONS
        and event.kind is OutputKind.ACTION
        and event.choice_id is not None
    ]
