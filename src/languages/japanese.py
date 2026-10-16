# Minimal kinsoku sets per W3C JLREQ. These line-break rules are the same for
# horizontal and vertical Japanese; only glyph rotation/mirroring is mode-specific.
CANNOT_START = set('、。，．・：；！？…‥」』）］｝〕〉》】〙〗〞”“’」』〜ー々ヽヾゞっゃゅょゎぁぃぅぇぉヵヶァィゥェォッャュョヮヷヸヹヺ\u30fd\u30fe')
CANNOT_END = set('「『（［｛〔〈《【〘〖〝‘“「『（')


def kinsoku_carry_count(prev_chars: list[str], next_char: str | None) -> int:
    """Number of trailing units of the previous segment to carry into the next.

    Shared by horizontal line breaking and vertical column packing: moves just
    enough trailing units so the next segment does not start with a
    cannot-start character and the previous segment does not end with a
    cannot-end character. `prev_chars` are the leading characters of the
    previous segment's units in order; `next_char` is the leading character of
    the next segment.
    """
    n = len(prev_chars)
    moved = 0
    if n and next_char is not None and next_char in CANNOT_START:
        moved = 1
        while moved < n and prev_chars[n - moved] in CANNOT_START:
            moved += 1
    if moved < n and prev_chars[n - moved - 1] in CANNOT_END:
        moved += 1
    return moved
