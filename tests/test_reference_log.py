from pathlib import Path

from eraplay.reference_log import parse_emuera_log


def test_parse_emuera_log_summary(tmp_path: Path) -> None:
    log_path = tmp_path / "emuera.log"
    log_path.write_text(
        "\n".join(
            [
                "加载macro.ini・・・",
                "VariableSize.CSV读取中・・・",
                "Chara\\Chara0.csv读取中・・・",
                "SYSTEM\\SYSTEM_TITLE.ERB读取中・・・",
                "HoX\\HoX.ERH读取中・・・",
                "警告Lv2:SYSTEM\\SHOP_MAIN.ERB:388行:无法被解析的标示符\"Local\"",
                "非注释行:157951, 函数数量:2227, 调用次数:1184",
                "载入完毕",
                "Erav",
                "1.07",
                "[0] 新的开始",
                "[1] 载入存档",
            ]
        ),
        encoding="utf-16",
    )

    summary = parse_emuera_log(log_path)

    assert summary.encoding == "utf-16-le"
    assert summary.macro_loaded is True
    assert summary.csv_files == ("VariableSize.CSV", "Chara\\Chara0.csv")
    assert summary.erb_files == ("SYSTEM\\SYSTEM_TITLE.ERB",)
    assert summary.erh_files == ("HoX\\HoX.ERH",)
    assert summary.chara_csv_count == 1
    assert len(summary.warnings) == 1
    assert summary.non_comment_lines == 157951
    assert summary.function_count == 2227
    assert summary.call_count == 1184
    assert summary.startup_screen[-2:] == ("[0] 新的开始", "[1] 载入存档")
