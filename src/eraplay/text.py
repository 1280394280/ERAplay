from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_FALLBACK_ENCODINGS = ("utf-8", "cp932", "cp950", "cp936")


@dataclass(frozen=True)
class DecodedText:
    text: str
    encoding: str
    used_fallback: bool = False


def decode_text(
    data: bytes,
    preferred_encoding: str | None = None,
    fallback_encodings: tuple[str, ...] = DEFAULT_FALLBACK_ENCODINGS,
) -> DecodedText:
    if preferred_encoding:
        return DecodedText(data.decode(preferred_encoding), preferred_encoding)

    bom_encoding = _detect_bom(data)
    if bom_encoding:
        return DecodedText(data.decode(bom_encoding), bom_encoding)

    errors: list[UnicodeDecodeError] = []
    for index, encoding in enumerate(fallback_encodings):
        try:
            return DecodedText(data.decode(encoding), encoding, used_fallback=index > 0)
        except UnicodeDecodeError as error:
            errors.append(error)

    if errors:
        raise errors[-1]
    raise ValueError("no fallback encodings configured")


def read_text_file(
    path: str | Path,
    preferred_encoding: str | None = None,
    fallback_encodings: tuple[str, ...] = DEFAULT_FALLBACK_ENCODINGS,
) -> DecodedText:
    return decode_text(
        Path(path).read_bytes(),
        preferred_encoding=preferred_encoding,
        fallback_encodings=fallback_encodings,
    )


def _detect_bom(data: bytes) -> str | None:
    if data.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if data.startswith(b"\xff\xfe"):
        return "utf-16-le"
    if data.startswith(b"\xfe\xff"):
        return "utf-16-be"
    return None
