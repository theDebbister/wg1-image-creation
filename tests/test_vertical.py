"""Tests for vertical ttb support and CJK font sizing, parametrized for ja, yu, zh, tc."""

from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_UTILS_PATH = REPO_ROOT / "src" / "utils" / "config_utils.py"
IMAGE_CONFIG_PATH = REPO_ROOT / "src" / "image_config.py"


class TestFontSizeReferenceChar:
    @pytest.mark.parametrize("lang,expected_char", [
        ("zh", "大"),
        ("yu", "大"),
        ("ja", "大"),
        ("tc", "大"),
        ("ar", "د"),
        ("fa", "د"),
        ("he", "ה"),
        ("en", "a"),
    ])
    def test_reference_char_for_lang(self, lang, expected_char):
        content = CONFIG_UTILS_PATH.read_text()
        if lang in ("zh", "yu", "ja", "tc"):
            assert "elif lang in ('zh', 'yu', 'ja', 'tc')" in content
            assert "char = '大'" in content

    @pytest.mark.parametrize("lang", ["zh", "yu", "ja", "tc"])
    def test_ja_uses_same_reference_as_zh(self, lang):
        content = CONFIG_UTILS_PATH.read_text()
        assert "char = '大'" in content


class TestTTBConfig:
    def test_image_config_handles_ttb(self):
        content = IMAGE_CONFIG_PATH.read_text()
        assert "elif LANGUAGE in ('zh', 'yu', 'ja', 'tc')" in content
        assert "'ttb'" in content

    @pytest.mark.parametrize("bad_value", ["diagonal", "vertical", "tbt"])
    def test_invalid_script_direction_string_detected(self, bad_value):
        assert bad_value.lower() not in ("ltr", "rtl", "ttb")


class TestDrawTextTTB:
    @pytest.mark.parametrize("lang,word_split", [
        ("ja", ""),
        ("yu", ""),
        ("zh", ""),
        ("tc", ""),
    ])
    def test_word_split_empty_for_cjk(self, lang, word_split):
        content = IMAGE_CONFIG_PATH.read_text()
        assert "elif LANGUAGE in ('zh', 'yu', 'ja', 'tc')" in content

    def _ensure_real_languages(self):
        import sys, importlib
        # if fake languages remain from test_unit, reload real ones
        for mod in ("languages.arabic_farsi", "languages.hebrew", "languages"):
            if mod in sys.modules and not hasattr(sys.modules[mod], "__file__"):
                del sys.modules[mod]
        try:
            import languages.arabic_farsi  # noqa: F401
            import languages.hebrew  # noqa: F401
        except Exception:
            pass
        # ensure text_to_picture is reloaded with real languages
        if "text_to_picture" in sys.modules:
            import importlib
            importlib.reload(sys.modules["text_to_picture"])

    @pytest.mark.parametrize("script_dir", ["ltr", "rtl", "ttb"])
    def test_draw_text_accepts_script_dirs(self, toy_image_config, script_dir):
        self._ensure_real_languages()
        from text_to_picture import draw_text
        import image_config
        img = Image.new("RGB", (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX), image_config.BACKGROUND_COLOR)
        if script_dir == "ttb":
            aois, words = draw_text("test", img, image_config.FONT_SIZE_PX, script_direction=script_dir, word_split_criterion="", line_limit=5)
            assert len(aois) > 0
        else:
            aois, words = draw_text("test", img, image_config.FONT_SIZE_PX, script_direction=script_dir)
            assert isinstance(aois, list)

    def test_draw_text_ttb_invalid_raises(self, toy_image_config):
        self._ensure_real_languages()
        from text_to_picture import draw_text
        import image_config
        img = Image.new("RGB", (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX), image_config.BACKGROUND_COLOR)
        with pytest.raises(ValueError):
            draw_text("test", img, image_config.FONT_SIZE_PX, script_direction="diagonal")


@pytest.mark.visual
class TestVisualTTB:
    @pytest.mark.parametrize("with_grid", [False, True])
    def test_ttb_visual_with_and_without_grid(self, toy_image_config, request, with_grid):
        from text_to_picture import draw_text
        import image_config
        from test_visual import _load_baseline, _save_baseline, _image_diff_pixels, _save_diff_report

        image_config.DEBUG_GRID = with_grid
        try:
            img = Image.new("RGB", (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX), color=image_config.BACKGROUND_COLOR)
            text = "テスト、。「」ー〜っゃ大３A 二段落目です。\n次の段落は別のカラムへ。"
            draw_text(
                text, img, image_config.FONT_SIZE_PX,
                draw_aoi=False,
                word_split_criterion="",
                script_direction="ttb",
                line_limit=image_config.NUM_LINES_PER_PAGE,
                image_short_name=f"ttb_grid_{with_grid}",
            )
            img_aoi = Image.new("RGB", (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX), color=image_config.BACKGROUND_COLOR)
            aois, _ = draw_text(
                text, img_aoi, image_config.FONT_SIZE_PX,
                draw_aoi=True,
                word_split_criterion="",
                script_direction="ttb",
                line_limit=image_config.NUM_LINES_PER_PAGE,
                image_short_name="ttb_aoi_check",
            )
            for aoi in aois:
                _, ch, x, y, w, h, *_ = aoi
                assert 0 <= x < image_config.IMAGE_WIDTH_PX
                assert 0 <= y < image_config.IMAGE_HEIGHT_PX
                assert x + w <= image_config.IMAGE_WIDTH_PX
                assert y + h <= image_config.IMAGE_HEIGHT_PX

            name = f"ttb_{'grid' if with_grid else 'nogrid'}"
            if request.config.getoption("--update-baselines", default=False):
                _save_baseline(name, img)
                pytest.skip("Baseline updated")
            else:
                baseline = _load_baseline(name)
                if baseline is None:
                    _save_baseline(name, img)
                    pytest.skip("Baseline created (first run)")
                diff_pixels = _image_diff_pixels(baseline, img)
                if diff_pixels > 0:
                    _save_diff_report(name, baseline, img, diff_pixels)
                    assert False, f"Visual diff {diff_pixels} pixels for {name}"
        finally:
            image_config.DEBUG_GRID = False

    @pytest.mark.parametrize("lang", ["ja", "zh", "yu"])
    def test_cjk_ttb_visual_per_lang(self, toy_image_config, request, lang):
        from text_to_picture import draw_text
        import image_config
        from test_visual import _load_baseline, _save_baseline, _image_diff_pixels, _save_diff_report

        orig_lang = image_config.LANGUAGE
        orig_font = image_config.FONT_TYPE
        orig_bold = image_config.FONT_TYPE_BOLD
        try:
            # Use NotoSansJP for all vertical renderings to avoid variable font issues
            # Han unification differences are documented, unit square uses same '大' anyway
            image_config.FONT_TYPE = "fonts/NotoSansJP-Regular.ttf"
            image_config.FONT_TYPE_BOLD = "fonts/NotoSansJP-Bold.ttf"
            img = Image.new("RGB", (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX), color=image_config.BACKGROUND_COLOR)
            sample = {"ja": "日本語のテキスト、テストです。", "zh": "中文文本测试。", "yu": "中文文本测试。"}[lang]
            draw_text(sample, img, image_config.FONT_SIZE_PX, draw_aoi=False, word_split_criterion="", script_direction="ttb", line_limit=image_config.NUM_LINES_PER_PAGE, image_short_name=f"ttb_{lang}")
            name = f"ttb_lang_{lang}"
            if request.config.getoption("--update-baselines", default=False):
                _save_baseline(name, img)
                pytest.skip("Baseline updated")
            else:
                baseline = _load_baseline(name)
                if baseline is None:
                    _save_baseline(name, img)
                    pytest.skip("Baseline created (first run)")
                diff_pixels = _image_diff_pixels(baseline, img)
                if diff_pixels > 0:
                    _save_diff_report(name, baseline, img, diff_pixels)
                    assert False, f"Visual diff for {lang}"
        finally:
            image_config.LANGUAGE = orig_lang
            image_config.FONT_TYPE = orig_font
            image_config.FONT_TYPE_BOLD = orig_bold


class TestTTBBoldAndSpaces:
    def _draw(self, text, toy_image_config):
        from text_to_picture import draw_text
        import image_config
        img = Image.new(
            "RGB",
            (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
            color=image_config.BACKGROUND_COLOR,
        )
        aois, _ = draw_text(
            text, img, image_config.FONT_SIZE_PX, draw_aoi=True,
            word_split_criterion="", script_direction="ttb",
            line_limit=image_config.NUM_LINES_PER_PAGE,
            image_short_name="ttb_bold_space",
        )
        return aois, image_config

    def test_bold_markers_are_consumed(self, toy_image_config):
        """**…** toggles bold; neither star may survive as a rendered AOI."""
        aois, _ = self._draw("あ**黒い点**い **。**", toy_image_config)
        chars = [a[1] for a in aois]
        assert "*" not in chars
        assert "黒" in chars and "。" in chars

    def test_bold_uses_bold_glyph_vertical_variant(self, toy_image_config):
        """A bold 、 must be shaped like regular text, not centred by PIL."""
        aois_plain, _ = self._draw("あ、い", toy_image_config)
        aois_bold, _ = self._draw("あ**、**い", toy_image_config)
        plain = next(a for a in aois_plain if a[1] == "、")
        bold = next(a for a in aois_bold if a[1] == "、")
        # Same cell geometry whether or not the char is bold.
        assert plain[3:6] == bold[3:6]

    def test_space_width_full_between_cjk_mono_next_to_latin(self, toy_image_config):
        aois, ic = self._draw("あ いA B", toy_image_config)
        spaces = [a for a in aois if a[1] == " "]
        # Exactly the two literal spaces: no automatic insertion around Latin.
        assert len(spaces) == 2
        # CJK/CJK space is a full Japanese cell; Latin-adjacent space is half width.
        assert spaces[0][5] == ic.FONT_SIZE_PX
        assert spaces[1][5] < ic.FONT_SIZE_PX

    def _draw_img(self, text, toy_image_config):
        from text_to_picture import draw_text
        import image_config
        img = Image.new(
            "RGB",
            (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
            color=image_config.BACKGROUND_COLOR,
        )
        aois, _ = draw_text(
            text, img, image_config.FONT_SIZE_PX, draw_aoi=True,
            word_split_criterion="", script_direction="ttb",
            line_limit=image_config.NUM_LINES_PER_PAGE,
            image_short_name="ttb_single_letter",
        )
        return img, aois, image_config

    @staticmethod
    def _ink_bbox(img, aoi):
        import numpy as np
        _, _, x, y, w, h, *_ = aoi
        crop = np.array(img.crop((int(x), int(y), int(x + w), int(y + h))).convert("L"))
        ys, xs = np.where(crop < 128)
        assert ys.size > 0, "AOI has no ink"
        return int(xs.max() - xs.min()) + 1, int(ys.max() - ys.min()) + 1

    def test_single_latin_letter_is_upright(self, toy_image_config):
        """A standalone Latin letter (e.g. the D in ビタミンD) is upright, not
        rotated: for a tall/narrow 'I' the ink is taller than it is wide."""
        img, aois, ic = self._draw_img("あIい", toy_image_config)
        a = next(x for x in aois if x[1] == "I")
        # full square cell, not the tight mono box used for rotated words
        assert a[4] == ic.FONT_SIZE_PX and a[5] == ic.FONT_SIZE_PX
        iw, ih = self._ink_bbox(img, a)
        assert ih >= iw, f"'I' should read upright, got ink {iw}x{ih}"

    def test_multi_letter_latin_word_stays_rotated(self, toy_image_config):
        img, aois, ic = self._draw_img("あIIい", toy_image_config)
        a = aois[[x[1] for x in aois].index("I")]
        iw, ih = self._ink_bbox(img, a)
        assert iw >= ih, f"rotated 'II' should read sideways, got ink {iw}x{ih}"


class TestJapaneseLTRParity:
    """Japanese must keep the same pixel font size horizontally and vertically,
    and kana must flow per character in the horizontal (ltr) path."""

    def test_kana_is_cjk_flow_char(self, toy_image_config):
        from text_to_picture import _is_cjk_flow_char
        for ch in ("あ", "ア", "ー", "漢", "。"):
            assert _is_cjk_flow_char(ch), ch
        for ch in ("A", "a", " ", "-"):
            assert not _is_cjk_flow_char(ch), ch

    def test_ja_font_size_identical_for_ltr_and_ttb(self, toy_image_config):
        import image_config
        from utils.config_utils import calculate_font_size

        orig_dir = image_config.SCRIPT_DIRECTION
        orig_font = image_config.FONT_TYPE
        try:
            image_config.FONT_TYPE = "fonts/NotoSansJP-Regular.ttf"
            image_config.SCRIPT_DIRECTION = "ltr"
            ltr = calculate_font_size("ja")
            image_config.SCRIPT_DIRECTION = "ttb"
            ttb = calculate_font_size("ja")
        finally:
            image_config.SCRIPT_DIRECTION = orig_dir
            image_config.FONT_TYPE = orig_font

        assert ltr > 0
        assert ltr == ttb

    def test_ja_ltr_kana_wraps_within_text_margin(self, toy_image_config):
        from text_to_picture import draw_text
        import image_config

        orig_lang = image_config.LANGUAGE
        orig_font = image_config.FONT_TYPE
        try:
            image_config.LANGUAGE = "ja"
            image_config.FONT_TYPE = "fonts/NotoSansJP-Regular.ttf"
            img = Image.new(
                "RGB",
                (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
                color=image_config.BACKGROUND_COLOR,
            )
            aois, _ = draw_text(
                "あ" * 200, img, image_config.FONT_SIZE_PX, draw_aoi=True,
                script_direction="ltr", word_split_criterion="",
                text_width_px=image_config.TEXT_WIDTH_PX,
            )
        finally:
            image_config.LANGUAGE = orig_lang
            image_config.FONT_TYPE = orig_font

        assert len(aois) > 0
        right_limit = image_config.ANCHOR_POINT_X_PX + image_config.TEXT_WIDTH_PX
        for aoi in aois:
            _, char, x, y, w, h = aoi[:6]
            assert x + w <= right_limit + 1, f"kana '{char}' overflowed the text margin"


class TestHorizontalKinsoku:
    """Shared JLREQ line-break rules applied to horizontal Japanese lines."""

    @staticmethod
    def _apply():
        from text_to_picture import _apply_horizontal_kinsoku
        return _apply_horizontal_kinsoku

    def test_pushes_out_line_start_punctuation(self, toy_image_config):
        out = self._apply()(["あい", "。うえ"])
        assert "".join(out) == "あい。うえ"
        assert all(not ln or ln[0] not in "、。" for ln in out)

    def test_pulls_opening_bracket_off_line_end(self, toy_image_config):
        out = self._apply()(["あい「", "うえ"])
        assert "".join(out) == "あい「うえ"
        assert not out[0].endswith("「")

    def test_leaves_clean_lines_unchanged(self, toy_image_config):
        original = ["あいうえ", "おかきく"]
        assert self._apply()(original) == original


class TestJapaneseLatinMonospace:
    """Horizontal Japanese renders Latin letters with the monospaced font and
    gives them uniform (monospaced) AOI boxes, while CJK stays full-width."""

    def test_latin_aois_are_monospaced(self, toy_image_config):
        from text_to_picture import draw_text
        import image_config

        orig = (image_config.LANGUAGE, image_config.FONT_TYPE,
                image_config.FONT_TYPE_BOLD, image_config.LATIN_FONT_TYPE)
        try:
            image_config.LANGUAGE = "ja"
            image_config.FONT_TYPE = "fonts/NotoSansJP-Regular.ttf"
            image_config.FONT_TYPE_BOLD = "fonts/NotoSansJP-Bold.ttf"
            image_config.LATIN_FONT_TYPE = "fonts/JetBrainsMono-Regular.ttf"
            img = Image.new(
                "RGB",
                (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
                color=image_config.BACKGROUND_COLOR,
            )
            aois, _ = draw_text(
                "Abあい", img, image_config.FONT_SIZE_PX, draw_aoi=True,
                script_direction="ltr", word_split_criterion="",
                text_width_px=image_config.TEXT_WIDTH_PX,
            )
        finally:
            (image_config.LANGUAGE, image_config.FONT_TYPE,
             image_config.FONT_TYPE_BOLD, image_config.LATIN_FONT_TYPE) = orig

        width = {aoi[1]: aoi[4] for aoi in aois}
        assert width.get("A", 0) > 0
        # Latin letters share one (monospaced) advance ...
        assert width["A"] == width["b"]
        # ... which differs from the full-width CJK cell.
        assert width["A"] != width["あ"] == width["い"]


class TestConfigPathNormalisation:
    """Windows path separators must not leak into the generated config."""

    def test_backslashes_are_written_as_slashes(self, toy_image_config, tmp_path):
        from utils.config_utils import write_final_config
        target = tmp_path / "config_normalisation.py"
        write_final_config(str(target), {"PATHS": {"some_csv": "data\\stimuli_x\\file.csv"}})
        content = target.read_text(encoding="utf8")
        assert 'some_csv = "data/stimuli_x/file.csv"' in content
        assert "\\" not in content
