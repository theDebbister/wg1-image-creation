from __future__ import annotations

import json
import os
import random
import warnings
import re
from collections import OrderedDict
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm

import image_config
try:
    from src.subcorpus.aging import get_stimulus_randomization_orders
except ImportError:
    from subcorpus.aging import get_stimulus_randomization_orders
from utils import config_utils, checks
from languages import arabic_farsi, hebrew
from languages.arabic_farsi import rtl_draw_kwargs

try:
    import uharfbuzz as hb
    import freetype
    _HAS_VERTICAL = True
except Exception:
    hb = None
    freetype = None
    _HAS_VERTICAL = False

pd.options.mode.chained_assignment = None  # default='warn'

CONFIG = {}


def normalize_render_text(text: str) -> str:
    """Expand ligatures that the configured font may not contain, and replace
    control whitespace that has no glyph in the fonts (it would otherwise be
    drawn as a missing-glyph box)."""
    text = text.replace('ﬁ', 'fi')
    text = re.sub(r'[\t\r\f\v\x00-\x08\x0e-\x1f]', ' ', text)
    return text


def clean_option(text):
    """Strip leading/trailing whitespace from an answer option; a space left in
    the source would otherwise render as an empty (full-width) cell."""
    return text.strip() if isinstance(text, str) else text


# Minimal kinsoku sets for vertical ttb, per W3C JLREQ and genkoyoshi
_TTB_CANNOT_START = set('、。，．・：；！？…‥」』）］｝〕〉》】〙〗〞”“’」』〜ー々ヽヾゞっゃゅょゎぁぃぅぇぉヵヶァィゥェォッャュョヮヷヸヹヺ\u30fd\u30fe')
_TTB_CANNOT_END = set('「『（［｛〔〈《【〘〖〝‘“「『（')


def _draw_text_ttb(text: str, image: Image, fontsize: int, draw_aoi: bool = False,
                   spacing: float = image_config.LINE_SPACING, image_short_name: str = None,
                   anchor_x_px: int = None, anchor_y_px: int = None,
                   text_width_px: int = None, text_height_px: int = None, script_direction: str = 'ttb',
                   word_split_criterion: str = ' ', line_limit: int = None,
                   latin_font_path: str = None, latin_box: str = None,
                   center_in_box: bool = False):
    """Vertical ttb column renderer via uharfbuzz plus freetype.

    Layout respects genkoyoshi grid and w3.org/TR/jlreq minimal kinsoku.
    Each cell is fontsize x fontsize. Char advance is +y, column advance is -x.
    AOI boxes are the uniform cells, not ink bboxes. Optional green grid when
    image_config.DEBUG_GRID is True, for lab review.
    """
    # For ttb: default anchor is top-right, but respect caller-provided anchors (e.g. answer boxes)
    if script_direction == 'ttb':
        if anchor_x_px is None:
            # Use image.width for extended pages so page-1 stays right-aligned and overflow extends left
            anchor_x_px = image.width - image_config.MIN_MARGIN_RIGHT_PX
        if anchor_y_px is None:
            anchor_y_px = image_config.MIN_MARGIN_TOP_PX
    else:
        if anchor_x_px is None:
            anchor_x_px = image_config.ANCHOR_POINT_X_PX
        if anchor_y_px is None:
            anchor_y_px = image_config.ANCHOR_POINT_Y_PX
    # Apply Japanese vertical defaults (JetBrains tight) if not overridden
    if latin_box is None:
        latin_box = getattr(image_config, 'LATIN_BOX_TYPE', 'square')
    if latin_font_path is None:
        latin_font_path = getattr(image_config, 'LATIN_FONT_TYPE', None)

    if line_limit is None:
        if script_direction == 'ttb':
            # Width-derived column limit for vertical, not horizontal NUM_LINES_PER_PAGE
            col_adv_tmp = int(fontsize * spacing) if spacing else fontsize
            line_limit = max(1, image_config.TEXT_WIDTH_PX // col_adv_tmp)
        else:
            line_limit = image_config.NUM_LINES_PER_PAGE

    draw = ImageDraw.Draw(image)
    text = normalize_render_text(text)
    paragraphs = re.split(r'\n+', text.strip()) if text.strip() else []

    # Build flat char sequence, preserving paragraph breaks as column breaks
    chars: list[str] = []
    for pi, para in enumerate(paragraphs):
        if word_split_criterion == '':
            seq = [c for c in para]
        else:
            # for ttb with spaces, keep chars including spaces as cells
            seq = list(para)
        chars.extend(seq)
        if pi < len(paragraphs) - 1:
            chars.append('\n')

    # Remove spaces that are not meaningful for ttb, keep explicit newline markers
    # For ja the sequence is already per char, spaces would be rare
    # Keep spaces for ttb to separate western words, skip only for non-ttb
    filtered: list[str] = []
    bold_flags: list[bool] = []
    in_bold = False
    _k = 0
    while _k < len(chars):
        c = chars[_k]
        if c == ' ' and word_split_criterion == '' and script_direction != 'ttb':
            _k += 1
            continue
        if c == '*' and _k + 1 < len(chars) and chars[_k + 1] == '*':
            # **…** bold marker pair: toggle bold, emit neither star
            in_bold = not in_bold
            _k += 2
            continue
        if c == '*':
            # stray single star (never part of a ** pair): drop it
            _k += 1
            continue
        filtered.append(c)
        bold_flags.append(in_bold)
        _k += 1
    chars = filtered
    # Index (in chars) of chars inside a **…** span.
    bold_chars = {i for i, b in enumerate(bold_flags) if b}

    def _is_halfwidth_digit(c: str) -> bool:
        return '0' <= c <= '9'

    def _is_latin_alpha(c: str) -> bool:
        return ('A' <= c <= 'Z') or ('a' <= c <= 'z')

    def _is_latin_rotated(c: str) -> bool:
        # Include URL characters . / : @ # ? & = % + for single Latin token (e.g. www.example.com/path)
        return _is_latin_alpha(c) or c in "-'.:/#@?&=%+_'\""

    def _is_punct_via_pil(c: str) -> bool:
        return c in "%％"

    def _group_into_cells(seq: list[str]) -> list[list[str]]:
        # returns list of cells, each cell is list of 1 or more chars
        # For Latin (monospaced): consecutive Latin letters are grouped into one word cell,
        # rendered as a whole word but AOIs are per-character at fixed intervals
        cells: list[list[str]] = []
        i = 0
        while i < len(seq):
            if seq[i] == '\n':
                cells.append(['\n'])
                i += 1
                continue
            if seq[i] == ' ':
                cells.append([' '])
                i += 1
                continue
            if _is_latin_rotated(seq[i]):
                j = i
                while j < len(seq) and _is_latin_rotated(seq[j]):
                    j += 1
                cells.append(seq[i:j])
                i = j
                continue
            # Group a run of digits (and an immediately-following %) into one
            # atomic cell so a number is not split across two columns; each
            # digit is still rendered upright.
            if _is_halfwidth_digit(seq[i]):
                j = i
                while j < len(seq) and _is_halfwidth_digit(seq[j]):
                    j += 1
                if j < len(seq) and seq[j] in ('%', '％'):
                    j += 1
                cells.append(seq[i:j])
                i = j
                continue
            cells.append([seq[i]])
            i += 1
        return cells

    cell_seq = _group_into_cells(chars)
    # Bold flag per cell (chars inside a **…** span), aligned with cell_seq.
    cell_bold: list[bool] = []
    _ci = 0
    for _cell in cell_seq:
        cell_bold.append(any((_ci + _k) in bold_chars for _k in range(len(_cell))))
        _ci += len(_cell)
    # No automatic spacing around Latin words: only spaces present in the input
    # are rendered. Their width is decided per space below (mono half-width when
    # touching western text, full Japanese width between Japanese characters).
    # Column packing for vertical: pixel height budget, variable for western words
    # For answer boxes (ttb with box constraints) use box dimensions, not full page
    col_advance = int(fontsize * spacing) if spacing else fontsize
    if script_direction == 'ttb' and text_width_px is not None and text_height_px is not None:
        # box-constrained: width = columns, height = chars per column
        text_height_px_local = text_height_px
        max_cols = max(1, text_width_px // col_advance)
    else:
        text_height_px_local = image_config.IMAGE_HEIGHT_PX - image_config.MIN_MARGIN_TOP_PX - image_config.MIN_MARGIN_BOTTOM_PX
        max_cols = line_limit if line_limit else max(1, image_config.TEXT_WIDTH_PX // col_advance)
    # alias for rest of function (uses text_height_px_local)
    text_height_px = text_height_px_local

    # helper to estimate cell height in pixels
    _pil_tmp = None

    def _latin_mono_w() -> int:
        # Monospace advance width of a Latin letter (and of a space), same size for both
        nonlocal _pil_tmp
        if _pil_tmp is None:
            fp = latin_font_path or str(image_config.REPO_ROOT / image_config.FONT_TYPE)
            _pil_tmp = ImageFont.truetype(fp, fontsize)
        return max(1, _pil_tmp.font.getsize(' ')[0][0])

    def _latin_space_w() -> int:
        # Width of the mono half-space AOI around Latin words; configurable.
        return getattr(image_config, 'LATIN_SPACE_WIDTH_PX', None) or _latin_mono_w()

    def _is_japanese_char(c: str) -> bool:
        o = ord(c)
        return (
            0x3000 <= o <= 0x303F      # CJK symbols and punctuation (、。「」〜・々)
            or 0x3040 <= o <= 0x309F   # hiragana
            or 0x30A0 <= o <= 0x30FF   # katakana (incl. ー)
            or 0x3400 <= o <= 0x4DBF   # CJK ext A
            or 0x4E00 <= o <= 0x9FFF   # CJK unified ideographs
            or 0xF900 <= o <= 0xFAFF   # CJK compatibility ideographs
        )

    def _space_width_at(idx: int) -> int:
        # A manual space is full Japanese width only when it sits between two
        # Japanese characters. When it touches western text (or digits/other
        # symbols) it keeps the monospace half-width used around Latin words.
        def _is_jp(nb: list[str] | None) -> bool:
            return bool(nb) and nb not in (['\n'], [' ']) and all(_is_japanese_char(c) for c in nb)
        prev = cell_seq[idx - 1] if idx > 0 else None
        nxt = cell_seq[idx + 1] if idx + 1 < len(cell_seq) else None
        if _is_jp(prev) and _is_jp(nxt):
            return fontsize
        return _latin_space_w()

    def _cell_height_px(cell: list[str], idx: int) -> int:
        nonlocal _pil_tmp
        if cell == [' ']:
            return _space_width_at(idx)
        if cell and all(_is_halfwidth_digit(c) for c in cell) or cell and all(_is_halfwidth_digit(c) or c in ('%', '％') for c in cell) and len(cell) > 1:
            return fontsize * len(cell)
        if cell and all(_is_latin_rotated(c) for c in cell):
            if latin_box == 'tight':
                return _latin_mono_w() * len(cell)
            return fontsize * len(cell)
        return fontsize

    # Precompute each cell's height once (spaces depend on their neighbours, and
    # kinsoku carry must move the precomputed height with the cell).
    cell_h: list[int] = [_cell_height_px(c, i) for i, c in enumerate(cell_seq)]

    cols: list[list[list[str]]] = []  # list of columns, each column is list of cells
    col_bold: list[list[bool]] = []   # parallel bold flags per column
    col_h: list[list[int]] = []       # parallel precomputed cell heights per column
    # Column packing with minimal kinsoku (JLREQ 3.1.7):
    #   - no column starts with a cannot_start char (、。」』） ー ・ small kana …)
    #   - no column ends with a cannot_end char (「『（)
    # Columns are filled to the height limit; at a break boundary the trailing
    # cells are carried to the next column so it starts with a char that may
    # start a line, and the current column does not end with an opening bracket.
    cur: list[list[str]] = []
    cur_bold: list[bool] = []
    cur_heights: list[int] = []
    cur_h = 0
    i = 0
    n = len(cell_seq)
    while i < n:
        cell = cell_seq[i]
        bold = cell_bold[i]
        h = cell_h[i]
        if cell == ['\n']:
            if cur:
                cols.append(cur)
                col_bold.append(cur_bold)
                col_h.append(cur_heights)
                cur = []
                cur_bold = []
                cur_heights = []
                cur_h = 0
            i += 1
            continue
        if cur and cur_h + h > text_height_px:
            carry: list[list[str]] = []
            carry_bold: list[bool] = []
            carry_heights: list[int] = []
            # If the next cell cannot start a line, carry trailing cells down so
            # the next column starts with a char allowed to start a line.
            if cell[0] in _TTB_CANNOT_START:
                while cur and (not carry or carry[0][0] in _TTB_CANNOT_START):
                    moved = cur.pop()
                    mb = cur_bold.pop()
                    mh = cur_heights.pop()
                    cur_h -= mh
                    carry.insert(0, moved)
                    carry_bold.insert(0, mb)
                    carry_heights.insert(0, mh)
            # Do not end a column with an opening bracket.
            if cur and cur[-1][0] in _TTB_CANNOT_END:
                moved = cur.pop()
                mb = cur_bold.pop()
                mh = cur_heights.pop()
                cur_h -= mh
                carry.insert(0, moved)
                carry_bold.insert(0, mb)
                carry_heights.insert(0, mh)
            if cur:
                cols.append(cur)
                col_bold.append(cur_bold)
                col_h.append(cur_heights)
            cur = carry
            cur_bold = carry_bold
            cur_heights = carry_heights
            cur_h = sum(cur_heights)
            if not cur:
                # Could not resolve (e.g. very first char); start a new column.
                cur.append(cell)
                cur_bold.append(bold)
                cur_heights.append(h)
                cur_h += h
                i += 1
            continue
        cur.append(cell)
        cur_bold.append(bold)
        cur_heights.append(h)
        cur_h += h
        i += 1
    if cur:
        cols.append(cur)
        col_bold.append(cur_bold)
        col_h.append(cur_heights)

    if len(cols) > max_cols:
        warnings.warn(
            f'Text for {image_short_name} exceeds {max_cols} columns: has {len(cols)} cols'
        )

    # Shaping and rendering per column
    font_path = str(image_config.REPO_ROOT / image_config.FONT_TYPE)
    blob = hb.Blob.from_file_path(font_path)
    face = hb.Face(blob)
    hb_font = hb.Font(face)
    hb_font.scale = (face.upem, face.upem)
    ft_face = freetype.Face(font_path)
    ft_face.set_char_size(fontsize * 64)
    scale = fontsize / face.upem
    # Bold face for **…** spans: shaped through HarfBuzz in ttb direction as well
    # so vertical variants (、。ー) are applied just like regular text.
    bold_font_path = str(image_config.REPO_ROOT / image_config.FONT_TYPE_BOLD)
    bold_blob = hb.Blob.from_file_path(bold_font_path)
    bold_face = hb.Face(bold_blob)
    hb_font_bold = hb.Font(bold_face)
    hb_font_bold.scale = (bold_face.upem, bold_face.upem)
    ft_face_bold = freetype.Face(bold_font_path)
    ft_face_bold.set_char_size(fontsize * 64)
    scale_bold = fontsize / bold_face.upem

    aois = []
    all_words: list[str] = []
    aoi_idx = 0
    col_idx = 0

    # Margin overlay for review
    if getattr(image_config, 'DEBUG_MARGIN', False):
        m = image_config
        # paint margins as semi transparent, draw border lines
        draw.rectangle([0, 0, m.MIN_MARGIN_LEFT_PX, m.IMAGE_HEIGHT_PX], fill=(255, 220, 220), outline=(255, 0, 0), width=1)
        draw.rectangle([m.IMAGE_WIDTH_PX - m.MIN_MARGIN_RIGHT_PX, 0, m.IMAGE_WIDTH_PX, m.IMAGE_HEIGHT_PX], fill=(255, 220, 220), outline=(255, 0, 0), width=1)
        draw.rectangle([0, 0, m.IMAGE_WIDTH_PX, m.MIN_MARGIN_TOP_PX], fill=(220, 220, 255), outline=(0, 0, 255), width=1)
        draw.rectangle([0, m.IMAGE_HEIGHT_PX - m.MIN_MARGIN_BOTTOM_PX, m.IMAGE_WIDTH_PX, m.IMAGE_HEIGHT_PX], fill=(220, 220, 255), outline=(0, 0, 255), width=1)

    # Green genkoyoshi grid colors
    grid_light = (183, 216, 176)
    grid_mid = (150, 190, 150)
    grid_dark = (110, 160, 110)

    # If image was extended for overflow, draw page margin guides (standard page is rightmost IMAGE_WIDTH_PX)
    if image.width > image_config.IMAGE_WIDTH_PX and getattr(image_config, 'DEBUG_MARGIN', False):
        off = image.width - image_config.IMAGE_WIDTH_PX
        guide_x_left = off + image_config.MIN_MARGIN_LEFT_PX
        guide_x_right = off + image_config.IMAGE_WIDTH_PX - image_config.MIN_MARGIN_RIGHT_PX
        # Draw margin bands for standard page
        draw.rectangle([off, 0, guide_x_left, image.height], fill=(255, 220, 220), outline=(255, 0, 0), width=1)
        draw.rectangle([guide_x_right, 0, off + image_config.IMAGE_WIDTH_PX, image.height], fill=(255, 220, 220), outline=(255, 0, 0), width=1)
        draw.rectangle([off, 0, off + image_config.IMAGE_WIDTH_PX, image_config.MIN_MARGIN_TOP_PX], fill=(220, 220, 255), outline=(0, 0, 255), width=1)
        draw.rectangle([off, image_config.IMAGE_HEIGHT_PX - image_config.MIN_MARGIN_BOTTOM_PX, off + image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX], fill=(220, 220, 255), outline=(0, 0, 255), width=1)
        # Vertical boundary lines at page edges
        draw.line([guide_x_left, 0, guide_x_left, image.height], fill=(255, 0, 0), width=2)
        draw.line([guide_x_right, 0, guide_x_right, image.height], fill=(255, 0, 0), width=2)

    # Centering offsets for box-constrained TTB (e.g. answer fields)
    center_offset_x = 0
    if center_in_box and script_direction == 'ttb' and text_width_px is not None and text_height_px is not None and cols:
        total_width = (len(cols) - 1) * col_advance + fontsize if cols else 0
        center_offset_x = (text_width_px - total_width) // 2
        # clamp to not shift outside box
        if center_offset_x < 0:
            center_offset_x = 0

    for col_idx, col in enumerate(cols):
        # Pen for this column: top-right anchor moving left per column
        # When centered, shift anchor left by center_offset_x so columns are centered horizontally in box
        # Vertical stays top-aligned (user request: only horizontal centering)
        pen_x_center = anchor_x_px - center_offset_x - fontsize // 2 - col_idx * col_advance
        pen_y_top = anchor_y_px

        # For single-char cells we can shape the column as one ttb run for efficiency
        # Latin, digits and %/dash are rendered via PIL, exclude them from the ttb run.
        # Spaces are rendered as empty boxes (no glyph), so they must also be excluded to
        # keep the shaped-run indices aligned with the cells that consume single_idx.
        # Bold cells are rendered separately with the bold font, so exclude them too.
        single_chars = [cell[0] for cell, b in zip(col, col_bold[col_idx]) if len(cell) == 1 and cell[0] != ' ' and not b and not _is_latin_rotated(cell[0]) and not _is_halfwidth_digit(cell[0]) and not _is_punct_via_pil(cell[0])]
        single_text = ''.join(single_chars)
        # Shape singles
        if single_chars:
            buf = hb.Buffer()
            buf.add_str(single_text)
            buf.direction = 'ttb'
            buf.language = image_config.LANGUAGE
            buf.guess_segment_properties()
            buf.direction = 'ttb'
            hb.shape(hb_font, buf)
            single_infos = list(buf.glyph_infos)
            single_positions = list(buf.glyph_positions)
        else:
            single_infos = []
            single_positions = []
        single_idx = 0
        y_px = 0
        row_idx = 0

        for cell, is_bold, cell_h_px in zip(col, col_bold[col_idx], col_h[col_idx]):
            if cell == [' ']:
                mono_w = cell_h_px
                aoi_x = pen_x_center - fontsize // 2
                aoi_y = pen_y_top + y_px
                aoi_w = fontsize
                aoi_h = mono_w
                if getattr(image_config, 'DEBUG_GRID', False):
                    y0 = aoi_y
                    y1 = aoi_y + mono_w
                    x0 = aoi_x
                    x1 = aoi_x + fontsize
                    draw.rectangle([x0, y0, x1, y1], fill=(235, 245, 235), outline=grid_light, width=1)
                    draw.line([x0 + fontsize // 2, y0, x0 + fontsize // 2, y1], fill=grid_mid, width=1)
                    draw.line([x0, y0 + mono_w // 2, x1, y0 + mono_w // 2], fill=grid_mid, width=1)
                    draw.rectangle([x0, y0, x1, y1], outline=grid_dark, width=1)
                if draw_aoi:
                    draw.rectangle([aoi_x, aoi_y, aoi_x + aoi_w, aoi_y + aoi_h], outline='red', width=1)
                aois.append([aoi_idx, ' ', aoi_x, aoi_y, aoi_w, aoi_h, row_idx, col_idx, image_short_name, aoi_idx, col_idx])
                all_words.append(' ')
                aoi_idx += 1
                y_px += mono_w
                row_idx += 1
                continue
            if len(cell) == 1 and _is_latin_alpha(cell[0]):
                # A standalone single Latin letter (e.g. the D in ビタミンD, or an
                # initial like R・ガルザ) is set upright in its own square rather
                # than rotated, so it matches the upright digits next to it. Words
                # of two or more Latin characters still rotate (see below).
                ch = cell[0]
                aoi_x = pen_x_center - fontsize // 2
                aoi_y = pen_y_top + y_px
                aoi_w = fontsize
                aoi_h = fontsize
                if getattr(image_config, 'DEBUG_GRID', False):
                    y0 = aoi_y
                    y1 = aoi_y + fontsize
                    x0 = aoi_x
                    x1 = aoi_x + fontsize
                    draw.rectangle([x0, y0, x1, y1], fill=(235, 245, 235), outline=grid_light, width=1)
                    draw.line([x0 + fontsize // 2, y0, x0 + fontsize // 2, y1], fill=grid_mid, width=1)
                    draw.line([x0, y0 + fontsize // 2, x1, y0 + fontsize // 2], fill=grid_mid, width=1)
                    draw.rectangle([x0, y0, x1, y1], outline=grid_dark, width=1)
                if draw_aoi:
                    draw.rectangle([aoi_x, aoi_y, aoi_x + aoi_w, aoi_y + aoi_h], outline='red', width=1)
                single_font_path = (
                    str(image_config.REPO_ROOT / image_config.FONT_TYPE_BOLD) if is_bold
                    else (latin_font_path or font_path)
                )
                pil_font_single = ImageFont.truetype(single_font_path, fontsize)
                draw.text((aoi_x + fontsize // 2, aoi_y + fontsize // 2), ch,
                          fill=image_config.TEXT_COLOR, font=pil_font_single, anchor='mm')
                aois.append([aoi_idx, ch, aoi_x, aoi_y, aoi_w, aoi_h, row_idx, col_idx, image_short_name, aoi_idx, col_idx])
                all_words.append(ch)
                aoi_idx += 1
                y_px += fontsize
            elif cell and all(_is_latin_rotated(c) for c in cell):
                # Western word (monospaced): AOIs per character, rendering differs by box
                word = ''.join(cell)
                lfp = latin_font_path or font_path
                pil_font_latin = ImageFont.truetype(lfp, fontsize)
                w_per_char = pil_font_latin.font.getsize(cell[0])[0][0]
                w_word = pil_font_latin.font.getsize(word)[0][0]
                if latin_box == 'tight':
                    aoi_h_per_char = max(1, w_per_char)
                else:
                    aoi_h_per_char = fontsize
                total_aoi_h = len(cell) * aoi_h_per_char
                aoi_x_word = pen_x_center - fontsize // 2
                aoi_y_word = pen_y_top + y_px
                # Create per-character AOIs at fixed intervals
                for idx_ch, ch in enumerate(cell):
                    aoi_y = aoi_y_word + idx_ch * aoi_h_per_char
                    aoi_w = fontsize
                    aoi_h = aoi_h_per_char
                    if getattr(image_config, 'DEBUG_GRID', False):
                        y0 = aoi_y
                        y1 = aoi_y + aoi_h
                        x0 = aoi_x_word
                        x1 = aoi_x_word + fontsize
                        draw.rectangle([x0, y0, x1, y1], fill=(235, 245, 235), outline=grid_light, width=1)
                        draw.line([x0 + fontsize // 2, y0, x0 + fontsize // 2, y1], fill=grid_mid, width=1)
                        draw.line([x0, y0 + aoi_h // 2, x1, y0 + aoi_h // 2], fill=grid_mid, width=1)
                        draw.rectangle([x0, y0, x1, y1], outline=grid_dark, width=1)
                    if draw_aoi:
                        draw.rectangle([aoi_x_word, aoi_y, aoi_x_word + aoi_w, aoi_y + aoi_h], outline='red', width=1)
                    aois.append([aoi_idx, ch, aoi_x_word, aoi_y, aoi_w, aoi_h, row_idx + idx_ch, col_idx, image_short_name, aoi_idx, col_idx])
                    all_words.append(ch)
                    aoi_idx += 1
                if latin_box == 'square':
                    # A: square AOI - each letter centered in its own square (not pulled together)
                    for idx_ch, ch in enumerate(cell):
                        aoi_y = aoi_y_word + idx_ch * aoi_h_per_char
                        w_ch = pil_font_latin.font.getsize(ch)[0][0]
                        pad = fontsize // 2
                        tmp_w = w_ch + pad * 2
                        tmp_h = fontsize + pad * 2
                        tmp_img = Image.new('L', (tmp_w, tmp_h), 0)
                        tmp_draw = ImageDraw.Draw(tmp_img)
                        tmp_draw.text((pad, pad), ch, fill=255, font=pil_font_latin)
                        rot = tmp_img.rotate(-90, expand=True, resample=Image.BICUBIC)
                        bbox = rot.getbbox()
                        if bbox:
                            rot_c = rot.crop(bbox)
                            rw, rh = rot_c.size
                            gx = aoi_x_word + (fontsize - rw) // 2
                            gy = aoi_y + (aoi_h_per_char - rh) // 2
                            image.paste(Image.new('RGB', (rw, rh), image_config.TEXT_COLOR), (gx, gy), rot_c)
                else:
                    # B/C: tight - whole word rendered together, correctly spaced, centered in tight AOIs
                    pad = fontsize // 2
                    tmp_w = w_word + pad * 2
                    tmp_h = fontsize + pad * 2
                    tmp_img = Image.new('L', (tmp_w, tmp_h), 0)
                    tmp_draw = ImageDraw.Draw(tmp_img)
                    tmp_draw.text((pad, pad), word, fill=255, font=pil_font_latin)
                    rot = tmp_img.rotate(-90, expand=True, resample=Image.BICUBIC)
                    bbox = rot.getbbox()
                    if bbox:
                        rot_c = rot.crop(bbox)
                        rw, rh = rot_c.size
                        gx = aoi_x_word + (fontsize - rw) // 2
                        gy = aoi_y_word + (total_aoi_h - rh) // 2
                        image.paste(Image.new('RGB', (rw, rh), image_config.TEXT_COLOR), (gx, gy), rot_c)
                y_px += total_aoi_h
                # row_idx counts as one row per word for grid purposes, but AOIs are per char
                row_idx += len(cell) - 1
            elif len(cell) > 1 and all(_is_halfwidth_digit(c) or c in ('%', '％') for c in cell) and any(_is_halfwidth_digit(c) for c in cell):
                # Atomic number run (e.g. 2011, 7,000%, 20%): each digit upright,
                # but the whole run stays together so it is not split across columns.
                pil_font_single = ImageFont.truetype(
                    str(image_config.REPO_ROOT / (image_config.FONT_TYPE_BOLD if is_bold else image_config.FONT_TYPE)),
                    fontsize,
                )
                for k, ch in enumerate(cell):
                    aoi_x = pen_x_center - fontsize // 2
                    aoi_y = pen_y_top + y_px + k * fontsize
                    aoi_w = fontsize
                    aoi_h = fontsize
                    if getattr(image_config, 'DEBUG_GRID', False):
                        y0 = aoi_y
                        y1 = aoi_y + fontsize
                        x0 = aoi_x
                        x1 = aoi_x + fontsize
                        draw.rectangle([x0, y0, x1, y1], fill=(235, 245, 235), outline=grid_light, width=1)
                        draw.line([x0 + fontsize // 2, y0, x0 + fontsize // 2, y1], fill=grid_mid, width=1)
                        draw.line([x0, y0 + fontsize // 2, x1, y0 + fontsize // 2], fill=grid_mid, width=1)
                        draw.rectangle([x0, y0, x1, y1], outline=grid_dark, width=1)
                    if draw_aoi:
                        draw.rectangle([aoi_x, aoi_y, aoi_x + aoi_w, aoi_y + aoi_h], outline='red', width=1)
                    draw.text((aoi_x + fontsize // 2, aoi_y + fontsize // 2), ch, fill=image_config.TEXT_COLOR, font=pil_font_single, anchor='mm')
                    aois.append([aoi_idx, ch, aoi_x, aoi_y, aoi_w, aoi_h, row_idx + k, col_idx, image_short_name, aoi_idx, col_idx])
                    all_words.append(ch)
                    aoi_idx += 1
                y_px += fontsize * len(cell)
                row_idx += len(cell) - 1
            elif len(cell) == 1 and (_is_halfwidth_digit(cell[0]) or _is_punct_via_pil(cell[0])):
                # Single halfwidth digit or %/dash: render centered via PIL; dash is turned (rotated 90° for vertical)
                ch = cell[0]
                aoi_x = pen_x_center - fontsize // 2
                aoi_y = pen_y_top + y_px
                aoi_w = fontsize
                aoi_h = fontsize
                if getattr(image_config, 'DEBUG_GRID', False):
                    y0 = aoi_y
                    y1 = aoi_y + fontsize
                    x0 = aoi_x
                    x1 = aoi_x + fontsize
                    draw.rectangle([x0, y0, x1, y1], fill=(235, 245, 235), outline=grid_light, width=1)
                    draw.line([x0 + fontsize // 2, y0, x0 + fontsize // 2, y1], fill=grid_mid, width=1)
                    draw.line([x0, y0 + fontsize // 2, x1, y0 + fontsize // 2], fill=grid_mid, width=1)
                    draw.rectangle([x0, y0, x1, y1], outline=grid_dark, width=1)
                if draw_aoi:
                    draw.rectangle([aoi_x, aoi_y, aoi_x + aoi_w, aoi_y + aoi_h], outline='red', width=1)
                pil_font_single = ImageFont.truetype(
                    str(image_config.REPO_ROOT / (image_config.FONT_TYPE_BOLD if is_bold else image_config.FONT_TYPE)),
                    fontsize,
                )
                draw.text((aoi_x + fontsize // 2, aoi_y + fontsize // 2), ch, fill=image_config.TEXT_COLOR, font=pil_font_single, anchor='mm')
                aois.append([aoi_idx, ch, aoi_x, aoi_y, aoi_w, aoi_h, row_idx, col_idx, image_short_name, aoi_idx, col_idx])
                all_words.append(ch)
                aoi_idx += 1
                y_px += fontsize
            elif len(cell) == 1 and is_bold:
                # Bold char (from a **…** span): shape with the bold font in ttb
                # direction so vertical variants (、。ー) are applied, exactly like
                # the regular single-char path.
                ch = cell[0]
                aoi_x = pen_x_center - fontsize // 2
                aoi_y = pen_y_top + y_px
                aoi_w = fontsize
                aoi_h = fontsize
                if getattr(image_config, 'DEBUG_GRID', False):
                    y0 = aoi_y
                    y1 = aoi_y + fontsize
                    x0 = aoi_x
                    x1 = aoi_x + fontsize
                    draw.rectangle([x0, y0, x1, y1], fill=(235, 245, 235), outline=grid_light, width=1)
                    draw.line([x0 + fontsize // 2, y0, x0 + fontsize // 2, y1], fill=grid_mid, width=1)
                    draw.line([x0, y0 + fontsize // 2, x1, y0 + fontsize // 2], fill=grid_mid, width=1)
                    draw.rectangle([x0, y0, x1, y1], outline=grid_dark, width=1)
                if draw_aoi:
                    draw.rectangle([aoi_x, aoi_y, aoi_x + aoi_w, aoi_y + aoi_h], outline='red', width=1)
                bbuf = hb.Buffer()
                bbuf.add_str(ch)
                bbuf.direction = 'ttb'
                bbuf.language = image_config.LANGUAGE
                bbuf.guess_segment_properties()
                bbuf.direction = 'ttb'
                hb.shape(hb_font_bold, bbuf)
                binfo = bbuf.glyph_infos[0]
                bpos = bbuf.glyph_positions[0]
                gid = binfo.codepoint
                x_off_px = bpos.x_offset * scale_bold
                y_off_px = -bpos.y_offset * scale_bold
                ft_face_bold.load_glyph(gid, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
                bitmap = ft_face_bold.glyph.bitmap
                w, h = bitmap.width, bitmap.rows
                left = ft_face_bold.glyph.bitmap_left
                top = ft_face_bold.glyph.bitmap_top
                glyph_x = int(pen_x_center + x_off_px + left)
                glyph_y = int(pen_y_top + y_px + y_off_px - top)
                if w > 0 and h > 0:
                    glyph_img = Image.frombytes('L', (w, h), bytes(bitmap.buffer))
                    image.paste(Image.new('RGB', (w, h), image_config.TEXT_COLOR), (glyph_x, glyph_y), glyph_img)
                aois.append([aoi_idx, ch, aoi_x, aoi_y, aoi_w, aoi_h, row_idx, col_idx, image_short_name, aoi_idx, col_idx])
                all_words.append(ch)
                aoi_idx += 1
                y_px += fontsize
            else:
                ch = cell[0]
                info = single_infos[single_idx]
                pos = single_positions[single_idx]
                single_idx += 1
                aoi_x = pen_x_center - fontsize // 2
                aoi_y = pen_y_top + y_px
                aoi_w = fontsize
                aoi_h = fontsize

                if getattr(image_config, 'DEBUG_GRID', False):
                    y0 = aoi_y
                    y1 = aoi_y + fontsize
                    x0 = aoi_x
                    x1 = aoi_x + fontsize
                    draw.rectangle([x0, y0, x1, y1], fill=(235, 245, 235), outline=grid_light, width=1)
                    draw.line([x0 + fontsize // 2, y0, x0 + fontsize // 2, y1], fill=grid_mid, width=1)
                    draw.line([x0, y0 + fontsize // 2, x1, y0 + fontsize // 2], fill=grid_mid, width=1)
                    draw.rectangle([x0, y0, x1, y1], outline=grid_dark, width=1)

                if draw_aoi:
                    draw.rectangle([aoi_x, aoi_y, aoi_x + aoi_w, aoi_y + aoi_h], outline='red', width=1)

                gid = info.codepoint
                x_off_px = pos.x_offset * scale
                y_off_px = -pos.y_offset * scale
                ft_face.load_glyph(gid, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
                bitmap = ft_face.glyph.bitmap
                w, h = bitmap.width, bitmap.rows
                left = ft_face.glyph.bitmap_left
                top = ft_face.glyph.bitmap_top
                pen_x = pen_x_center
                pen_y = pen_y_top + y_px
                glyph_x = int(pen_x + x_off_px + left)
                glyph_y = int(pen_y + y_off_px - top)
                if w > 0 and h > 0:
                    glyph_img = Image.frombytes('L', (w, h), bytes(bitmap.buffer))
                    image.paste(Image.new('RGB', (w, h), image_config.TEXT_COLOR), (glyph_x, glyph_y), glyph_img)

                aois.append([aoi_idx, ch, aoi_x, aoi_y, aoi_w, aoi_h, row_idx, col_idx, image_short_name, aoi_idx, col_idx])
                all_words.append(ch)
                aoi_idx += 1
                y_px += fontsize
            row_idx += 1

        col_idx += 1

    # Fixation dot: single hollow end dot, matching Arabic horizontal
    # When image was extended for overflow, keep dot at original page left margin
    r = image_config.FIX_DOT_RADIUS_PX
    fix_x = image_config.POS_BOTTOM_DOT_X_PX
    if image.width > image_config.IMAGE_WIDTH_PX:
        fix_x += image.width - image_config.IMAGE_WIDTH_PX
    fix_y = image_config.POS_BOTTOM_DOT_Y_PX
    draw.ellipse((fix_x - r, fix_y - r, fix_x + r, fix_y + r), fill=None, outline=image_config.TEXT_COLOR, width=image_config.FIX_DOT_WIDTH_PX)

    return aois, all_words


def create_images(
        stimuli_xlsx_file_name: str,
        question_xlsx_file_name: str,
        image_dir: str = image_config.IMAGE_DIR,
        question_dir: str = image_config.QUESTION_IMAGE_DIR,
        aoi_dir: str = image_config.AOI_DIR,
        question_aoi_dir: str = image_config.AOI_QUESTION_DIR,
        aoi_image_dir: str = image_config.AOI_IMG_DIR,
        draw_aoi=False,
):

    initial_stimulus_df = pd.read_excel(stimuli_xlsx_file_name)
    # initial_stimulus_df = pd.read_csv(stimuli_csv_file_name, sep=',', encoding='utf-8')
    initial_stimulus_df.dropna(subset=['stimulus_id'], inplace=True)

    initial_stimulus_df['stimulus_id'] = initial_stimulus_df['stimulus_id'].astype(int)

    stimulus_types = initial_stimulus_df['stimulus_type'].unique()
    checks.check_stimulus_types(stimulus_types)

    open(image_config.REPO_ROOT / image_config.OUTPUT_TOP_DIR / 'overlong_question_options.txt', 'w',
         encoding='utf8').close()

    # check whether question excel exists as file, stimuli can be created independent of questions
    if os.path.isfile(question_xlsx_file_name):
        initial_question_df = pd.read_excel(question_xlsx_file_name)
        initial_question_df.dropna(subset=['stimulus_id'], inplace=True)
        # make sure in initial question df, stimulus_id is int
        initial_question_df['stimulus_id'] = initial_question_df['stimulus_id'].astype(int)

        stimulus_types = initial_question_df['stimulus_type'].unique()
        checks.check_stimulus_types(stimulus_types)

        cols = initial_question_df.columns.to_list().extend(
            ['question_img_path', 'question_img_file', 'target_key', 'distractor_a_key', 'distractor_b_key',
             'distractor_c_key']
        )
        new_question_df = pd.DataFrame(columns=cols)
    else:
        warnings.warn("No question file found. Question images will not be created.")
        question_xlsx_file_name = None

    block_config = pd.read_csv(image_config.REPO_ROOT / image_config.BLOCK_CONFIG_PATH, sep=',', encoding='UTF-8')

    image_dir_with_root = image_config.REPO_ROOT / image_dir
    aoi_dir_with_root = image_config.REPO_ROOT / aoi_dir
    aoi_image_dir_with_root = image_config.REPO_ROOT / aoi_image_dir
    question_dir_with_root = image_config.REPO_ROOT / question_dir
    question_aoi_dir_with_root = image_config.REPO_ROOT / question_aoi_dir

    if not os.path.isdir(image_dir_with_root):
        os.mkdir(image_dir_with_root)

    if not os.path.isdir(aoi_dir_with_root):
        os.mkdir(aoi_dir_with_root)

    if not os.path.isdir(aoi_image_dir_with_root):
        os.mkdir(aoi_image_dir_with_root)

    if not os.path.isdir(question_dir_with_root):
        os.mkdir(question_dir_with_root)

    if not os.path.isdir(question_aoi_dir_with_root):
        os.mkdir(question_aoi_dir_with_root)

    stimulus_images = {}

    for row_index, row in (pbar := tqdm(initial_stimulus_df.iterrows(), total=len(initial_stimulus_df))):
        stimulus_name = row[f"stimulus_name"]
        stimulus_id = int(row[f"stimulus_id"])
        pbar.set_description(
            f'Creating {image_config.LANGUAGE}{" aoi" if draw_aoi else ""} stimuli images for {stimulus_id}'
            f' {stimulus_name}'
        )

        # check whether stimulus id and name exist
        try:
            block_config[((block_config['stimulus_id'] == stimulus_id)
                          & (block_config['stimulus_name'] == stimulus_name))]
        except IndexError:
            raise ValueError(
                f'Something is wrong with the stimulus id and name of : {stimulus_id} {stimulus_name}. '
                f'Please check it is the same as in the English files.'
            )
        stimulus_name = re.sub(' ', '_', stimulus_name)

        aoi_file_name = f'{stimulus_name.lower()}_{stimulus_id}_aoi.csv'
        aoi_file_name_questions = f'{stimulus_name.lower()}_{stimulus_id}_aoi_questions.csv'
        aoi_header = ['char_idx', 'char', 'top_left_x', 'top_left_y', 'width', 'height',
                      'char_idx_in_line', 'line_idx', 'page', 'word_idx', 'word_idx_in_line']
        all_aois = []
        all_words = []
        question_image_versions = []

        # check whether question excel exists
        if question_xlsx_file_name:

            # get all questions for that text
            question_sub_df_stimulus = initial_question_df.loc[(initial_question_df['stimulus_id'] == stimulus_id) &
                                                               (initial_question_df['stimulus_name'] == stimulus_name)]
            if len(question_sub_df_stimulus) == 0:
                warnings.warn(f'No questions found for {stimulus_name} {stimulus_id}. Please check if the question '
                              f'are there and all the spelling and IDs are correct in all files! Question files '
                              f'and stimulus files.')

            for i in range(image_config.VERSION_START, image_config.NUM_PERMUTATIONS + image_config.VERSION_START):

                # the answer options are shuffeled for each participant (each gets a new item version)
                session_id = 'question_images_version_' + str(i)

                question_csv_filename_stem = Path(question_xlsx_file_name).stem
                new_session_question_df_name = (f'{question_csv_filename_stem}{"_aoi" if draw_aoi else ""}_'
                                                f'{session_id}_with_img_paths.csv')
                full_path_root_question_df = os.path.join(
                    question_dir_with_root if not draw_aoi else question_aoi_dir_with_root,
                    session_id,
                    new_session_question_df_name
                )

                if not os.path.exists(Path(full_path_root_question_df).parent):
                    os.mkdir(Path(full_path_root_question_df).parent)

                full_path_question_df = os.path.join(
                    question_dir if not draw_aoi else question_aoi_dir,
                    session_id,
                    new_session_question_df_name
                )

                # if there already is a file, and we did not start a new image creation, we open the existing file
                if os.path.isfile(full_path_root_question_df) and not row_index == 0:
                    new_session_question_df = pd.read_csv(full_path_root_question_df)

                else:
                    new_session_question_df = new_question_df

                shuffeled_answer_options_path = os.path.join(
                    image_config.ANSWER_OPTION_FOLDER +
                    f'shuffled_option_keys_{image_config.LANGUAGE}_{session_id}.json'
                )
                # if we have already once shuffeled some of the options for this item, we open the existing file
                if os.path.isfile(image_config.REPO_ROOT / shuffeled_answer_options_path):
                    with open(image_config.REPO_ROOT / shuffeled_answer_options_path, 'r') as f:
                        shuffled_option_dict = json.load(f)
                else:
                    shuffled_option_dict = {}

                question_sub_csv_copy = question_sub_df_stimulus.copy()

                temp_paths = []
                temp_files_names = []
                temp_target_keys = []
                temp_distractor_a_keys = []
                temp_distractor_b_keys = []
                temp_distractor_c_keys = []
                for question_row_index, question_row in question_sub_df_stimulus.iterrows():

                    question = question_row['question']
                    snippet_no = question_row['snippet_no']
                    condition_no = question_row['condition_no']
                    question_no = question_row['question_no']
                    question_id = str(int(stimulus_id)) + str(int(snippet_no)) + str(int(condition_no)) + str(int(question_no))
                    if len(question_id) == 4:
                        question_id = '0' + question_id

                    # Hardcoded fix for Arg_PISACowsMilk (stimulus_id 10) question 10212 in
                    # Hebrew only: 'ה-British' is a mixed Hebrew+Latin token directly glued to
                    # the following pure-Latin run 'Medical Journal'. reorder_ltr_runs merges
                    # the three into one run and reverses their order, which is correct for a
                    # pure-Latin-led run (verified against the Unicode Bidi Algorithm) but wrong
                    # when a mixed word leads the run: it produces 'Journal Medical British-ה'
                    # instead of 'ה-British Medical Journal'. A general fix for mixed-word-led
                    # runs was tried and reverted -- it broke the (unrelated, already-correct)
                    # 'תוכניותCOST (Cooperation in Science and Technology)' case. Splitting off
                    # the 'ה-' prefix with a space keeps it out of the run entirely, which
                    # matches the desired order (verified against the Unicode Bidi Algorithm).
                    if (image_config.LANGUAGE == 'he' and question_id == '10212'
                            and image_config.CITY == 'Haifa'):
                        question = question.replace('ה-British', 'ה- British')

                    # item_id = question_row['item_id']

                    question_identifier = f'question_{question_id}_stimulus_{stimulus_id}'

                    answer_options = OrderedDict(
                        {'target': clean_option(question_row['target']),
                         'distractor_a': clean_option(question_row['distractor_a']),
                         'distractor_b': clean_option(question_row['distractor_b']),
                         'distractor_c': clean_option(question_row['distractor_c'])}
                    )

                    question_image = Image.new(
                        'RGB', (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
                        color=image_config.BACKGROUND_COLOR
                    )

                    aois, words = draw_text(
                        question, question_image, image_config.FONT_SIZE_PX,
                        spacing=image_config.LINE_SPACING,
                        image_short_name=f'question_{question_id}',
                        draw_aoi=draw_aoi, line_limit=2,
                        word_split_criterion=image_config.WORD_SPLIT_CRITERION,
                    )

                    all_aois.extend(aois)
                    all_words.extend(words)
                    question_image_versions.extend([session_id for _ in range(len(aois))])

                    # vertical ttb: same dims as before but squeezed left for 2-col question, up/down taller
                    if image_config.SCRIPT_DIRECTION == 'ttb':
                        col_w = image_config.COLUMN_ADVANCE_PX or int(image_config.FONT_SIZE_PX * image_config.LINE_SPACING)
                        question_w = 2 * col_w
                        available_w = image_config.TEXT_WIDTH_PX - question_w - int(col_w * 0.5)
                        available_w = max(available_w, image_config.TEXT_WIDTH_PX // 2)
                        # keep original proportions but fit in available_w: up/down 0.7W, left/right split remaining
                        up_w = int(image_config.IMAGE_WIDTH_PX * 0.7)
                        up_w = min(up_w, available_w)
                        left_w = int((available_w - 109) // 2)
                        left_w = min(left_w, int(image_config.IMAGE_WIDTH_PX * 0.41))
                        right_w = left_w
                        # squeeze left: center up/down in available area, left at margin, right after gap
                        up_x = image_config.MIN_MARGIN_LEFT_PX + (available_w - up_w) // 2
                        left_x = image_config.MIN_MARGIN_LEFT_PX
                        right_x = left_x + left_w + 109
                        # enlarge = 0.22-0.17 = 0.05H, shift up 3x, middle 2x, down 1x to avoid overlap
                        delta_h = int(image_config.IMAGE_HEIGHT_PX * 0.05)
                        option_keys = {
                            'left': {
                                'x_px': int(left_x),
                                'y_px': int(image_config.IMAGE_HEIGHT_PX * 0.44 - delta_h * 2),
                                'text_width_px': int(left_w),
                                'text_height_px': int(image_config.IMAGE_HEIGHT_PX * 0.28),
                            },
                            'up': {
                                'x_px': int(up_x),
                                'y_px': int(image_config.IMAGE_HEIGHT_PX * 0.25 - int(delta_h * 3)),
                                'text_width_px': int(up_w),
                                'text_height_px': int(image_config.IMAGE_HEIGHT_PX * 0.22),
                            },
                            'right': {
                                'x_px': int(right_x),
                                'y_px': int(image_config.IMAGE_HEIGHT_PX * 0.44 - delta_h * 2),
                                'text_width_px': int(right_w),
                                'text_height_px': int(image_config.IMAGE_HEIGHT_PX * 0.28),
                            },
                            'down': {
                                'x_px': int(up_x),
                                'y_px': int(image_config.IMAGE_HEIGHT_PX * 0.71 - delta_h),
                                'text_width_px': int(up_w),
                                'text_height_px': int(image_config.IMAGE_HEIGHT_PX * 0.22),
                            }
                        }
                    # greenlandic needs a different layout as it has very long words and the boxes are too small
                    elif image_config.LANGUAGE == 'kl':
                        option_keys = {
                            'left': {
                                'x_px': image_config.MIN_MARGIN_LEFT_PX,
                                'y_px': image_config.IMAGE_HEIGHT_PX * 0.39,
                                'text_width_px': image_config.TEXT_WIDTH_PX * 0.49,
                                'text_height_px': (5.0 + 3 * image_config.LINE_SPACING) * image_config.FONT_SIZE_PX,
                            },
                            'up': {
                                'x_px': image_config.MIN_MARGIN_LEFT_PX,
                                'y_px': image_config.IMAGE_HEIGHT_PX * 0.25,
                                'text_width_px': image_config.IMAGE_WIDTH_PX - image_config.MIN_MARGIN_RIGHT_PX - image_config.MIN_MARGIN_LEFT_PX,
                                'text_height_px': (2.1 + image_config.LINE_SPACING) * image_config.FONT_SIZE_PX,

                            },
                            'right': {
                                'x_px': image_config.IMAGE_WIDTH_PX * 0.51,
                                'y_px': image_config.IMAGE_HEIGHT_PX * 0.39,
                                'text_width_px': image_config.TEXT_WIDTH_PX * 0.49,
                                'text_height_px': (5.0 + 3 * image_config.LINE_SPACING) * image_config.FONT_SIZE_PX,
                            },
                            'down': {
                                'x_px': image_config.MIN_MARGIN_LEFT_PX,
                                'y_px': image_config.IMAGE_HEIGHT_PX * 0.75,
                                'text_width_px': image_config.IMAGE_WIDTH_PX - image_config.MIN_MARGIN_RIGHT_PX - image_config.MIN_MARGIN_LEFT_PX,
                                'text_height_px': (2.1 + image_config.LINE_SPACING) * image_config.FONT_SIZE_PX,
                            }
                        }

                    else:
                        option_keys = {
                            'left': {
                                'x_px': image_config.MIN_MARGIN_LEFT_PX,
                                'y_px': image_config.IMAGE_HEIGHT_PX * 0.44,
                                'text_width_px': image_config.IMAGE_WIDTH_PX * 0.41,
                                'text_height_px': image_config.IMAGE_HEIGHT_PX * 0.28,
                            },
                            'up': {
                                'x_px': image_config.IMAGE_WIDTH_PX * 0.15,
                                'y_px': image_config.IMAGE_HEIGHT_PX * 0.25,
                                'text_width_px': image_config.IMAGE_WIDTH_PX * 0.7,
                                'text_height_px': image_config.IMAGE_HEIGHT_PX * 0.17,

                            },
                            'right': {
                                'x_px': image_config.IMAGE_WIDTH_PX * 0.53,
                                'y_px': image_config.IMAGE_HEIGHT_PX * 0.44,
                                'text_width_px': image_config.IMAGE_WIDTH_PX * 0.41,
                                'text_height_px': image_config.IMAGE_HEIGHT_PX * 0.28,
                            },
                            'down': {
                                'x_px': image_config.IMAGE_WIDTH_PX * 0.15,
                                'y_px': image_config.IMAGE_HEIGHT_PX * 0.75,
                                'text_width_px': image_config.IMAGE_WIDTH_PX * 0.7,
                                'text_height_px': image_config.IMAGE_HEIGHT_PX * 0.17,
                            }
                        }

                        if image_config.LANGUAGE == 'ca' and image_config.CITY == 'Zurich':
                            # for the catalan data collection in zurich two options are too large.
                            # To ensure comparability across the data collection sites, the left and right box are made
                            # slightly bigger instead of shortening the text
                            option_keys['right']['text_width_px'] = image_config.IMAGE_WIDTH_PX * 0.42
                            option_keys['left']['text_width_px'] = image_config.IMAGE_WIDTH_PX * 0.42


                    # if we already have the shuffled options file for this item version, but we have not yet
                    # shuffled the options for this question
                    if question_identifier not in shuffled_option_dict:
                        # TESTING ANSWER OPTION LENGTH: refer to README.md
                        shuffled_option_keys = ['left', 'up', 'right', 'down']
                        # shuffled_option_keys = ['up', 'left', 'down', 'right']
                        random.seed(question_identifier + session_id)
                        random.shuffle(shuffled_option_keys)
                        shuffled_option_keys = {k: v for k, v in zip(answer_options, shuffled_option_keys)}
                        shuffled_option_dict[question_identifier] = shuffled_option_keys

                    else:
                        shuffled_option_keys = shuffled_option_dict[question_identifier]

                    temp_target_keys.append(shuffled_option_keys['target'])
                    temp_distractor_a_keys.append(shuffled_option_keys['distractor_a'])
                    temp_distractor_b_keys.append(shuffled_option_keys['distractor_b'])
                    temp_distractor_c_keys.append(shuffled_option_keys['distractor_c'])

                    for option, distractor_key in shuffled_option_keys.items():
                        # for greenlandic (kl), we reduce the font size for the options a bit as
                        # the words are so long that they do not fit
                        if image_config.LANGUAGE == 'kl':
                            font_size = image_config.FONT_SIZE_PX * 0.8
                        else:
                            font_size = image_config.FONT_SIZE_PX

                        aois, words = draw_text(
                            answer_options[option], question_image, font_size,
                            spacing=image_config.LINE_SPACING,
                            image_short_name=f'{stimulus_name}_{stimulus_id}_question_{question_id}_{option}',
                            draw_aoi=draw_aoi,
                            anchor_x_px=(option_keys[distractor_key]['x_px'] + option_keys[distractor_key]['text_width_px']
                                         if image_config.SCRIPT_DIRECTION in ('rtl', 'ttb')
                                         else option_keys[distractor_key]['x_px']),
                            anchor_y_px=option_keys[distractor_key]['y_px'],
                            text_width_px=option_keys[distractor_key]['text_width_px'],
                            text_height_px=option_keys[distractor_key]['text_height_px'],
                            question_option_type=distractor_key,
                            word_split_criterion=image_config.WORD_SPLIT_CRITERION,
                            center_in_box=(image_config.SCRIPT_DIRECTION == 'ttb'),
                        )

                        draw = ImageDraw.Draw(question_image)

                        # draw a box around the answer options: x, y, x + width, y + height, x must be a bit smaller
                        # otherwise it is too close to the letters
                        new_x = option_keys[distractor_key]['x_px'] - image_config.MIN_MARGIN_LEFT_PX * 0.1
                        new_width = option_keys[distractor_key]['text_width_px'] + image_config.MIN_MARGIN_LEFT_PX * 0.15
                        box_coordinates = (
                            new_x,
                            option_keys[distractor_key]['y_px'],
                            new_x + new_width,
                            option_keys[distractor_key]['y_px'] + option_keys[distractor_key][
                                'text_height_px'])

                        draw.rectangle(box_coordinates, outline='black', width=1)

                        CONFIG.setdefault('QUESTION_OPTION_BOXES: TOP_X, TOP_Y, BOTTOM_X, BOTTOM_Y', {}).update(
                            {distractor_key: box_coordinates})

                        all_aois.extend(aois)
                        all_words.extend(words)
                        question_image_versions.extend([session_id for _ in range(len(aois))])

                    question_image_file = f"{stimulus_name}_id{stimulus_id}_question_{question_id}_{image_config.LANGUAGE}" \
                                          f"{'_aoi' if draw_aoi else ''}.png"
                    question_image_path_root = question_aoi_dir_with_root if draw_aoi else question_dir_with_root

                    if not os.path.isdir(os.path.join(question_image_path_root, session_id)):
                        os.mkdir(os.path.join(question_image_path_root, session_id))

                    question_image.save(question_image_path_root / session_id / question_image_file)

                    question_image_path = question_aoi_dir if draw_aoi else question_dir
                    question_image_path = Path(question_image_path) / session_id / question_image_file
                    question_image_path = str(question_image_path).replace('\\', '/')

                    temp_paths.append(question_image_path)
                    temp_files_names.append(question_image_file)

                question_sub_csv_copy.loc[
                    question_sub_df_stimulus['stimulus_id'] == stimulus_id, 'question_img_path'] = temp_paths
                question_sub_csv_copy['question_img_file'] = temp_files_names
                question_sub_csv_copy['target_key'] = temp_target_keys
                question_sub_csv_copy['distractor_a_key'] = temp_distractor_a_keys
                question_sub_csv_copy['distractor_b_key'] = temp_distractor_b_keys
                question_sub_csv_copy['distractor_c_key'] = temp_distractor_c_keys
                new_session_question_df = pd.concat([new_session_question_df, question_sub_csv_copy], axis=0)

                new_session_question_df.to_csv(
                    full_path_root_question_df,
                    sep=',',
                    index=False,
                )
                # save relative path without root
                CONFIG.setdefault('QUESTION_CSV_PATHS', {}).update(
                    {
                        f'question_images_{session_id}{"_aoi" if draw_aoi else ""}_csv': full_path_question_df
                    }
                )

                output_file = Path(image_config.REPO_ROOT / shuffeled_answer_options_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)

                with open(image_config.REPO_ROOT / shuffeled_answer_options_path, 'w', encoding='utf8') as f:
                    json.dump(shuffled_option_dict, f, indent=4)

        empty_page = False
        empty_page_inbetween = False

        for col_index, column_name in enumerate(initial_stimulus_df.columns):

            if column_name.startswith('page'):

                new_col_name_path = column_name + '_img_path'
                new_col_name_file = column_name + '_img_file'

                if new_col_name_path not in stimulus_images:
                    stimulus_images[new_col_name_path] = []

                if new_col_name_file not in stimulus_images:
                    stimulus_images[new_col_name_file] = []

                # if page for that text is empty
                if row[[column_name]].isnull().values.any():
                    stimulus_images[new_col_name_path].append(pd.NA)
                    stimulus_images[new_col_name_file].append(pd.NA)
                    empty_page = True
                    continue

                if empty_page:
                    empty_page_inbetween = True
                    empty_page = False

                text = str(initial_stimulus_df.iloc[row_index, col_index])

                # Hardcoded fix for PopSci_MultiplEYE (stimulus_id 1) page_1 in Hebrew only:
                # '(eye-tracking). MultiplEYE' is a run of English words long enough to wrap
                # across a line break. Because '(eye-tracking).' isn't self-bracketed (the
                # closing ')' is followed by a period), it gets merged into one multi-word run
                # with 'MultiplEYE' and reordered as a unit, which corrupts the layout when the
                # run is split across the wrap. Reviewers confirmed this can't be fixed
                # automatically and asked for this exact occurrence to be handled by hand: the
                # period belongs to the 'eye-tracking' sentence and must stay glued to it, while
                # 'MultiplEYE' (a new sentence) starts on the next row. Forcing a paragraph break
                # right there keeps '(eye-tracking).' intact as its own line (rendered correctly
                # since it's no longer merged with 'MultiplEYE') and starts 'MultiplEYE' fresh.
                if (image_config.LANGUAGE == 'he' and stimulus_id == 1
                        and column_name == 'page_1' and image_config.CITY == 'Haifa'):
                    text = text.replace('(eye-tracking). MultiplEYE', '(eye-tracking).\nMultiplEYE')

                # Hardcoded fix for Arg_PISACowsMilk (stimulus_id 10) page_11 in Hebrew only:
                # same 'ה-British' issue as the question_10212 fix above (see that comment for
                # the full explanation) -- this is the stimulus-page occurrence of the same text.
                if (image_config.LANGUAGE == 'he' and stimulus_id == 10
                        and column_name == 'page_11' and image_config.CITY == 'Haifa'):
                    text = text.replace('ה-British', 'ה- British')

                # Create a new image with a previously defined color background and size
                final_image = Image.new(
                    'RGB', (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
                    color=image_config.BACKGROUND_COLOR
                )

                aois, words = draw_text(
                    text, final_image, image_config.FONT_SIZE_PX,
                    spacing=image_config.LINE_SPACING, image_short_name=column_name,
                    draw_aoi=draw_aoi,
                    word_split_criterion=image_config.WORD_SPLIT_CRITERION,
                )
                # For ttb overflow, extend image so all columns fit with margin guides
                if image_config.SCRIPT_DIRECTION == 'ttb' and aois:
                    min_x = min(a[2] for a in aois)
                    if min_x < image_config.MIN_MARGIN_LEFT_PX:
                        extend = image_config.MIN_MARGIN_LEFT_PX - min_x
                        new_w = image_config.IMAGE_WIDTH_PX + extend
                        final_image = Image.new('RGB', (new_w, image_config.IMAGE_HEIGHT_PX), color=image_config.BACKGROUND_COLOR)
                        aois, words = draw_text(
                            text, final_image, image_config.FONT_SIZE_PX,
                            spacing=image_config.LINE_SPACING, image_short_name=column_name,
                            draw_aoi=draw_aoi,
                            word_split_criterion=image_config.WORD_SPLIT_CRITERION,
                        )

                filename = f"{stimulus_name.lower()}_id{stimulus_id}_{column_name}_{image_config.LANGUAGE}" \
                           f"{'_aoi' if draw_aoi else ''}.png"

                # save the image to path with root, but save the path without only rela tive to the data folder
                img_path_root = aoi_image_dir_with_root if draw_aoi else image_dir_with_root
                img_path = aoi_image_dir if draw_aoi else image_dir
                img_path_root = os.path.join(img_path_root, filename)
                img_path = os.path.join(img_path, filename)
                final_image.save(img_path_root)

                stimulus_images[new_col_name_path].append(img_path)
                stimulus_images[new_col_name_file].append(filename)

                all_aois.extend(aois)
                all_words.extend(words)
                question_image_versions.extend([pd.NA for _ in range(len(aois))])

        if empty_page_inbetween and not draw_aoi:
            warnings.warn(f'Empty page for {stimulus_name} {stimulus_id}')

        aoi_df = pd.DataFrame(all_aois, columns=aoi_header)
        aoi_df['word'] = all_words
        aoi_df['question_image_version'] = question_image_versions
        aoi_df_path = os.path.join(aoi_dir, aoi_file_name)
        aoi_df_path_questions = os.path.join(aoi_dir, aoi_file_name_questions)

        # split the aoi_df into two parts, one for the stimulus and one for the questions
        aoi_df_texts = aoi_df[~aoi_df['page'].str.contains('question', na=False)]
        aoi_df_texts.drop(columns=['question_image_version'], inplace=True, errors='ignore')
        aoi_df_questions = aoi_df[aoi_df['page'].str.contains('question', na=False)]

        aoi_df_texts.to_csv(image_config.REPO_ROOT / aoi_df_path, sep=',', index=False, encoding='UTF-8')
        aoi_df_questions.to_csv(image_config.REPO_ROOT / aoi_df_path_questions, sep=',', index=False, encoding='UTF-8')

    # Create a new csv file with the names of the pictures in the first column and their paths in the second
    image_df = pd.DataFrame(stimulus_images)
    final_stimulus_df = initial_stimulus_df.join(image_df)
    stimuli_file_name_stem = Path(stimuli_xlsx_file_name).stem
    full_output_file_name = f'{stimuli_file_name_stem}_{image_config.COUNTRY_CODE}_{image_config.LAB_NUMBER}{"_aoi" if draw_aoi else ""}_with_img_paths.csv'
    full_path = os.path.join(image_config.OUTPUT_TOP_DIR, full_output_file_name)
    CONFIG.setdefault('PATHS', {}).update({f'stimuli_images{"_aoi" if draw_aoi else ""}_csv': full_path})
    final_stimulus_df.to_csv(
        image_config.REPO_ROOT / full_path,
        sep=',',
        index=False
    )


def get_option_span_indices(text: str, annotated_text: str,
                            target_span: str, distractor_span: str | None,
                            question_id: str, aoi: bool) -> [list, list, list]:
    """
    Searches a text span in a text and returns the word and char indices in the text of the span.
    :param text: Stimulus text as-is
    :param annotated_text: Stimulus text with annotated spans
    :param target_span: That target span, beginning with the target begin marker and ending with the target end marker
    :param distractor_span: The distractor span, beginning with the distractor begin marker
        and ending with the distractor end marker. If none, there is no distractor span
    :param question_id: The question id to identify the markers in the text
    :param aoi: Whether we are drawing aois or not
    :return: Three lists for all chars in the text. First contains whether and what part of target span the char is, second
        same for distractor, third the chars in the text

    see: https://pynative.com/python-find-position-of-regex-match-using-span-start-end/
    """

    target_span_marked, distractor_span_marked = [], []

    target_begin_marker = f'<t{question_id}b>'
    target_end_marker = f'<t{question_id}e>'
    distractor_begin_marker = f'<d{question_id}b>'
    distractor_end_marker = f'<d{question_id}e>'

    # check whether the target span is annotated in the text
    target_span_match = re.search(target_span, annotated_text)

    if distractor_span is not None:
        distractor_span = re.escape(distractor_span)
        distractor_span_match = re.search(distractor_span, annotated_text)
    else:
        distractor_span_match = None

    # not necessary to warn for drawing aoi images, as we have already warned for the normal ones
    if not aoi:
        if not target_span_match:
            warnings.warn(
                f'Target/distractor a span including markers not found in the annotated text for question {question_id}.'
                f'Please check that the span has been copied correctly in the excel!', stacklevel=2)
        if distractor_span and not distractor_span_match:
            warnings.warn(
                f'Distractor b span including marker not found in the annotated text for question {question_id}. '
                f'Please check that the span has been copied correctly in the excel!', stacklevel=2)

    # get the indice of the start and end character of both spans in the normal text, clean spans first
    target_span_clean = target_span.replace(target_begin_marker, '').replace(target_end_marker, '')
    target_span_clean = re.escape(target_span_clean)
    target_span_match_clean = re.search(target_span_clean, text)

    if distractor_span:
        distractor_span_clean = distractor_span.replace(distractor_begin_marker, '').replace(distractor_end_marker, '')
        distractor_span_match_clean = re.search(distractor_span_clean, text)
    else:
        distractor_span_match_clean = None

    # in case the target span cannot be found, we warn and continue
    if not target_span_match_clean:
        if not aoi:
            warnings.warn(f'Target/distractor a span without markers not found in the text for question {question_id}. '
                          f'Please check that the span has been copied correctly in the excel!', stacklevel=2)
            print(f'AOI file NOT annotated with target/distractor a spans for question {question_id}.')
    else:
        target_begin_index = target_span_match_clean.start()
        target_end_index = target_span_match_clean.end()

        before_span = ['x' for _ in range(target_begin_index)]
        in_span = [i for i in range(target_end_index - target_begin_index)]
        after_span = ['x' for _ in range(len(text) - target_end_index)]

        target_span_marked = before_span + in_span + after_span

    if distractor_span and not distractor_span_match_clean:
        if not aoi:
            warnings.warn(
                f'Distractor b span without markers not found in the text without annotation for question {question_id}. '
                f'Please check that the span has been copied correctly in the excel!', stacklevel=2)
            print(f'AOI file NOT annotated with distractor b spans for question {question_id}.')
    elif distractor_span and distractor_span_match_clean:
        distractor_begin_index = distractor_span_match_clean.start()
        distractor_end_index = distractor_span_match_clean.end()

        before_span = ['x' for _ in range(distractor_begin_index)]
        in_span = [i for i in range(distractor_end_index - distractor_begin_index)]
        after_span = ['x' for _ in range(len(text) - distractor_end_index)]

        distractor_span_marked = before_span + in_span + after_span

    else:
        distractor_span_marked = ['x' for _ in range(len(text))]

    chars = [char for char in text]

    return target_span_marked, distractor_span_marked, chars


def create_stimuli_images():
    if os.path.isfile(image_config.REPO_ROOT / image_config.STIMULI_FILE_PATH):
        create_images(
            image_config.REPO_ROOT / image_config.STIMULI_FILE_PATH,
            image_config.REPO_ROOT / image_config.QUESTION_FILE_PATH,
            draw_aoi=False
        )

        create_images(
            image_config.REPO_ROOT / image_config.STIMULI_FILE_PATH,
            image_config.REPO_ROOT / image_config.QUESTION_FILE_PATH,
            draw_aoi=True
        )
    else:
        warnings.warn(
            f'No excel file for stimuli found at {image_config.REPO_ROOT / image_config.STIMULI_FILE_PATH}. '
            f'No stimuli images will be created.'
        )

    # check whether excel for other screens exists
    if os.path.isfile(image_config.REPO_ROOT / image_config.OTHER_SCREENS_FILE_PATH):

        create_other_screens(draw_aoi=False)

    else:
        print(
            f'No excel file for other screens found at {image_config.REPO_ROOT / image_config.OTHER_SCREENS_FILE_PATH}. '
            f'No other screens will be created.'
        )

    # create randomization file for the stimuli
    # read the stimulus order version from the global config and select the versions ranging from
    # image_config.VERSION_START to image_config.NUM_PERMUTATIONS + image_config.VERSION_START
    all_versions_df = pd.read_csv(image_config.INITIAL_RANDOMIZATION_CSV, sep=',', encoding='UTF-8')

    if image_config.SUBCORPUS == 'aging':
        all_versions_df = get_stimulus_randomization_orders(all_versions_df)

    # if there are not enough versions in the initial randomization csv, copy and append the df and increase the version
    # number until we have num permutations
    while len(all_versions_df) <= image_config.NUM_PERMUTATIONS:
        all_versions_df = pd.concat([all_versions_df, all_versions_df.assign(version_number=all_versions_df['version_number'] + len(all_versions_df))])

    # get those entries between the version start and the number of permutations + version start
    language_versions_df = all_versions_df[all_versions_df['version_number'].between(
        image_config.VERSION_START, image_config.NUM_PERMUTATIONS + image_config.VERSION_START,
        inclusive='left'
    )]

    language_versions_df.to_csv(
        image_config.REPO_ROOT / image_config.OUTPUT_TOP_DIR / 'config' /
        f'stimulus_order_versions_{image_config.SUBCORPUS + "_" if image_config.SUBCORPUS else ""}{image_config.LANGUAGE}_'
        f'{image_config.COUNTRY_CODE}_{image_config.LAB_NUMBER}.csv',
        sep=',',
        index=False
    )

    path_for_config = (image_config.OUTPUT_TOP_DIR + 'config' +
                       f'/stimulus_order_versions_{image_config.SUBCORPUS + "_" if image_config.SUBCORPUS else ""}{image_config.LANGUAGE}_'
                       f'{image_config.COUNTRY_CODE}_{image_config.LAB_NUMBER}.csv').replace('\\', '/')

    CONFIG.setdefault('PATHS', {}).update(
        {
            'stimulus_order_versions_csv': path_for_config
        }
    )


def draw_text(text: str, image: Image, fontsize: int, draw_aoi: bool = False,
              spacing: int = image_config.LINE_SPACING, image_short_name: str = None,
              anchor_x_px: int = None,
              anchor_y_px: int = None,
              text_width_px: int = None,
              text_height_px: int = None,
              script_direction: str = image_config.SCRIPT_DIRECTION,
              question_option_type: str | None = None,
              word_split_criterion: str = ' ',
line_limit: int = image_config.NUM_LINES_PER_PAGE, character_limit: int = None,
               latin_font_path: str = None, latin_box: str = None,
               center_in_box: bool = False) -> (list[list], list):
    """
    Draws text on an image and creates aoi boxes for each letter
    :param text: str
        text to draw on the image
    :param image: Image
        a previously created Pillow Image object
    :param fontsize: int
        the height of the font in pixels
    :param draw_aoi: bool
        Whether to draw aoi boxes around each letter
    :param spacing:
        spacing between the lines of the text in. Will be multiplied with the font size
    :param image_short_name: str
       the image short name is the name of the image that is currently being created
    :param anchor_x_px: int
        the top left corner x coordinate of the text
    :param anchor_y_px: int
        the top left corner y coordinate of the text
    :param text_width_px: int
        the width of the text in pixels
    :param script_direction: str
        the direction of the script, either 'ltr' or 'rtl'
    :param question_option_type: str
        if the text is a question option, the type of the question option, e.g. 'left', 'up', 'right', 'down'
    :param word_split_criterion:
        defines where to split words in the input text. Default '\\s' means split at white spaces. None will split each
        character separately.
    :param line_limit: int
        how many lines are allowed on the image. If more, a warning will be raised but the image will still be created!
    :param character_limit: int
        how many characters are allowed on each line. Mutally exclusive with text_width_px

    :return: list[list], list
        the first list contains a list for each character aoi together with the information about the size and position
        the second list contains all words in text order as many times as there are characters in the word
    """
    script_direction = script_direction.lower()
    if script_direction not in ['ltr', 'rtl', 'ttb']:
        raise ValueError(f'Script direction must be one of ltr, rtl, ttb, not {script_direction}')

    # Anchor default depends on the requested script direction, not on the
    # lab config (which may describe a different direction in tests).
    if anchor_x_px is None:
        anchor_x_px = (
            image.width - image_config.MIN_MARGIN_RIGHT_PX if script_direction == 'ttb'
            else image_config.ANCHOR_POINT_X_PX
        )
    if anchor_y_px is None:
        anchor_y_px = image_config.ANCHOR_POINT_Y_PX

    if script_direction == 'ttb':
        if not _HAS_VERTICAL:
            raise RuntimeError('ttb rendering requires uharfbuzz and freetype-py')
        return _draw_text_ttb(
            text=text, image=image, fontsize=fontsize, draw_aoi=draw_aoi,
            spacing=spacing, image_short_name=image_short_name,
            anchor_x_px=anchor_x_px, anchor_y_px=anchor_y_px,
            text_width_px=text_width_px, text_height_px=text_height_px, script_direction=script_direction,
            word_split_criterion=word_split_criterion, line_limit=line_limit,
            latin_font_path=latin_font_path, latin_box=latin_box,
            center_in_box=center_in_box,
        )

    if not text_width_px and not character_limit:
        character_limit = image_config.MAX_CHARS_PER_LINE
    elif text_width_px and character_limit:
        raise ValueError('Only one of text_width_px and character_limit can be set')

    # Create a drawing object on the given image
    draw = ImageDraw.Draw(image)
    if getattr(image_config, 'DEBUG_MARGIN', False):
        m = image_config
        draw.rectangle([0, 0, m.MIN_MARGIN_LEFT_PX, m.IMAGE_HEIGHT_PX], fill=(255, 220, 220), outline=(255, 0, 0), width=1)
        draw.rectangle([m.IMAGE_WIDTH_PX - m.MIN_MARGIN_RIGHT_PX, 0, m.IMAGE_WIDTH_PX, m.IMAGE_HEIGHT_PX], fill=(255, 220, 220), outline=(255, 0, 0), width=1)
        draw.rectangle([0, 0, m.IMAGE_WIDTH_PX, m.MIN_MARGIN_TOP_PX], fill=(220, 220, 255), outline=(0, 0, 255), width=1)
        draw.rectangle([0, m.IMAGE_HEIGHT_PX - m.MIN_MARGIN_BOTTOM_PX, m.IMAGE_WIDTH_PX, m.IMAGE_HEIGHT_PX], fill=(220, 220, 255), outline=(0, 0, 255), width=1)

    font = ImageFont.truetype(str(image_config.REPO_ROOT / image_config.FONT_TYPE), fontsize)

    text = normalize_render_text(text)

    try:
        paragraphs = re.split(r'\n+', text.strip())
    except AttributeError as e:
        print(text, image_short_name)
        raise e

    aois = []
    all_words = []
    line_idx = 0
    all_lines = []

    word_idx = 0
    aoi_idx = 0
    quote_open = False  # tracks open/close quote state across paragraphs on this page

    # Tracks how far down the page the text actually reaches, so we can warn only if it
    # really crosses into the bottom margin, instead of predicting from a line count.
    text_start_y_px = anchor_y_px
    line_height = sum(font.getmetrics())
    last_line_bottom_px = text_start_y_px

    for paragraph in paragraphs:
        if word_split_criterion == '':
            words_in_paragraph = [char.strip() for char in paragraph]
            character_limit = None
            if not text_width_px:
                text_width_px = image_config.TEXT_WIDTH_PX
        elif word_split_criterion == ' ':
            words_in_paragraph = paragraph.split()
        else:
            words_in_paragraph = paragraph.split(word_split_criterion)

        if image_config.LANGUAGE in ('fa', 'ar'):
            words_in_paragraph, quote_open = arabic_farsi.normalize_quote_pairing(
                words_in_paragraph, quote_open
            )
            arabic_farsi.reverse_ltr_runs(words_in_paragraph)
        elif image_config.LANGUAGE == 'he':
            hebrew.reorder_ltr_runs(words_in_paragraph)
            hebrew.merge_prefix_gap(words_in_paragraph)
            hebrew.fix_cost_parens(words_in_paragraph)
        line = ""
        lines = []

        latin_word = ''
        in_latin_word = False
        # create lines based on image margins
        for word in words_in_paragraph:

            left, top, right, bottom = draw.multiline_textbbox(
                (0, 0), line + word, font=font
            )
            text_width = right - left

            if character_limit:
                if len(line) + len(word) > character_limit:
                    lines.append(line.strip())
                    line = word + word_split_criterion
                else:
                    line += word.strip() + word_split_criterion
            else:
                # chinese is a special case
                if image_config.LANGUAGE in ('zh', 'ja'):
                    # for chinese a word is a single character, if it is not a chinese character but a latin one,
                    # we will treat it differently
                    if not re.match(r'[\u4e00-\u9fff|\uFF1F|\u3000-\u303f|0-9|\u2014]', word):
                        # if not re.match(r'[\u4e00-\u9fff|\u3000-\u303f|0-9|\u2014]', word):
                        in_latin_word = True
                        if word == '':
                            latin_word += ' '
                        else:
                            latin_word += word
                        continue

                if in_latin_word:
                    # if the latin word is just one char, we treat it like the Chinese ones, happens for example with
                    # semicolons or quotation marks
                    if len(latin_word) > 1:
                        # check whether we can append the latin word to the line
                        left, top, right, bottom = draw.multiline_textbbox(
                            (0, 0), line + latin_word, font=font
                        )
                        text_width = right - left

                        if text_width < text_width_px:
                            line += latin_word
                        else:
                            lines.append(line.strip())
                            line = latin_word
                        in_latin_word = False
                        latin_word = ''

                    else:
                        word = latin_word + word
                        latin_word = ''
                        in_latin_word = False
                    # check whether the current word can be appended
                    left, top, right, bottom = draw.multiline_textbbox(
                        (0, 0), line + latin_word, font=font
                    )
                    text_width = right - left

                if text_width < text_width_px:
                    # if there is a latin word before the word latin word will be a space which is added after it
                    line += latin_word + word.strip() + word_split_criterion
                else:
                    lines.append(line.strip())
                    line = word + word_split_criterion

                latin_word = ''

        if latin_word:
            line += latin_word
        lines.append(line.strip())

        for line in lines:

            if len(line) == 0:
                continue

            all_lines.append(line)

            # for chinese we need to split the line into chars later and do not want to split at spaces
            if image_config.LANGUAGE in ('zh', 'ja'):
                words_in_line = [line]
            else:
                words_in_line = line.split()
            x_word = anchor_x_px

            # get metrics returns the ascent and descent of the font from the baseline
            line_height = font.getmetrics()[0] + font.getmetrics()[1]
            # calculate aoi boxes for each letter
            top_left_corner_x_letter = anchor_x_px
            words = []

            char_idx_in_line = 0
            word_idx_in_line = 0
            prev_word_left_overflow = 0

            stop_bold = False
            for word_number, word in enumerate(words_in_line):
                if word.startswith('**'):
                    font = ImageFont.truetype(str(image_config.REPO_ROOT / image_config.FONT_TYPE_BOLD), fontsize)
                    word = word[2:]

                bold_close = re.search(r'\*\*(\W*)$', word)
                if bold_close:
                    stop_bold = True
                    word = word[:bold_close.start()] + bold_close.group(1)

                # A prefix glued directly onto a bold-marked word (e.g. Hebrew 'ה**word**'
                # with no space between the prefix and the marker) leaves one '**' marker
                # in the middle of the token, since the checks above only look at the
                # token's edges. Split it out so the prefix and the bold word can each be
                # drawn in their own font.
                mid_bold_split = None
                if image_config.LANGUAGE not in ('fa', 'ar') and '**' in word:
                    mid_bold_split = word.index('**')
                    word = word[:mid_bold_split] + word[mid_bold_split + 2:]

                # add a space before the word if it is in the middle of a line or the last word
                # this is to make sure that white space belong to the following word in reading order
                if word_number != 0:
                    word = word_split_criterion + word
                    if mid_bold_split is not None:
                        mid_bold_split += len(word_split_criterion)

                word_left, word_top, word_right, word_bottom = draw.multiline_textbbox(
                    (0, 0), word, font=font
                )

                word_width = word_right - word_left

                if image_config.LANGUAGE in ('fa', 'ar'):
                    # put this in functions to keep the code here more legible
                    (current_x, aoi_idx, char_idx_in_line, word_idx_in_line,
                     chars_added, word_stripped, prev_word_left_overflow) = arabic_farsi.render_rtl_word(
                        draw, word, word_number, words_in_line, x_word,
                        anchor_y_px, font, fontsize, line_height,
                        aoi_idx, char_idx_in_line, line_idx, image_short_name,
                        word_idx, word_idx_in_line, draw_aoi, aois,
                        prev_word_left_overflow,
                    )
                    top_left_corner_x_letter = current_x
                    word_idx += 1
                    x_word = current_x
                    if word_number == 0:
                        words.extend([word_stripped for _ in range(chars_added)])
                    else:
                        words.extend([pd.NA] + [word_stripped for _ in range(chars_added)])
                    if stop_bold:
                        font = ImageFont.truetype(str(image_config.REPO_ROOT / image_config.FONT_TYPE), fontsize)
                        stop_bold = False


                else:
                    chars_to_render = list(word)

                    if mid_bold_split is not None:
                        bold_font = ImageFont.truetype(
                            str(image_config.REPO_ROOT / image_config.FONT_TYPE_BOLD), fontsize
                        )
                        prefix_char_count = mid_bold_split
                        char_fonts = (
                            [font] * prefix_char_count
                            + [bold_font] * (len(chars_to_render) - prefix_char_count)
                        )
                        font = bold_font
                    else:
                        char_fonts = [font] * len(chars_to_render)

                    # Tracks the most recently drawn non-mark character, so a Hebrew
                    # niqqud mark (see hebrew.is_combining_mark) can be positioned
                    # against it instead of occupying a cell of its own.
                    prev_base_char = None
                    prev_base_x = None
                    prev_base_y = None
                    prev_base_font = None

                    for char_idx, char in enumerate(chars_to_render):
                        char_font = char_fonts[char_idx]

                        aoi_y = anchor_y_px

                        # In RTL context, bracket/paren glyphs must be visually mirrored
                        # so they open toward the content (e.g. '(' → ')' when drawn RTL).
                        glyph = arabic_farsi.BIDI_MIRROR.get(char, char) if script_direction == 'rtl' else char

                        # A Hebrew niqqud mark attaches to the previously drawn letter
                        # rather than occupying its own cell: no AOI box, no cursor
                        # advance, no width measurement -- the font's own mark
                        # positioning is unreliable for several base letters (see
                        # hebrew.draw_mark), so it's drawn separately using plain
                        # pixel measurements against that letter's ink instead.
                        if image_config.LANGUAGE == 'he' and hebrew.is_combining_mark(char):
                            if prev_base_char is not None:
                                hebrew.draw_mark(
                                    draw, glyph, prev_base_char, prev_base_x, prev_base_y,
                                    prev_base_font, image_config.TEXT_COLOR
                                )
                            continue

                        _, _, letter_width, _ = char_font.getbbox(char, anchor='la')
                        if script_direction == 'rtl':
                            aoi_x = top_left_corner_x_letter - letter_width
                        else:
                            aoi_x = top_left_corner_x_letter

                        if draw_aoi:
                            draw.rectangle(
                                (aoi_x, aoi_y,
                                 aoi_x + letter_width,
                                 aoi_y + line_height),
                                outline='red', width=1
                            )

                        aoi_letter = [
                            aoi_idx, char, aoi_x, aoi_y,
                            letter_width, line_height,
                            char_idx_in_line, line_idx, image_short_name, word_idx, word_idx_in_line
                        ]

                        # update top left corner x for next letter
                        if script_direction == 'rtl':
                            top_left_corner_x_letter -= letter_width
                        else:
                            top_left_corner_x_letter += letter_width

                        aois.append(aoi_letter)

                        char_idx_in_line += 1
                        aoi_idx += 1

                        draw.text(
                            (aoi_x, aoi_y), glyph, fill=image_config.TEXT_COLOR,
                            font=char_font, anchor='la'
                        )
                        if image_config.LANGUAGE == 'he':
                            prev_base_char, prev_base_x, prev_base_y, prev_base_font = (
                                glyph, aoi_x, aoi_y, char_font
                            )

                    word_idx_in_line += 1
                    word_idx += 1

                    stripped = word.strip()
                    if image_config.LANGUAGE == 'he':
                        # Niqqud marks don't get their own AOI entry (see the
                        # per-character loop above), so only count characters that do.
                        n_chars = sum(1 for c in stripped if not hebrew.is_combining_mark(c))
                    else:
                        n_chars = len(stripped)
                    if word_number == 0:
                        words.extend([stripped for _ in range(n_chars)])
                    else:
                        words.extend([pd.NA] + [stripped for _ in range(n_chars)])

                    if stop_bold:
                        font = ImageFont.truetype(str(image_config.REPO_ROOT / image_config.FONT_TYPE), fontsize)
                        stop_bold = False

                    x_word = x_word + word_width if script_direction == 'ltr' else x_word - word_width

            all_words.extend(words)
            last_line_bottom_px = anchor_y_px + line_height
            anchor_y_px += line_height * spacing
            line_idx += 1

    # line_limit lines means (line_limit - 1) full line pitches between lines, plus the
    # last line's own height -- not line_limit full pitches, which would reserve an unused
    # trailing gap and warn a line too early.
    allowed_bottom_px = text_start_y_px + (line_limit - 1) * line_height * spacing + line_height
    if last_line_bottom_px > allowed_bottom_px and not draw_aoi:
        warnings.warn(
            f'Text for {image_short_name} extends past its {line_limit}-line allotment: '
            f'ends at {last_line_bottom_px:.0f}px, allotted up to {allowed_bottom_px:.0f}px'
        )

    overlong_questions = []
    if question_option_type and not draw_aoi:
        # add too long question options to file
        with open(image_config.REPO_ROOT / image_config.OUTPUT_TOP_DIR / 'overlong_question_options.txt', 'a',
                  encoding='utf8') as f:

            # check if the options contain a line break. If yes, we need to include it first
            if text.count('\n') > 0:
                raise ValueError(f'Question option contains line break: {image_short_name}, please remove it.')

            num_lines = len(all_lines)
            num_words = len(text.split())
            num_chars = len(text.strip())
            if question_option_type in ('left', 'right'):
                # count only the lines with text
                if image_config.LANGUAGE == 'kl' and num_lines > 5:
                    if not image_short_name in overlong_questions:
                        overlong_questions.append(image_short_name)
                        warnings.warn(
                            f'Question options that do not fit:\n{image_short_name},{num_lines} lines,{num_words} words,{num_chars} chars'
                        )
                        f.write(f'Question option too long for left/right box for {image_short_name}\n\n')

                elif image_config.LANGUAGE != 'kl' and num_lines > 3:
                    if not image_short_name in overlong_questions:
                        overlong_questions.append(image_short_name)
                        warnings.warn(
                            f'Question options that do not fit:\n{image_short_name},{num_lines} lines,{num_words} words,{num_chars} chars'
                        )
                        f.write(f'Question option too long for left/right box for {image_short_name}\n\n')
            else:
                if num_lines > 2:
                    if not image_short_name in overlong_questions:
                        overlong_questions.append(image_short_name)
                        warnings.warn(
                            f'Question options that do not fit:\n{image_short_name},{num_lines} lines,{num_words} words,{num_chars} chars'
                        )
                        f.write(f'Question option too long for top/bottom box for {image_short_name}\n\n')

    # draw fixation point
    r = image_config.FIX_DOT_RADIUS_PX
    fix_x = image_config.POS_BOTTOM_DOT_X_PX
    fix_y = image_config.POS_BOTTOM_DOT_Y_PX
    draw.ellipse(
        (fix_x - r, fix_y - r, fix_x + r, fix_y + r),
        fill=None,
        outline=image_config.TEXT_COLOR,
        width=image_config.FIX_DOT_WIDTH_PX
    )

    return aois, all_words


def create_welcome_screen(image: Image, text: str) -> None:
    """
    Creates a welcome screen with a white background, all the logos and a blue greeting in the middle of the screen.
    """
    root = Path(__file__).parent.parent
    # We have three different logos - load them and change the size if needed
    cost_logo = Image.open(root / "logo_imgs/cost_logo.jpg")
    cost_width, cost_height = cost_logo.size
    cost_ratio = cost_height / cost_width
    # TODO fix this at some point (the logos are distorted)
    # cost_logo_new_size = (
    #     int((max(cost_width // image_config.IMAGE_WIDTH_PX, 1)) * image_config.MIN_MARGIN_LEFT_PX * 1.5),
    #     int((max(cost_width // image_config.IMAGE_WIDTH_PX, 1)) * image_config.MIN_MARGIN_LEFT_PX * 1.5 * cost_ratio)
    # )
    cost_logo_new_size = (
        int(image_config.MIN_MARGIN_LEFT_PX * 2.5),
        int(image_config.MIN_MARGIN_LEFT_PX * 2.5 * cost_ratio)
    )

    cost_logo = cost_logo.resize(cost_logo_new_size)

    eu_logo = Image.open(root / "logo_imgs/eu_fund_logo.png")
    eu_width, eu_height = eu_logo.size
    eu_ratio = eu_height / eu_width

    # eu_logo_new_size = (
    #     int((max(eu_width // image_config.IMAGE_WIDTH_PX, 1)) * image_config.MIN_MARGIN_LEFT_PX * 2),
    #     int((max(eu_width // image_config.IMAGE_WIDTH_PX, 1)) * image_config.MIN_MARGIN_LEFT_PX * 2 * eu_ratio)
    # )
    eu_logo_new_size = (
        int(image_config.MIN_MARGIN_LEFT_PX * 5),
        int(image_config.MIN_MARGIN_LEFT_PX * 5 * eu_ratio)
    )

    eu_logo = eu_logo.resize(eu_logo_new_size)

    multipleye_logo = Image.open(root / "logo_imgs/logo_multipleye.png")

    text = normalize_render_text(text)

    # Set the text
    our_blue = "#007baf"
    font_size_title = image_config.FONT_SIZE_PX * 1.8
    font_size_text = image_config.FONT_SIZE_PX * 1.2
    font_type = str(image_config.REPO_ROOT / image_config.FONT_TYPE)

    # Create a drawing object
    draw = ImageDraw.Draw(image)

    # Create coordinates for three different logos
    multipleye_logo_x = (image.width - multipleye_logo.width) // 2
    multipleye_logo_y = image_config.ANCHOR_POINT_Y_PX // 7
    multipleye_logo_position = (multipleye_logo_x, multipleye_logo_y)
    eu_logo_x = image_config.MIN_MARGIN_LEFT_PX // 2
    eu_logo_y = image.height - image_config.MIN_MARGIN_BOTTOM_PX // 2 - eu_logo.height
    eu_logo_position = (eu_logo_x, eu_logo_y)
    cost_logo_x = image.width - image_config.MIN_MARGIN_LEFT_PX // 2 - cost_logo.width
    cost_logo_y = image.height - image_config.MIN_MARGIN_BOTTOM_PX // 2 - cost_logo.height
    cost_logo_position = (cost_logo_x, cost_logo_y)

    # Paste the logos onto the final image at the calculated coordinates
    image.paste(
        multipleye_logo, multipleye_logo_position, mask=multipleye_logo
    )
    image.paste(eu_logo, eu_logo_position, mask=eu_logo)
    image.paste(cost_logo, cost_logo_position)

    texts = text.split('\n')
    rtl_kwargs = rtl_draw_kwargs()

    text_y = image_config.IMAGE_HEIGHT_PX // 2
    for idx, t in enumerate(texts):
        # title is bigger
        if idx == 0:
            font = ImageFont.truetype(font_type, font_size_title)

        else:
            font = ImageFont.truetype(font_type, font_size_text)

        left, top, right, bottom = draw.multiline_textbbox(
            (0, 0), t, font=font, **rtl_kwargs
        )

        text_width, text_height = right - left, bottom - top

        # if the text is too long for one line, split it into two lines
        if text_width > image_config.IMAGE_WIDTH_PX:
            lines = []
            elements = t.split(image_config.WORD_SPLIT_CRITERION)

            line = ''

            for element in elements:
                left, top, right, bottom = draw.multiline_textbbox(
                    (0, 0), line + element, font=font, **rtl_kwargs
                )
                width = right - left

                if width < image_config.IMAGE_WIDTH_PX:
                    line += element + image_config.WORD_SPLIT_CRITERION
                else:
                    lines.append(line.strip())
                    line = element + image_config.WORD_SPLIT_CRITERION
            lines.append(line.strip())

            for line in lines:
                left, top, right, bottom = draw.multiline_textbbox(
                    (0, 0), line, font=font, **rtl_kwargs
                )
                text_width, text_height = right - left, bottom - top

                text_x = (image_config.IMAGE_WIDTH_PX - text_width) // 2
                draw.text((text_x, text_y), line, font=font, fill=our_blue, **rtl_kwargs)
                text_y += text_height * 1.5

        else:
            text_x = (image_config.IMAGE_WIDTH_PX - text_width) // 2
            draw.text((text_x, text_y), t, font=font, fill=our_blue, **rtl_kwargs)
            text_y += text_height * 3


def create_fixation_screen(image: Image):
    """
    Creates a fixation screen with a white background and a fixation dot in the top left corner.
    """
    # Create a drawing object
    draw = ImageDraw.Draw(image)

    # The fixation dot is positioned a bit left to the first char in the middle of the line
    r = image_config.FIX_DOT_RADIUS_PX
    fix_x = image_config.POS_TOP_DOT_X_PX
    fix_y = image_config.POS_TOP_DOT_Y_PX

    draw.ellipse(
        (fix_x - r, fix_y - r, fix_x + r, fix_y + r),
        fill=None,
        outline=image_config.TEXT_COLOR,
        width=image_config.FIX_DOT_WIDTH_PX
    )

    CONFIG.setdefault('IMAGE', {}).update({'FIX_DOT_X': fix_x, 'FIX_DOT_Y': fix_y, 'FIX_DOT_RADIUS': r})


def create_camera_setup_screen(image: Image, text: str):
    """
    Creates a camera setup screen with a white background and five fixation dot in the center and the corners.
    """
    draw_text(text, image, image_config.FONT_SIZE_PX, draw_aoi=False, line_limit=12,
              word_split_criterion=image_config.WORD_SPLIT_CRITERION, )


def create_final_screen(image: Image, text: str):
    """
    Creates a final screen with a white background, one logo and a blue messages in the middle of the screen.
    """
    root = Path(__file__).parent.parent
    multipleye_logo = Image.open(root / "logo_imgs/logo_multipleye.png")

    text = normalize_render_text(text)

    final_text = text.split('\n')

    our_blue = "#007baf"
    our_red = "#b94128"
    # font_size = 38
    font_size = image_config.FONT_SIZE_PX * 1.4

    font_type = str(image_config.REPO_ROOT / image_config.FONT_TYPE)

    # Create a drawing object
    draw = ImageDraw.Draw(image)

    # Create coordinates for three different logos
    multipleye_logo_x = (image.width - multipleye_logo.width) // 2
    multipleye_logo_y = image_config.ANCHOR_POINT_Y_PX // 7
    multipleye_logo_position = (multipleye_logo_x, multipleye_logo_y)

    # Paste the logos onto the final image at the calculated coordinates
    image.paste(
        multipleye_logo, multipleye_logo_position, mask=multipleye_logo
    )
    # final_image.paste(eu_logo, eu_logo_position, mask = eu_logo)
    # final_image.paste(cost_logo, cost_logo_position)

    # Paste the texts onto the final image
    font = ImageFont.truetype(font_type, font_size)
    rtl_kwargs = rtl_draw_kwargs()
    text_y = 0
    text_x = 0
    for paragraph in final_text:
        left, top, right, bottom = draw.multiline_textbbox(
            (0, 0), paragraph, font=font, **rtl_kwargs
        )
        text_width, text_height = right - left, bottom - top
        if not text_x:
            text_x = (image_config.IMAGE_WIDTH_PX - text_width) // 2
            text_y = (image_config.IMAGE_HEIGHT_PX - text_height) // 2
        else:
            text_x = (image_config.IMAGE_WIDTH_PX - text_width) // 2
            text_y += text_width

        draw.text((text_x, text_y), paragraph, font=font, fill=our_blue, **rtl_kwargs)


def create_rating_screens(image: Image, text: str, title: str):
    sentences = text.split('\n')
    question = sentences[0]
    options = sentences[1:]

    draw_text(question, image, image_config.FONT_SIZE_PX, draw_aoi=False, line_limit=12,
              word_split_criterion=image_config.WORD_SPLIT_CRITERION, )

    font = ImageFont.truetype(str(image_config.REPO_ROOT / image_config.FONT_TYPE), image_config.FONT_SIZE_PX)

    if image_config.SCRIPT_DIRECTION == 'ttb':
        # Vertical: question at top right, answers 1..5 each as a column right-to-left, spaced a bit more than usual
        col_advance = int(image_config.FONT_SIZE_PX * image_config.LINE_SPACING)
        gap = int(col_advance * 1.35)  # a bit more than usual
        valid_options = [o for o in options if not (o.isspace() or o == '')]
        n = len(valid_options)
        total_width = n * image_config.FONT_SIZE_PX + (n - 1) * gap if n else 0
        block_left = image_config.MIN_MARGIN_LEFT_PX + (image_config.TEXT_WIDTH_PX - total_width) // 2
        block_right = block_left + total_width
        option_y_px = image_config.MIN_MARGIN_TOP_PX
        avail_h = image_config.IMAGE_HEIGHT_PX - option_y_px - image_config.MIN_MARGIN_BOTTOM_PX
        option_width = image_config.FONT_SIZE_PX  # single column width
        option_height = avail_h
        y_step = None
    else:
        option_width = image_config.IMAGE_WIDTH_PX * 0.4
        if image_config.SCRIPT_DIRECTION == 'rtl':
            # Anchor is the right edge of the text area; box extends leftward
            option_x_px = image_config.IMAGE_WIDTH_PX - 1.2 * image_config.MIN_MARGIN_RIGHT_PX
        else:
            option_x_px = 1.2 * image_config.MIN_MARGIN_LEFT_PX
        option_y_px = 3.1 * image_config.MIN_MARGIN_TOP_PX
        y_step = image_config.MIN_MARGIN_TOP_PX

    option_idx = 1
    ttb_col_idx = 0
    for option in options:
        # empty lines and spaces only are excluded
        if option.isspace() or option == '':
            continue
        if image_config.SCRIPT_DIRECTION == 'ttb':
            col_left = block_right - (ttb_col_idx + 1) * image_config.FONT_SIZE_PX - ttb_col_idx * gap
            col_anchor = col_left + image_config.FONT_SIZE_PX  # right edge for ttb
            # Rating options are "1 – 0%" (prefix, dash, suffix). The prefix digit is set
            # upright. the numeric/percentage suffix (0%, 25%, 100%) is set horizontally.
            # The dash comes from the input file and is rendered as-is (its optimal form in
            # vertical text is still under discussion).
            m = re.search(f"[{re.escape('–—-')}]", option)
            if m and title in ("familiarity_rating_screen_1", "familiarity_rating_screen_2", "subject_difficulty_screen"):
                dash_idx = m.start()
                dash_char = option[dash_idx]
                prefix = option[:dash_idx].strip()
                suffix = option[dash_idx + 1:].strip()
                pen_y = option_y_px
                font_path = str(image_config.REPO_ROOT / image_config.FONT_TYPE)
                pil_font = ImageFont.truetype(font_path, image_config.FONT_SIZE_PX)
                draw = ImageDraw.Draw(image)
                # prefix (e.g. "1") upright, one cell per character
                for ch in prefix:
                    if ch == ' ':
                        pen_y += image_config.FONT_SIZE_PX // 3
                        continue
                    draw.text((col_left + image_config.FONT_SIZE_PX // 2, pen_y + image_config.FONT_SIZE_PX // 2),
                              ch, fill=image_config.TEXT_COLOR, font=pil_font, anchor='mm')
                    pen_y += image_config.FONT_SIZE_PX
                # dash as in the input file, rendered vertically (rotated 90 degrees)
                if dash_char:
                    tmp_w = image_config.FONT_SIZE_PX + 10
                    tmp_h = image_config.FONT_SIZE_PX + 10
                    tmp_img = Image.new('L', (tmp_w, tmp_h), 0)
                    tmp_draw = ImageDraw.Draw(tmp_img)
                    tmp_draw.text((tmp_w // 2, tmp_h // 2), dash_char, fill=255, font=pil_font, anchor='mm')
                    rot = tmp_img.rotate(90, expand=True, resample=Image.BICUBIC)
                    bbox = rot.getbbox()
                    if bbox:
                        rot_c = rot.crop(bbox)
                        rw, rh = rot_c.size
                        gx = col_left + (image_config.FONT_SIZE_PX - rw) // 2
                        gy = pen_y + (image_config.FONT_SIZE_PX - rh) // 2
                        image.paste(Image.new('RGB', (rw, rh), image_config.TEXT_COLOR), (gx, gy), rot_c)
                    pen_y += image_config.FONT_SIZE_PX
                # suffix: numeric/percentage -> horizontal; otherwise vertical Japanese
                if suffix:
                    is_numeric_suffix = bool(re.fullmatch(r"[0-9%％\s]+", suffix)) and any(c.isdigit() for c in suffix)
                    if is_numeric_suffix:
                        w = pil_font.getlength(suffix)
                        x0 = col_left + (image_config.FONT_SIZE_PX - w) / 2
                        y0 = pen_y + image_config.FONT_SIZE_PX // 2
                        draw.text((x0 + w / 2, y0), suffix, fill=image_config.TEXT_COLOR, font=pil_font, anchor='mm')
                    else:
                        remaining_h = avail_h - (pen_y - option_y_px)
                        if remaining_h > 0:
                            draw_text(
                                suffix, image, image_config.FONT_SIZE_PX, draw_aoi=False,
                                anchor_x_px=col_anchor, anchor_y_px=pen_y,
                                text_width_px=image_config.FONT_SIZE_PX, text_height_px=remaining_h,
                                line_limit=1, word_split_criterion=image_config.WORD_SPLIT_CRITERION,
                                center_in_box=False,
                            )
            else:
                draw_text(
                    option, image, image_config.FONT_SIZE_PX, draw_aoi=False,
                    anchor_x_px=col_anchor, anchor_y_px=option_y_px,
                    text_width_px=image_config.FONT_SIZE_PX, text_height_px=avail_h,
                    line_limit=1, word_split_criterion=image_config.WORD_SPLIT_CRITERION,
                    center_in_box=False,
                )
            box_coordinates = (
                col_left - image_config.MIN_MARGIN_LEFT_PX * 0.1,
                option_y_px,
                col_left + image_config.FONT_SIZE_PX + image_config.MIN_MARGIN_LEFT_PX * 0.1,
                option_y_px + avail_h
            )
            ttb_col_idx += 1
        else:
            draw_text(
                option, image, image_config.FONT_SIZE_PX, draw_aoi=False,
                anchor_x_px=option_x_px, anchor_y_px=option_y_px, text_width_px=option_width,
                line_limit=12, word_split_criterion=image_config.WORD_SPLIT_CRITERION,
            )
            draw = ImageDraw.Draw(image)
            text_height = font.getmetrics()[0] + font.getmetrics()[1]
            if image_config.SCRIPT_DIRECTION == 'rtl':
                box_x0 = option_x_px - option_width
                box_x1 = option_x_px + image_config.MIN_MARGIN_RIGHT_PX * 0.1
            else:
                box_x0 = option_x_px - image_config.MIN_MARGIN_LEFT_PX * 0.1
                box_x1 = option_x_px + option_width
            box_coordinates = (
                box_x0,
                option_y_px,
                box_x1,
                option_y_px + text_height
            )

        # draw.rectangle(box_coordinates, outline='black', width=1)

        CONFIG.setdefault('RATING_QUESTION_BOXES', {}).update({f'option_{option_idx}': box_coordinates})

        option_idx += 1

        if image_config.SCRIPT_DIRECTION != 'ttb':
            option_y_px += y_step


def write_final_image_config() -> None:
    """
    Some settings from the image creation need to be imported in the experiment.
    This function writes them to a language config file.
    """

    CONFIG.setdefault('EXPERIMENT', {}).update(
        {
            'LANGUAGE': image_config.LANGUAGE,
            'NUM_PERMUTATIONS': image_config.NUM_PERMUTATIONS,
            'VERSION_START': image_config.VERSION_START,
            'MULTIPLE_DEVICES': image_config.MULTIPLE_DEVICES,
        }
    )

    CONFIG.setdefault('IMAGE', {}).update(
        {
            'FONT_SIZE': image_config.FONT_SIZE_PX,
            'FONT': image_config.FONT_TYPE,
            'FGC': image_config.TEXT_COLOR,
            'IMAGE_BGC': image_config.BACKGROUND_COLOR,
            'IMAGE_WIDTH_PX': image_config.IMAGE_WIDTH_PX,
            'IMAGE_HEIGHT_PX': image_config.IMAGE_HEIGHT_PX,
            'MIN_MARGIN_LEFT_PX': image_config.MIN_MARGIN_LEFT_PX,
            'MIN_MARGIN_RIGHT_PX': image_config.MIN_MARGIN_RIGHT_PX,
            'MIN_MARGIN_TOP_PX': image_config.MIN_MARGIN_TOP_PX,
            'MIN_MARGIN_BOTTOM_PX': image_config.MIN_MARGIN_BOTTOM_PX,
            'IMAGE_SIZE_CM': image_config.IMAGE_SIZE_CM,
            'MAX_CHARS_PER_LINE': image_config.MAX_CHARS_PER_LINE,
            'POS_BOTTOM_DOT_X_PX': image_config.POS_BOTTOM_DOT_X_PX,
            'POS_BOTTOM_DOT_Y_PX': image_config.POS_BOTTOM_DOT_Y_PX,
            'SCRIPT_DIRECTION': image_config.SCRIPT_DIRECTION,
            'COLUMN_ADVANCE_PX': getattr(image_config, 'COLUMN_ADVANCE_PX', None),
            'LATIN_FONT_TYPE': getattr(image_config, 'LATIN_FONT_TYPE', None),
            'LATIN_BOX_TYPE': getattr(image_config, 'LATIN_BOX_TYPE', None),
        }
    )

    CONFIG.setdefault('SCREEN', {}).update(
        {
            'RESOLUTION': image_config.RESOLUTION,
            'SCREEN_SIZE_CM': image_config.SCREEN_SIZE_CM,
            'DISTANCE_CM': image_config.DISTANCE_CM,
        }
    )

    CONFIG.setdefault('PATHS', {}).update(
        {
            'question_file_excel': image_config.QUESTION_FILE_PATH,
            'participant_instruction_excel': image_config.OTHER_SCREENS_FILE_PATH,
            'stimuli_file_excel': image_config.STIMULI_FILE_PATH,
        }
    )

    CONFIG.setdefault('DIRECTORIES', {}).update(
        {
            'question_image_dir': image_config.QUESTION_IMAGE_DIR,
            'image_dir': image_config.IMAGE_DIR,
            'aoi_dir': image_config.AOI_DIR,
            'aoi_question_dir': image_config.AOI_QUESTION_DIR,
            'aoi_image_dir': image_config.AOI_IMG_DIR,
            'other_screens_dir': image_config.OTHER_SCREENS_DIR,
            'output_top_dir': image_config.OUTPUT_TOP_DIR,
        }
    )

    # probably need to refactor this method, but whatever
    config_utils.write_final_config(image_config.FINAL_CONFIG, CONFIG)


def create_other_screens(draw_aoi=False):
    other_screen_df = pd.read_excel(image_config.REPO_ROOT / image_config.OTHER_SCREENS_FILE_PATH)
    other_screen_df.dropna(subset=['instruction_screen_id'], inplace=True)

    if not os.path.isdir(image_config.REPO_ROOT / image_config.OTHER_SCREENS_DIR):
        os.mkdir(image_config.REPO_ROOT / image_config.OTHER_SCREENS_DIR)

    file_names = []
    file_paths = []

    for idx, row in tqdm(
            other_screen_df.iterrows(),
            desc=f'Creating {image_config.LANGUAGE}{" aoi" if draw_aoi else ""} participant instruction images',
            total=len(other_screen_df)
    ):

        final_image = Image.new(
            'RGB', (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX), color=image_config.BACKGROUND_COLOR
        )

        title = row["instruction_screen_name"]
        text = row["instruction_screen_text"]
        # FreeFarsi-Mono lacks U+2013 (en dash); replace with hyphen-minus
        if image_config.LANGUAGE in ('ar', 'fa') and isinstance(text, str):
            text = text.replace('\u2013', '-')

        if title == "welcome_screen":
            create_welcome_screen(final_image, text)

        elif title == "fixation_screen":
            create_fixation_screen(final_image)

        elif title == "camera_setup_screen":
            create_camera_setup_screen(final_image, text)

        elif title == "final_screen":
            create_final_screen(final_image, text)

        elif title == 'familiarity_rating_screen_1':
            create_rating_screens(final_image, text, title)

        elif title == 'subject_difficulty_screen' or title == 'familiarity_rating_screen_2':
            create_rating_screens(final_image, text, title)

        # for all other text screens
        elif title != 'empty_screen':
            if image_config.LANGUAGE == 'kl':
                spacing = 1.7
            else:
                spacing = image_config.LINE_SPACING_INSTRUCTION

            draw_text(text, final_image, image_config.FONT_SIZE_PX - 2, spacing=spacing, draw_aoi=draw_aoi,
                      line_limit=image_config.NUM_LINES_PER_INSTRUCTION_PAGE,
                      word_split_criterion=image_config.WORD_SPLIT_CRITERION, text_width_px=image_config.TEXT_WIDTH_PX,
                      image_short_name=title)

        file_name = f'{title}_{image_config.LANGUAGE}.png'
        file_path = image_config.OTHER_SCREENS_DIR + file_name
        file_names.append(file_name)
        file_paths.append(file_path)

        final_image.save(image_config.REPO_ROOT / image_config.OTHER_SCREENS_DIR / file_name)

    other_screen_df['instruction_screen_img_name'] = file_names
    other_screen_df['instruction_screen_img_path'] = file_paths

    participant_instruction_csv_path = (image_config.OTHER_SCREENS_FILE_PATH[:-5]
                                        + f'{"_aoi" if draw_aoi else ""}_with_img_paths.csv')

    CONFIG.setdefault('PATHS', {}).update(
        {f'participant_instruction{"_aoi" if draw_aoi else ""}_csv': participant_instruction_csv_path}
    )

    other_screen_df.to_csv(
        image_config.REPO_ROOT / participant_instruction_csv_path,
        index=False
    )


if __name__ == '__main__':
    create_stimuli_images()
    write_final_image_config()

    # get_option_span_indices('This is <tb>a test sentence.<te>', '<tb>', '<te>')
