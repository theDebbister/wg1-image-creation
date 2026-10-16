"""Shared CJK line/column-break (kinsoku) rules per W3C JLREQ.

Used by both the horizontal line breaker and the vertical (ttb) column packer.
`COMMON_CANNOT_START` / `COMMON_CANNOT_END` hold the punctuation that must not
start / end a line for CJK languages in general; `JAPANESE_CANNOT_START` adds
the characters only Japanese forbids there (small kana, iteration marks,
prolonged sound mark, wave dash). Language selection happens through
`rules_for`, so the generic renderer never assumes Japanese.
"""

# Languages that lay text out on a CJK grid (kana/kanji/han). Used to pick the
# character-flow and single-run branches of the renderer.
CJK_LANGUAGES = ('zh', 'yu', 'ja', 'zt')

# Punctuation that may not start a line/column (all CJK).
COMMON_CANNOT_START = set('、。，．・：；！？…‥」』）］｝〕〉》】〙〗〞”“’')
# Opening brackets that may not end a line/column (all CJK).
COMMON_CANNOT_END = set('「『（［｛〔〈《【〘〖〝‘“')

# Japanese-only additions: chōonpu, wave dash, iteration marks and small kana.
JAPANESE_CANNOT_START = set('〜ー々ヽヾゞっゃゅょゎぁぃぅぇぉヵヶァィゥェォッャュョヮヷヸヹヺ')


def is_cjk_language(language: str) -> bool:
    return language in CJK_LANGUAGES


def rules_for(language: str) -> tuple[set[str], set[str]]:
    """Return the (cannot_start, cannot_end) kinsoku sets for a language.

    Japanese adds its kana/iteration marks; every other language (including
    non-CJK ones, for which the sets are simply a no-op) uses the shared
    punctuation.
    """
    if language == 'ja':
        return COMMON_CANNOT_START | JAPANESE_CANNOT_START, COMMON_CANNOT_END
    return COMMON_CANNOT_START, COMMON_CANNOT_END


def kinsoku_carry_count(
        prev_chars: list[str],
        next_char: str | None,
        rules: tuple[set[str], set[str]],
) -> int:
    """Number of trailing units of the previous segment to carry into the next.

    Shared by horizontal line breaking and vertical column packing: moves just
    enough trailing units so the next segment does not start with a
    cannot-start character and the previous segment does not end with a
    cannot-end character. `prev_chars` are the leading characters of the
    previous segment's units in order; `next_char` is the leading character of
    the next segment; `rules` is the (cannot_start, cannot_end) pair from
    `rules_for`.
    """
    cannot_start, cannot_end = rules
    n = len(prev_chars)
    moved = 0
    if n and next_char is not None and next_char in cannot_start:
        moved = 1
        while moved < n and prev_chars[n - moved] in cannot_start:
            moved += 1
    if moved < n and prev_chars[n - moved - 1] in cannot_end:
        moved += 1
    return moved
