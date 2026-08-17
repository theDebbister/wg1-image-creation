from __future__ import annotations
import unicodedata

from PIL import Image, ImageDraw


def _reverse_latin_runs_in_mixed_word(word: str) -> str:
    """Reverse each Latin/numeric run within a Hebrew+Latin mixed word.

    In char-by-char RTL rendering, a Latin substring like 'DNA' would appear backwards
    ('AND') unless its characters are pre-reversed. This function handles words that
    contain both Hebrew and Latin/numeric characters (e.g. 'ה-DNA', 'ב-23', 'ה-34-18').

    A 'Latin run' is a maximal sequence of ASCII alphanumeric characters, allowing
    ASCII punctuation (e.g. hyphen, comma) to be included when they appear between
    two alphanumeric characters — so '34-18' and '15,000' each reverse as one unit.
    Trailing punctuation (e.g. the comma in '1722,') is excluded from the run.
    """
    chars = list(word)
    i = 0
    while i < len(chars):
        if ord(chars[i]) < 128 and chars[i].isalnum():
            j = i + 1
            while j < len(chars):
                c = chars[j]
                if ord(c) < 128 and c.isalnum():
                    j += 1
                elif (ord(c) < 128 and not c.isspace()
                        and j + 1 < len(chars)
                        and ord(chars[j + 1]) < 128 and chars[j + 1].isalnum()):
                    # ASCII connector (hyphen, comma, …) between two alphanumeric chars:
                    # include it in the run so '34-18' and '15,000' reverse as units.
                    j += 1
                else:
                    break
            chars[i:j] = chars[i:j][::-1]
            i = j
        else:
            i += 1
    return ''.join(chars)


# Punctuation that can wrap an embedded LTR run inside Hebrew text, e.g. the '(' in
# '(238,900' or the trailing ',' in 'B12,'. This punctuation resolves to RTL direction
# (it belongs to the Hebrew sentence flow, not the embedded run) and must therefore be
# kept out of the run's character reversal, or it ends up mirrored to the wrong side.
LEADING_RUN_PUNCT = '([\''
TRAILING_RUN_PUNCT = ')],.;:\'?'


def reorder_ltr_runs(words: list) -> list:
    """Prepare LTR (Latin) word runs in a Hebrew paragraph for char-by-char RTL rendering.

    Hebrew text is drawn character-by-character right-to-left. For Latin characters
    drawn in RTL order to appear visually correct (left-to-right), each Latin word's
    characters must be reversed before rendering. Multi-word Latin runs also need their
    word order reversed, so the entire phrase reads correctly after RTL placement.

    Punctuation wrapping the run (e.g. '(238,900', 'B12,') is detached before the
    reversal and re-attached, un-reversed, to the outer edge of the run afterwards —
    otherwise it gets swept into the reversal and ends up on the wrong side.

    For words that mix Hebrew and Latin characters (e.g. 'ה-DNA', 'ב-23', 'ש-MultiplEYE'),
    the Latin/numeric runs within the word are reversed in place. A mixed word directly
    touching an LTR run (e.g. 'ה-British' next to 'Medical Journal') is treated as part
    of that run rather than an isolated island, so the whole phrase is repositioned as
    one unit; a mixed word with no adjacent LTR word (e.g. a lone 'ה-DNA') is left alone.
    """
    def is_ltr_word(w):
        # treat word as LTR if it has ASCII letters or digits but no Hebrew characters
        has_hebrew = any('֐' <= c <= '׿' for c in w)
        has_ascii = any(ord(c) < 128 and c.isalnum() for c in w)
        return has_ascii and not has_hebrew

    def is_mixed_word(w):
        has_hebrew = any('֐' <= c <= '׿' for c in w)
        has_ascii = any(ord(c) < 128 and c.isalnum() for c in w)
        return has_hebrew and has_ascii

    def is_self_bracketed(w):
        # a token that already wraps its own '(...)', e.g. a citation code like
        # '(2011/c372/08)'. Such a token is a complete unit on its own and must not be
        # merged into a run with a neighbouring LTR word (e.g. a bare year right before
        # it, '2011 (2011/c372/08)') — merging would swap their order and reattach the
        # closing paren to the wrong token.
        return len(w) >= 2 and w[0] == '(' and w[-1] == ')'

    i = 0
    while i < len(words):
        if is_ltr_word(words[i]) or is_mixed_word(words[i]):
            j = i + 1
            if not is_self_bracketed(words[i]):
                while (j < len(words) and (is_ltr_word(words[j]) or is_mixed_word(words[j]))
                       and not is_self_bracketed(words[j])):
                    j += 1

            if not any(is_ltr_word(w) for w in words[i:j]):
                # a mixed word (or run of mixed words) with no pure-LTR neighbour:
                # not an embedded English phrase, handle each in place as before
                for k in range(i, j):
                    words[k] = _reverse_latin_runs_in_mixed_word(words[k])
                i = j
                continue

            leading_punct = ''
            first_word = words[i]
            while first_word and first_word[0] in LEADING_RUN_PUNCT:
                leading_punct += first_word[0]
                first_word = first_word[1:]
            words[i] = first_word

            trailing_punct = ''
            last_word = words[j - 1]
            while last_word and last_word[-1] in TRAILING_RUN_PUNCT:
                trailing_punct = last_word[-1] + trailing_punct
                last_word = last_word[:-1]
            words[j - 1] = last_word

            for k in range(i, j):
                if is_mixed_word(words[k]):
                    words[k] = _reverse_latin_runs_in_mixed_word(words[k])
                else:
                    words[k] = words[k][::-1]
            if j - i > 1:
                words[i:j] = words[i:j][::-1]

            words[i] = leading_punct + words[i]
            words[j - 1] = words[j - 1] + trailing_punct

            i = j
        else:
            i += 1
    return words

# --- Manual niqqud mark positioning ----------------------------------------
# FreeMono's own OpenType mark-attachment data is unreliable for several base
# letters: dagesh renders completely invisible for א ו ז י פ ש when placed via
# the font's built-in combining-mark shaping (verified letter-by-letter,
# confirmed against real stimulus text). Rather than depend on the font to
# position combining marks, we draw the base letter and each mark as separate
# glyphs, positioned against the base letter's own measured ink extent. This
# sidesteps the font's mark-attachment bug entirely and behaves identically
# for every letter.

_MARK_INSIDE = {'ּ'}  # dagesh / mapiq: centered inside the base letter
_MARK_ABOVE = {'ֹ', 'ֺ', 'ֿ'}  # holam, holam haserah for vav, rafe
_MARK_ABOVE_RIGHT = {'ׁ'}  # shin dot
_MARK_ABOVE_LEFT = {'ׂ'}  # sin dot
# Everything else in the Hebrew points block (sheva through qubuts, meteg)
# sits below the letter. Qamats qatan (05C7) has no glyph at all in this font;
# substitute the ordinary qamats, which occupies the same below-letter
# position and is visually near-identical -- only the qatan/gadol distinction
# (both pronounced as vowel variants of qamats) is lost.
_QAMATS_QATAN = 'ׇ'
_QAMATS = 'ָ'

_GAP_PX_FRACTION = 0.04  # small visual gap between a mark and the letter it attaches to

_ink_bbox_cache: dict[tuple[int, str], tuple[int, int, int, int] | None] = {}
_basic_font_cache: dict[tuple[str, int], object] = {}


def is_combining_mark(char: str) -> bool:
    """True for a Hebrew niqqud/cantillation character that attaches to the
    previous base letter rather than occupying a cell of its own."""
    return unicodedata.combining(char) != 0


def _basic_font(font):
    """Return a Layout.BASIC variant of `font` (same file + size), cached.

    Drawing a lone combining mark through the font's default (raqm) layout makes
    HarfBuzz insert an automatic dotted-circle placeholder, since a mark with no
    base character is treated as ill-formed text. Layout.BASIC does plain glyph
    lookup with no complex-script shaping, so it draws exactly the mark's own
    glyph with no substitution. Used only for measuring and drawing the mark
    itself (see mark_draw_position / draw_mark) -- the base letter is drawn
    exactly as every other language draws its characters, with the font object
    the caller already has.
    """
    key = (font.path, font.size)
    cached = _basic_font_cache.get(key)
    if cached is None:
        from PIL import ImageFont
        cached = ImageFont.truetype(font.path, font.size, layout_engine=ImageFont.Layout.BASIC)
        _basic_font_cache[key] = cached
    return cached


def _ink_bbox(font, char: str) -> tuple[int, int, int, int] | None:
    """Return the (left, top, right, bottom) ink extent of one character drawn in
    isolation with `font`, relative to its own anchor='la' draw point. None if the
    character renders no ink (e.g. a space). Cached per (font identity, character):
    a given font+size renders any single character identically every time.
    """
    key = (id(font), char)
    if key in _ink_bbox_cache:
        return _ink_bbox_cache[key]
    pad = font.size
    img = Image.new('L', (font.size * 3, font.size * 3), 0)
    draw = ImageDraw.Draw(img)
    draw.text((pad, pad), char, font=font, fill=255, anchor='la')
    bbox = img.getbbox()
    if bbox is not None:
        bbox = (bbox[0] - pad, bbox[1] - pad, bbox[2] - pad, bbox[3] - pad)
    _ink_bbox_cache[key] = bbox
    return bbox


def draw_mark(draw, mark: str, base_char: str, base_x: int, base_y: int, font, fill) -> None:
    """Draw one niqqud mark positioned against a base letter that was already
    drawn at (base_x, base_y) with anchor='la' — used in place of the plain
    draw.text() call that other languages use, only for characters where
    is_combining_mark() is True. Everything else in the render loop (character
    splitting, per-character AOI boxes, advancing the cursor) is unchanged from
    the other-language path; this only replaces how one specific glyph gets
    drawn, using plain pixel measurements against the base letter's ink rather
    than the font's own (unreliable, see module docstring above) combining-mark
    positioning.
    """
    font = _basic_font(font)
    draw_mark_char = _QAMATS if mark == _QAMATS_QATAN else mark

    base_bbox = _ink_bbox(font, base_char)
    mark_bbox = _ink_bbox(font, draw_mark_char)
    if base_bbox is None or mark_bbox is None:
        return
    base_left, base_top, base_right, base_bottom = base_bbox
    base_cx = (base_left + base_right) / 2
    gap = font.size * _GAP_PX_FRACTION

    m_left, m_top, m_right, m_bottom = mark_bbox
    m_w = m_right - m_left
    m_h = m_bottom - m_top

    if draw_mark_char in _MARK_INSIDE:
        target_x = base_cx - m_w / 2
        target_y = (base_top + base_bottom) / 2 - m_h / 2
    elif draw_mark_char in _MARK_ABOVE:
        target_x = base_cx - m_w / 2
        target_y = base_top - m_h - gap
    elif draw_mark_char in _MARK_ABOVE_RIGHT:
        target_x = base_right - m_w
        target_y = base_top - m_h - gap
    elif draw_mark_char in _MARK_ABOVE_LEFT:
        target_x = base_left
        target_y = base_top - m_h - gap
    else:
        target_x = base_cx - m_w / 2
        target_y = base_bottom + gap

    draw_x = base_x + (target_x - m_left)
    draw_y = base_y + (target_y - m_top)
    draw.text((draw_x, draw_y), draw_mark_char, font=font, fill=fill, anchor='la')


def merge_prefix_gap(words: list) -> list:
    """Collapse the space after a standalone 'ה-' token into the word next to it.

    Hardcoded for the 'ה-British Medical Journal' occurrences (see the
    stimulus_id 10 / question_id 10212 fixes in text_to_picture.py): splitting
    'ה-' off with a space fixes the word order (reorder_ltr_runs reverses a
    run led by a mixed word incorrectly -- see that function's docstring) but
    leaves a visible inter-word gap next to whichever word 'ה-' ends up beside
    after reordering. The Unicode Bidi Algorithm's own reference output for
    this exact text has no gap there at all -- it attaches directly, with no
    space. 'ה-' only ever appears as a standalone token because of those two
    hardcoded substitutions, so this cannot affect anything else in the corpus.
    """
    for i, w in enumerate(words):
        if w == 'ה-' and i + 1 < len(words):
            words[i] = words[i] + words[i + 1]
            del words[i + 1]
            break
    return words


def fix_cost_parens(words: list) -> list:
    """Hardcoded fix for 'COST (Cooperation in Science and Technology)' (PopSci_MultiplEYE
    page_1, Hebrew only).

    reorder_ltr_runs treats 'COST (Cooperation in Science and Technology)' as one run led
    by the plain word 'COST'. The closing ')' is stripped from the run's last word
    ('Technology)') before the run's word order is reversed, then reattached to whatever
    word ends up last afterwards -- which, after reversal, is 'COST' (the run's original
    first word), not 'Technology'. This exactly matches the reference implementation of
    the Unicode Bidi Algorithm (verified against python-bidi), so it isn't a bug in the
    reordering logic -- but it renders as '(COST) Cooperation in Science and Technology'
    instead of the intended 'COST (Cooperation in Science and Technology)', which
    reviewers flagged as wrong-looking and asked to have corrected by hand.

    'TSOC)' / 'ygolonhceT' (COST / Technology, reversed) only ever appear together as a
    result of that one run, so swapping the ')' between them can't affect anything else.
    """
    if 'TSOC)' in words and 'ygolonhceT' in words:
        words[words.index('TSOC)')] = 'TSOC'
        words[words.index('ygolonhceT')] = 'ygolonhceT)'
    return words
