"""Pure unit tests. No data/ or font dependencies.

These test standalone helper functions that can be imported without
triggering image_config's import-time side effects.
"""
from __future__ import annotations

import re
import warnings

import pytest


# ---------------------------------------------------------------------------
# Helpers to import pure functions without triggering image_config
# ---------------------------------------------------------------------------

def _import_normalize_render_text():
    """Import normalize_render_text without importing all of text_to_picture."""
    import importlib
    import types
    from pathlib import Path

    # text_to_picture imports image_config at module level, which triggers
    # side effects.  We pre-create a fake image_config module so the import
    # succeeds without touching the real one.
    REPO_ROOT = Path(__file__).resolve().parent.parent
    fake_ic = types.ModuleType("image_config")
    fake_ic.LANGUAGE = "en"
    fake_ic.REPO_ROOT = REPO_ROOT
    fake_ic.IMAGE_DIR = "dummy/"
    fake_ic.QUESTION_IMAGE_DIR = "dummy/"
    fake_ic.AOI_DIR = "dummy/"
    fake_ic.AOI_QUESTION_DIR = "dummy/"
    fake_ic.AOI_IMG_DIR = "dummy/"
    fake_ic.OUTPUT_TOP_DIR = "dummy/"
    fake_ic.BLOCK_CONFIG_PATH = "dummy/"
    fake_ic.STIMULI_FILE_PATH = "dummy/"
    fake_ic.QUESTION_FILE_PATH = "dummy/"
    fake_ic.OTHER_SCREENS_FILE_PATH = "dummy/"
    fake_ic.OTHER_SCREENS_DIR = "dummy/"
    fake_ic.INITIAL_RANDOMIZATION_CSV = "dummy/"
    fake_ic.NUM_PERMUTATIONS = 10
    fake_ic.VERSION_START = 1
    fake_ic.SUBCORPUS = ""
    fake_ic.COUNTRY_CODE = "X"
    fake_ic.CITY = "X"
    fake_ic.LAB_NUMBER = 1
    fake_ic.YEAR = 1
    fake_ic.TESTING_IMAGES = True
    fake_ic.FONT_TYPE = "fonts/JetBrainsMono-Regular.ttf"
    fake_ic.FONT_TYPE_BOLD = "fonts/JetBrainsMono-ExtraBold.ttf"
    fake_ic.FONT_SIZE_PX = 20
    fake_ic.LINE_SPACING = 2.9
    fake_ic.LINE_SPACING_INSTRUCTION = 2
    fake_ic.WORD_SPLIT_CRITERION = " "
    fake_ic.IMAGE_WIDTH_PX = 1000
    fake_ic.IMAGE_HEIGHT_PX = 700
    fake_ic.TEXT_WIDTH_PX = 800
    fake_ic.TEXT_COLOR = (0, 0, 0)
    fake_ic.BACKGROUND_COLOR = (231, 230, 230)
    fake_ic.MIN_MARGIN_LEFT_PX = 50
    fake_ic.MIN_MARGIN_RIGHT_PX = 50
    fake_ic.MIN_MARGIN_TOP_PX = 50
    fake_ic.MIN_MARGIN_BOTTOM_PX = 80
    fake_ic.ANCHOR_POINT_X_PX = 50
    fake_ic.ANCHOR_POINT_Y_PX = 50
    fake_ic.MAX_CHARS_PER_LINE = 82
    fake_ic.NUM_LINES_PER_PAGE = 10
    fake_ic.NUM_LINES_PER_INSTRUCTION_PAGE = 10
    fake_ic.SCRIPT_DIRECTION = "ltr"
    fake_ic.POS_BOTTOM_DOT_X_PX = 950
    fake_ic.POS_BOTTOM_DOT_Y_PX = 600
    fake_ic.POS_TOP_DOT_X_PX = 40
    fake_ic.POS_TOP_DOT_Y_PX = 60
    fake_ic.FIX_DOT_RADIUS_PX = 7
    fake_ic.FIX_DOT_WIDTH_PX = 5
    fake_ic.ANSWER_OPTION_FOLDER = "dummy/"
    fake_ic.FINAL_CONFIG = "dummy/"
    fake_ic.LAB_CONFIGURATION_PATH = "dummy/"
    import sys
    sys.modules.setdefault("image_config", fake_ic)

    # Also need the subcorpus.aging module that text_to_picture imports
    fake_aging = types.ModuleType("src.subcorpus.aging")
    fake_aging.get_stimulus_randomization_orders = lambda x: x
    sys.modules.setdefault("src", types.ModuleType("src"))
    sys.modules.setdefault("src.subcorpus", types.ModuleType("src.subcorpus"))
    sys.modules.setdefault("src.subcorpus.aging", fake_aging)

    # text_to_picture also imports languages.*, stub those
    for mod_name in ("languages", "languages.arabic_farsi", "languages.hebrew"):
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)
    # text_to_picture calls rtl_draw_kwargs() at module level
    sys.modules["languages.arabic_farsi"].rtl_draw_kwargs = lambda: {}

    from text_to_picture import normalize_render_text
    return normalize_render_text


def _import_checks():
    from utils import checks
    return checks.check_stimulus_types


def _import_config_utils_pure():
    """Import parse_true_false without image_config side effects."""
    import sys, types
    if "image_config" not in sys.modules:
        fake_ic = types.ModuleType("image_config")
        fake_ic.TESTING_IMAGES = True
        sys.modules["image_config"] = fake_ic
    from utils.config_utils import parse_true_false
    return parse_true_false


def _import_get_option_span_indices():
    """Import get_option_span_indices with stubbed image_config."""
    import sys, types
    from pathlib import Path
    REPO_ROOT = Path(__file__).resolve().parent.parent
    for name in ("image_config", "src", "src.subcorpus", "src.subcorpus.aging",
                 "languages", "languages.arabic_farsi", "languages.hebrew"):
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)
    ic = sys.modules["image_config"]
    if not hasattr(ic, "LANGUAGE"):
        ic.LANGUAGE = "en"
    if not hasattr(ic, "REPO_ROOT"):
        ic.REPO_ROOT = REPO_ROOT
    if not hasattr(ic, "FONT_TYPE"):
        ic.FONT_TYPE = "fonts/JetBrainsMono-Regular.ttf"
    if not hasattr(ic, "FONT_TYPE_BOLD"):
        ic.FONT_TYPE_BOLD = "fonts/JetBrainsMono-ExtraBold.ttf"
    if not hasattr(ic, "FONT_SIZE_PX"):
        ic.FONT_SIZE_PX = 20
    if not hasattr(ic, "LINE_SPACING"):
        ic.LINE_SPACING = 2.9
    if not hasattr(ic, "IMAGE_WIDTH_PX"):
        ic.IMAGE_WIDTH_PX = 1000
    if not hasattr(ic, "IMAGE_HEIGHT_PX"):
        ic.IMAGE_HEIGHT_PX = 700
    if not hasattr(ic, "TEXT_WIDTH_PX"):
        ic.TEXT_WIDTH_PX = 800
    if not hasattr(ic, "TEXT_COLOR"):
        ic.TEXT_COLOR = (0, 0, 0)
    if not hasattr(ic, "BACKGROUND_COLOR"):
        ic.BACKGROUND_COLOR = (231, 230, 230)
    if not hasattr(ic, "MIN_MARGIN_LEFT_PX"):
        ic.MIN_MARGIN_LEFT_PX = 50
    if not hasattr(ic, "MIN_MARGIN_RIGHT_PX"):
        ic.MIN_MARGIN_RIGHT_PX = 50
    if not hasattr(ic, "MIN_MARGIN_TOP_PX"):
        ic.MIN_MARGIN_TOP_PX = 50
    if not hasattr(ic, "MIN_MARGIN_BOTTOM_PX"):
        ic.MIN_MARGIN_BOTTOM_PX = 80
    if not hasattr(ic, "ANCHOR_POINT_X_PX"):
        ic.ANCHOR_POINT_X_PX = 50
    if not hasattr(ic, "ANCHOR_POINT_Y_PX"):
        ic.ANCHOR_POINT_Y_PX = 50
    if not hasattr(ic, "MAX_CHARS_PER_LINE"):
        ic.MAX_CHARS_PER_LINE = 82
    if not hasattr(ic, "NUM_LINES_PER_PAGE"):
        ic.NUM_LINES_PER_PAGE = 10
    if not hasattr(ic, "SCRIPT_DIRECTION"):
        ic.SCRIPT_DIRECTION = "ltr"
    if not hasattr(ic, "OUTPUT_TOP_DIR"):
        ic.OUTPUT_TOP_DIR = "dummy/"
    if not hasattr(ic, "WORD_SPLIT_CRITERION"):
        ic.WORD_SPLIT_CRITERION = " "
    if not hasattr(ic, "POS_BOTTOM_DOT_X_PX"):
        ic.POS_BOTTOM_DOT_X_PX = 950
    if not hasattr(ic, "POS_BOTTOM_DOT_Y_PX"):
        ic.POS_BOTTOM_DOT_Y_PX = 600
    if not hasattr(ic, "FIX_DOT_RADIUS_PX"):
        ic.FIX_DOT_RADIUS_PX = 7
    if not hasattr(ic, "FIX_DOT_WIDTH_PX"):
        ic.FIX_DOT_WIDTH_PX = 5
    from text_to_picture import get_option_span_indices
    return get_option_span_indices


# ---------------------------------------------------------------------------
# normalize_render_text
# ---------------------------------------------------------------------------

class TestNormalizeRenderText:
    normalize = staticmethod(_import_normalize_render_text())

    @pytest.mark.parametrize("input_text, expected", [
        ("Hello \ufb01le", "Hello file"),
        ("No ligatures here", "No ligatures here"),
        ("\ufb01 \ufb01 \ufb01", "fi fi fi"),
        ("", ""),
        ("\ufb01rst floor", "first floor"),
        # CJK: no fi ligature, passthrough unchanged
        ("\u5927\u6587\u672c\u65e5\u8a9e\u306e\u30c6\u30ad\u30b9\u30c8",
         "\u5927\u6587\u672c\u65e5\u8a9e\u306e\u30c6\u30ad\u30b9\u30c8"),
        # Arabic: passthrough
        ("\u0627\u0644\u0639\u0631\u0628\u064a\u0629 \u0627\u0644\u0645\u062a\u062c\u0647\u0632\u0629",
         "\u0627\u0644\u0639\u0631\u0628\u064a\u0629 \u0627\u0644\u0645\u062a\u062c\u0647\u0632\u0629"),
        # Hebrew: passthrough
        ("\u05e1\u05e4\u05e8 \u05d8\u05e7\u05e1\u05d8", "\u05e1\u05e4\u05e8 \u05d8\u05e7\u05e1\u05d8"),
        # Mixed CJK + Latin with ligature
        ("\u65e5\u672c\u8a9e\ufb01le\u65e5",
         "\u65e5\u672c\u8a9efile\u65e5"),
    ])
    def test_ligature_expansion(self, input_text, expected):
        assert self.normalize(input_text) == expected


# ---------------------------------------------------------------------------
# parse_true_false
# ---------------------------------------------------------------------------

class TestParseTrueFalse:
    parse = staticmethod(_import_config_utils_pure())

    @pytest.mark.parametrize("value, expected", [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("yes", True),
        ("1", True),
        ("on", True),
        ("false", False),
        ("False", False),
        ("no", False),
        ("0", False),
        ("off", False),
    ])
    def test_valid_boolean_strings(self, value, expected):
        assert self.parse(value) is expected

    def test_invalid_value_raises(self):
        import image_config
        old = image_config.TESTING_IMAGES
        image_config.TESTING_IMAGES = False
        try:
            with pytest.raises(ValueError):
                self.parse("maybe")
        finally:
            image_config.TESTING_IMAGES = old

    def test_invalid_value_warns_in_test_mode(self):
        import image_config
        old = image_config.TESTING_IMAGES
        image_config.TESTING_IMAGES = True
        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                self.parse("invalid")
                assert len(w) == 1
        finally:
            image_config.TESTING_IMAGES = old


# ---------------------------------------------------------------------------
# check_stimulus_types
# ---------------------------------------------------------------------------

class TestCheckStimulusTypes:
    check = staticmethod(_import_checks())

    def test_valid_types(self):
        self.check(["practice", "experiment"])  # should not raise

    def test_wrong_count_raises(self):
        with pytest.raises(ValueError, match="Only two stimulus types"):
            self.check(["practice"])

    def test_wrong_names_raises(self):
        with pytest.raises(ValueError, match="Only two stimulus types"):
            self.check(["practice", "test"])

    @pytest.mark.parametrize("types_list", [
        ["experiment", "practice"],
        ["practice", "experiment"],
    ])
    def test_order_does_not_matter(self, types_list):
        self.check(types_list)  # should not raise


# ---------------------------------------------------------------------------
# get_option_span_indices
# ---------------------------------------------------------------------------

class TestGetOptionSpanIndices:
    get_indices = staticmethod(_import_get_option_span_indices())

    def test_basic_span(self):
        text = "The cat sat on the mat"
        annotated = "The <t1b>cat sat<t1e> on the mat"
        target, distractor, chars = self.get_indices(
            text, annotated, "<t1b>cat sat<t1e>", None, "1", aoi=False
        )
        assert len(target) == len(text)
        assert len(chars) == len(text)
        # Characters 'c','a','t',' ','s','a','t' (indices 4-10) should be marked
        assert all(v == i for i, v in enumerate(target[4:11]))
        # Characters outside span should be 'x'
        assert target[0] == 'x'
        assert target[-1] == 'x'

    def test_no_span_found(self):
        text = "Hello world"
        annotated = "Hello world"
        target, distractor, chars = self.get_indices(
            text, annotated, "<t1b>missing<t1e>", None, "1", aoi=True
        )
        # No match, target should be empty list
        assert target == []

    def test_with_distractor(self):
        text = "The big red fox"
        annotated = "The <t1b>big<t1e> red <d1b>fox<d1e>"
        target, distractor, chars = self.get_indices(
            text, annotated, "<t1b>big<t1e>", "<d1b>fox<d1e>", "1", aoi=False
        )
        assert len(target) == len(text)
        assert all(v == i for i, v in enumerate(target[4:7]))  # "big"
        assert all(v == i for i, v in enumerate(distractor[12:15]))  # "fox"

    def test_cjk_span(self):
        text = "\u5927\u6587\u672c\u65e5\u8a9e\u306e\u30c6\u30ad\u30b9\u30c8"
        annotated = "\u5927\u6587<t1b>\u672c\u65e5\u8a9e<t1e>\u306e\u30c6\u30ad\u30b9\u30c8"
        target, distractor, chars = self.get_indices(
            text, annotated, "<t1b>\u672c\u65e5\u8a9e<t1e>", None, "1", aoi=False
        )
        assert len(target) == len(text)
        assert len(chars) == len(text)
        # "本日語" is at indices 2,3,4
        assert all(v == i for i, v in enumerate(target[2:5]))
        assert target[0] == 'x'
        assert target[-1] == 'x'

    def test_arabic_span(self):
        text = "\u0627\u0644\u0639\u0631\u0628\u064a\u0629 \u0627\u0644\u0645\u062a\u062c\u0647\u0632\u0629"
        annotated = "\u0627\u0644\u0639\u0631\u0628\u064a\u0629 <t1b>\u0627\u0644\u0645\u062a\u062c\u0647\u0632\u0629<t1e>"
        target, distractor, chars = self.get_indices(
            text, annotated, "<t1b>\u0627\u0644\u0645\u062a\u062c\u0647\u0632\u0629<t1e>", None, "1", aoi=False
        )
        assert len(target) == len(text)
        # "المتجزة" is at indices 8..14
        assert all(v == i for i, v in enumerate(target[8:15]))
        assert target[0] == 'x'

    def test_hebrew_span(self):
        text = "\u05e1\u05e4\u05e8 \u05d8\u05e7\u05e1\u05d8 \u05de\u05d0\u05d5\u05de\u05e8"
        annotated = "\u05e1\u05e4\u05e8 <t1b>\u05d8\u05e7\u05e1\u05d8<t1e> \u05de\u05d0\u05d5\u05de\u05e8"
        target, distractor, chars = self.get_indices(
            text, annotated, "<t1b>\u05d8\u05e7\u05e1\u05d8<t1e>", None, "1", aoi=False
        )
        assert len(target) == len(text)
        # "טקסט" is at indices 4,5,6,7
        assert all(v == i for i, v in enumerate(target[4:8]))
        assert target[0] == 'x'
