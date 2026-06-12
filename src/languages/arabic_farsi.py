from __future__ import annotations

import re
import unicodedata

import uharfbuzz as hb  # noqa: F401 — required by Pillow's libraqm RTL backend
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import ImageFont

import image_config

# Unicode BiDi mirroring pairs: visually swapped in RTL context.
BIDI_MIRROR = {
    '(': ')', ')': '(', '[': ']', ']': '[', '{': '}', '}': '{',
    '<': '>', '>': '<', '«': '»', '»': '«', '‹': '›', '›': '‹',
}

# Arabic characters that only join to the right and never connect leftward.
# ر/ز do not overflow when preceded by one of these.
RIGHT_JOINING_ONLY = frozenset('اآأإؤةدذرزوى')

# Characters whose glyphs visually overflow their left cell boundary,
# and the number of pixels to extend the AOI box leftward.
ALWAYS_OVERFLOW = {'ص': 1, 'ض': 1, 'س': 1, 'ش': 1}


def rtl_display(text: str) -> str:
    """Reshape and BiDi-order text for RTL languages so PIL renders it correctly."""
    if image_config.LANGUAGE not in ('fa', 'ar'):
        return text
    return get_display(arabic_reshaper.reshape(text))


def is_arabic_codepoint(cp: int) -> bool:
    """Return True if the Unicode codepoint belongs to an Arabic script block."""
    return (
        0x0600 <= cp <= 0x06FF or
        0x0750 <= cp <= 0x077F or
        0x08A0 <= cp <= 0x08FF or
        0xFB50 <= cp <= 0xFDFF or
        0xFE70 <= cp <= 0xFEFF
    )


def normalize_quote_pairing(words: list, quote_open: bool) -> tuple:
    """Normalize « / » so the first occurrence on a page is the opening mark and the
    next is the closing mark, alternating.

    Regardless of which character appears in the source text, after normalization:
      - opening marks are «  (get_display with base_dir='R' renders this as » on the right)
      - closing marks are »  (rendered as « on the left)

    quote_open: state carried in from the previous paragraph on the same page.
    Returns (modified_words, updated_quote_open).
    """
    double_quotes = frozenset('«»')
    single_quotes = frozenset('‹›')

    result = []
    for word in words:
        if not any(c in double_quotes or c in single_quotes for c in word):
            result.append(word)
            continue
        chars = []
        for char in word:
            if char in double_quotes:
                if not quote_open:
                    chars.append('«')
                    quote_open = True
                else:
                    chars.append('»')
                    quote_open = False
            else:
                chars.append(char)
        result.append(''.join(chars))
    return result, quote_open


def reverse_ltr_runs(words: list) -> list:
    """Reverse consecutive LTR (Latin) word runs within an RTL paragraph word list.

    Multi-word English phrases embedded in RTL text must be reversed at paragraph
    level so the complete run reads left-to-right after the BiDi algorithm reverses
    the whole paragraph.  Closing brackets on the last word are moved (mirrored) to
    the front of the first word so they land on the left (visual end) after reversal.
    Opening brackets on the first word are moved to the end of the last word so they
    land on the right (visual start) after reversal.
    """
    def has_latin_alpha(w):
        return any(c.isalpha() and ord(c) < 128 for c in w)

    i = 0
    while i < len(words):
        if has_latin_alpha(words[i]):
            # find the end of this LTR run
            j = i + 1
            while j < len(words) and has_latin_alpha(words[j]):
                j += 1
            if j - i > 1:
                last_word = words[j - 1]
                trailing_sent_punct = ''
                while last_word and last_word[-1] == '.':
                    trailing_sent_punct = last_word[-1] + trailing_sent_punct
                    last_word = last_word[:-1]
                last_word_core = last_word.rstrip(')]}>»›')
                closing_bracket = last_word[len(last_word_core):]

                # Extract any opening bracket from the first word (FA/other only).
                # It will be appended to the last word so that after reversal it
                # ends up rightmost — the correct side for an opening mark in RTL.
                first_word = words[i]
                first_core = first_word.lstrip('([{<«‹')
                opening_bracket = first_word[:len(first_word) - len(first_core)]

                if closing_bracket:
                    mirrored_closing = ''.join(BIDI_MIRROR.get(c, c) for c in closing_bracket)
                    if image_config.LANGUAGE != 'ar' or first_word[0] in '([{<«‹':
                        words[j - 1] = last_word_core + trailing_sent_punct
                        if image_config.LANGUAGE == 'ar':
                            # AR: prepend to full first word (including its opening bracket);
                            # the AR-specific block below then separates them.
                            words[i] = mirrored_closing + first_word
                            fw = words[i]
                            fw_core = fw.lstrip('([{<«‹')
                            fw_prefix = fw[:len(fw) - len(fw_core)]
                            if len(fw_prefix) > len(mirrored_closing):
                                extra_prefix = fw_prefix[len(mirrored_closing):]
                                mirrored_extra = ''.join(BIDI_MIRROR.get(c, c) for c in extra_prefix)
                                words[i] = mirrored_closing + fw_core
                                words[j - 1] = last_word_core + mirrored_extra + trailing_sent_punct
                        else:
                            # FA/other: strip the opening bracket from the first word here;
                            # it is re-attached to the last word below.
                            words[i] = mirrored_closing + first_core
                elif opening_bracket and image_config.LANGUAGE != 'ar':
                    # No closing bracket but opening bracket present: strip it from first word.
                    words[i] = first_core

                # FA/other: append the opening bracket to the last word (before reversal)
                # so it appears at the right end of the run after reversal.
                if image_config.LANGUAGE != 'ar' and opening_bracket:
                    words[j - 1] = words[j - 1] + opening_bracket

                words[i:j] = words[i:j][::-1]
            i = j
        else:
            i += 1
    return words


def _prepare_ltr_word(word: str, is_punct_only: bool) -> str:
    """Prepare an LTR word embedded in RTL text for rendering.

    Trailing closing brackets are moved to the front and mirrored so they
    appear on the correct (left) side in the RTL visual stream.
    """
    if is_punct_only:
        return word

    w = word
    trailing_sent_punct = ''
    while w and w[-1] == '.':
        trailing_sent_punct = w[-1] + trailing_sent_punct
        w = w[:-1]
    word_core = w.rstrip(')]}>»›')
    bracket_suffix = w[len(word_core):]

    if bracket_suffix:
        mirrored_bracket = ''.join(BIDI_MIRROR.get(c, c) for c in bracket_suffix)
        if image_config.LANGUAGE == 'ar':
            # AR only: only move the bracket when this word also has a matching
            # opening bracket (e.g. "(multilingualism)").  Without one, keep as-is.
            core_without_prefix = word_core.lstrip('([{<«‹')
            opening_bracket = word_core[:len(word_core) - len(core_without_prefix)]
            if opening_bracket:
                mirrored_opening = ''.join(BIDI_MIRROR.get(c, c) for c in opening_bracket)
                return trailing_sent_punct + mirrored_bracket + core_without_prefix + mirrored_opening
            else:
                return word
        else:
            # FA: if the word already has a matching opening bracket (e.g. "(ECTS)"),
            # prepending a mirrored bracket would produce "((ECTS" — render as-is.
            if word_core and BIDI_MIRROR.get(bracket_suffix[0]) == word_core[0]:
                return word
            else:
                return trailing_sent_punct + mirrored_bracket + word_core
    else:
        core = word.rstrip(')]}>»›')
        suffix = word[len(core):]
        mirrored_suffix = ''.join(BIDI_MIRROR.get(c, c) for c in suffix)
        return mirrored_suffix + core if suffix else word


def render_rtl_word(
    draw, word, word_number, words_in_line, x_word, anchor_y_px,
    font, fontsize, line_height, aoi_idx, char_idx_in_line,
    line_idx, image_short_name, word_idx, word_idx_in_line,
    draw_aoi, aois,
):
    """Render one word of RTL (Arabic/Farsi) text and collect AOI entries.

    Returns (current_x, aoi_idx, char_idx_in_line, word_idx_in_line, chars_added, word_stripped).
    current_x is the updated right-edge position for the next word (moves leftward).
    """
    word_stripped = word.strip()
    reshaped_word = arabic_reshaper.reshape(word_stripped)  # noqa: F841 — kept for ligature info
    fallback_font = ImageFont.truetype(
        str(image_config.REPO_ROOT / 'fonts/JetBrainsMono-Regular.ttf'), fontsize
    )

    aoi_y = anchor_y_px
    current_x = x_word  # right edge; moves leftward as we place characters
    chars_added = 0

    # Space between words: placed to the RIGHT of this word (before its characters
    # in RTL order) so no trailing space appears at the left edge of a line.
    if word_number != 0:
        space_width = int(draw.textlength(' ', font=font))
        if space_width == 0:
            space_width = max(1, int(font.getbbox(' ')[2]))
        space_x = current_x - space_width
        aoi_space = [
            aoi_idx, ' ', space_x, aoi_y,
            space_width, line_height,
            char_idx_in_line, line_idx, image_short_name, word_idx, word_idx_in_line,
        ]
        if draw_aoi:
            draw.rectangle(
                (space_x, aoi_y, space_x + space_width, aoi_y + line_height),
                outline='red', width=1,
            )
        aois.append(aoi_space)
        aoi_idx += 1
        char_idx_in_line += 1
        current_x -= space_width

    # Decimal digits (category 'Nd') in Arabic/Farsi are treated as LTR.
    has_arabic_chars = any(
        is_arabic_codepoint(ord(c)) and unicodedata.category(c) != 'Nd'
        for c in word_stripped
        if unicodedata.category(c) not in ('Cf', 'Cc')
    )
    # Pure punctuation/digit words (no Arabic script, no alphabetic chars)
    # need BiDi mirroring when placed in the RTL stream.
    is_punct_only = not has_arabic_chars and not any(c.isalpha() for c in word_stripped)

    if not has_arabic_chars:
        # ── LTR word inside RTL text (e.g. "MultiplEYE") ──────────────────────
        render_word_ltr = _prepare_ltr_word(word_stripped, is_punct_only)

        # Split on hyphens so each part can be drawn with the right font.
        # Hyphens use fallback_font (KawkabMono renders '-' as '_').
        ltr_segments = re.split(r'(-)', render_word_ltr)

        # Baseline alignment: shift fallback_font so its baseline matches the
        # primary font (the two fonts have different ascent metrics).
        primary_ascent = font.getmetrics()[0]
        fallback_ascent = fallback_font.getmetrics()[0]
        fallback_y_anchor = anchor_y_px + (primary_ascent - fallback_ascent)

        # Compute total width first so we know where to start the left edge.
        total_ltr_width = 0
        for seg in ltr_segments:
            if not seg:
                continue
            seg_font = fallback_font if seg == '-' else font
            seg_w = int(draw.textlength(seg, font=seg_font))
            if seg_w == 0:
                seg_w = int(seg_font.getbbox(seg)[2])
            total_ltr_width += seg_w

        char_x = current_x - total_ltr_width  # left edge; moves rightward
        for seg in ltr_segments:
            if not seg:
                continue
            seg_font = fallback_font if seg == '-' else font
            seg_y = fallback_y_anchor if seg_font is fallback_font else anchor_y_px
            # Punct-only words: use BiDi algorithm so digits and punctuation land
            # in the correct visual order (e.g. '۱.' → '.۱' so '۱' is rightmost).
            shaped_seg = get_display(arabic_reshaper.reshape(seg), base_dir='R') if is_punct_only else seg
            draw.text(
                (char_x, seg_y), shaped_seg,
                fill=image_config.TEXT_COLOR, font=seg_font, anchor='la',
            )
            for char in (shaped_seg if is_punct_only else seg):
                if unicodedata.category(char) in ('Cf', 'Cc'):
                    continue
                char_w = int(draw.textlength(char, font=seg_font))
                if char_w == 0:
                    char_w = int(seg_font.getbbox(char)[2])
                if char_w == 0:
                    continue
                aoi_letter = [
                    aoi_idx, char, char_x, aoi_y,
                    char_w, line_height,
                    char_idx_in_line, line_idx, image_short_name, word_idx, word_idx_in_line,
                ]
                if draw_aoi:
                    draw.rectangle(
                        (char_x, aoi_y, char_x + char_w, aoi_y + line_height),
                        outline='red', width=1,
                    )
                aois.append(aoi_letter)
                aoi_idx += 1
                char_idx_in_line += 1
                word_idx_in_line += 1
                chars_added += 1
                char_x += char_w
        current_x -= total_ltr_width

    else:
        # ── Arabic/Farsi word ─────────────────────────────────────────────────
        # Use Pillow's libraqm backend (direction='rtl') so KawkabMono's OpenType
        # GSUB rules are applied.  arabic_reshaper is NOT used for rendering —
        # its presentation-form codepoints map to notdef in KawkabMono's cmap.
        #
        # Trailing closing brackets are stripped, mirrored, and placed to the LEFT
        # of the word where the reader encounters them last in RTL.
        word_core = word_stripped.rstrip(')]}>»›')
        trailing_bracket = word_stripped[len(word_core):]
        if trailing_bracket:
            word_stripped = word_core
            reshaped_word = arabic_reshaper.reshape(word_stripped)  # noqa: F841

        render_word = word_stripped
        raqm_opts = {'direction': 'rtl', 'language': image_config.LANGUAGE}

        word_render_width = round(draw.textlength(render_word, font=font, **raqm_opts))
        if word_render_width == 0:
            word_render_width = round(font.getbbox(render_word)[2])

        draw.text(
            (current_x - word_render_width, anchor_y_px), render_word,
            fill=image_config.TEXT_COLOR, font=font, anchor='la', **raqm_opts,
        )

        # AOI: each original visible character gets a box of the standard monospaced
        # width (std_char_w).  When a ligature compresses two chars into one glyph
        # (e.g. ل + ا → لا), the actual advance is less than n_chars × std_char_w;
        # the deficit is recorded as a '_LIGA_SPACE_' AOI.  An '_EXTRA_SPACE_' AOI
        # is added when the word is wider than expected.
        visible_chars = [c for c in word_stripped if unicodedata.category(c) not in ('Cf', 'Cc')]
        n_visible = len(visible_chars)
        if n_visible > 0:
            std_char_w = round(draw.textlength('م', font=font, **raqm_opts))
            if std_char_w == 0:
                std_char_w = max(1, round(font.getbbox('م')[2]))

            expected_width = n_visible * std_char_w
            width_diff = word_render_width - expected_width  # >0: extra; <0: ligature gap

            aoi_x_right = current_x
            prev_left_overflow = 0
            for vi, char in enumerate(visible_chars):
                aoi_x = aoi_x_right - std_char_w
                left_overflow = ALWAYS_OVERFLOW.get(char, 0)

                if char in ('ر', 'ز'):
                    # Overflow only when connected to the right (bilateral connector).
                    prev_char = visible_chars[vi - 1] if vi > 0 else None
                    if prev_char is not None and prev_char not in RIGHT_JOINING_ONLY:
                        left_overflow = 4
                elif char == 'ك':
                    # The كا combination causes ك to overflow leftward.
                    next_char = visible_chars[vi + 1] if vi < len(visible_chars) - 1 else None
                    if next_char in ('ا', 'آ', 'أ', 'إ'):
                        left_overflow = 6

                box_x = aoi_x - left_overflow
                box_right = aoi_x_right - prev_left_overflow
                box_w = box_right - box_x
                aoi_letter = [
                    aoi_idx, char, box_x, aoi_y,
                    box_w, line_height,
                    char_idx_in_line, line_idx, image_short_name, word_idx, word_idx_in_line,
                ]
                if draw_aoi:
                    draw.rectangle(
                        (box_x, aoi_y, box_right, aoi_y + line_height),
                        outline='red', width=1,
                    )
                aois.append(aoi_letter)
                aoi_idx += 1
                char_idx_in_line += 1
                word_idx_in_line += 1
                chars_added += 1
                prev_left_overflow = left_overflow
                aoi_x_right -= std_char_w

            if width_diff != 0 and word_number != len(words_in_line) - 1:
                space_label = '_EXTRA_SPACE_' if width_diff > 0 else '_LIGA_SPACE_'
                space_w = abs(width_diff)
                space_x = current_x - word_render_width if width_diff > 0 else current_x - expected_width
                space_aoi = [
                    aoi_idx, space_label, space_x, aoi_y,
                    space_w, line_height,
                    char_idx_in_line, line_idx, image_short_name, word_idx, word_idx_in_line,
                ]
                if draw_aoi:
                    draw.rectangle(
                        (space_x, aoi_y, space_x + space_w, aoi_y + line_height),
                        outline='red', width=1,
                    )
                aois.append(space_aoi)
                aoi_idx += 1
                char_idx_in_line += 1
                chars_added += 1
        current_x -= word_render_width

        # Draw the mirrored trailing bracket to the left of the Arabic word.
        if trailing_bracket:
            mirrored_bracket = ''.join(BIDI_MIRROR.get(c, c) for c in trailing_bracket)
            bracket_width = round(draw.textlength(mirrored_bracket, font=font))
            if bracket_width == 0:
                bracket_width = max(1, round(font.getbbox(mirrored_bracket)[2]))
            draw.text(
                (current_x - bracket_width, anchor_y_px), mirrored_bracket,
                fill=image_config.TEXT_COLOR, font=font, anchor='la',
            )
            bracket_x = current_x - bracket_width
            for bracket_char in mirrored_bracket:
                if unicodedata.category(bracket_char) in ('Cf', 'Cc'):
                    continue
                bracket_char_w = round(draw.textlength(bracket_char, font=font))
                if bracket_char_w == 0:
                    bracket_char_w = max(1, round(font.getbbox(bracket_char)[2]))
                aois.append([
                    aoi_idx, bracket_char, bracket_x, aoi_y, bracket_char_w, line_height,
                    char_idx_in_line, line_idx, image_short_name,
                    word_idx, word_idx_in_line,
                ])
                if draw_aoi:
                    draw.rectangle(
                        (bracket_x, aoi_y, bracket_x + bracket_char_w, aoi_y + line_height),
                        outline='red', width=1,
                    )
                aoi_idx += 1
                char_idx_in_line += 1
                chars_added += 1
                bracket_x += bracket_char_w
            current_x -= bracket_width

    return current_x, aoi_idx, char_idx_in_line, word_idx_in_line, chars_added, word_stripped