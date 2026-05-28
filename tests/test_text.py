from eraplay.text import decode_text


def test_decode_utf8_cjk_text() -> None:
    decoded = decode_text("通常業務，患者請進！".encode("utf-8"))

    assert decoded.text == "通常業務，患者請進！"
    assert decoded.encoding == "utf-8"
    assert decoded.used_fallback is False


def test_decode_cp932_japanese_fallback() -> None:
    decoded = decode_text("通常業務".encode("cp932"))

    assert decoded.text == "通常業務"
    assert decoded.encoding == "cp932"
    assert decoded.used_fallback is True


def test_decode_cp950_traditional_chinese_fallback() -> None:
    decoded = decode_text("患者請進".encode("cp950"), preferred_encoding="cp950")

    assert decoded.text == "患者請進"
    assert decoded.encoding == "cp950"
    assert decoded.used_fallback is False


def test_decode_cp936_simplified_chinese_with_preferred_encoding() -> None:
    decoded = decode_text("患者请进".encode("cp936"), preferred_encoding="cp936")

    assert decoded.text == "患者请进"
    assert decoded.encoding == "cp936"
    assert decoded.used_fallback is False
