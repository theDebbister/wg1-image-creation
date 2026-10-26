# Japanese kinsoku rules: the shared CJK punctuation (languages/cjk.py) plus the
# additions that only apply to Japanese (small kana, iteration marks, prolonged
# sound mark, wave dash). Kept as the Japanese-specific entry point; the generic
# renderer selects rules per language via languages.cjk.rules_for.

from languages.cjk import (
    COMMON_CANNOT_START,
    COMMON_CANNOT_END,
    JAPANESE_CANNOT_START,
    kinsoku_carry_count as _kinsoku_carry_count,
)

CANNOT_START = COMMON_CANNOT_START | JAPANESE_CANNOT_START
CANNOT_END = COMMON_CANNOT_END


def kinsoku_carry_count(prev_chars: list[str], next_char: str | None) -> int:
    """Japanese kinsoku carry rule (see languages.cjk.kinsoku_carry_count)."""
    return _kinsoku_carry_count(prev_chars, next_char, (CANNOT_START, CANNOT_END))
