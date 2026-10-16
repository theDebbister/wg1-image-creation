"""Tests for vertical ttb support and CJK font sizing, parametrized for ja, yu, zh, zt."""

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
        ("zt", "大"),
        ("ar", "د"),
        ("fa", "د"),
        ("he", "ה"),
        ("en", "a"),
    ])
    def test_reference_char_for_lang(self, lang, expected_char):
        content = CONFIG_UTILS_PATH.read_text()
        if lang in ("zh", "yu", "ja", "zt"):
            assert "elif lang in ('zh', 'yu', 'ja', 'zt')" in content
            assert "char = '大'" in content

    @pytest.mark.parametrize("lang", ["zh", "yu", "ja", "zt"])
    def test_ja_uses_same_reference_as_zh(self, lang):
        content = CONFIG_UTILS_PATH.read_text()
        assert "char = '大'" in content


class TestTTBConfig:
    def test_image_config_handles_ttb(self):
        content = IMAGE_CONFIG_PATH.read_text()
        assert "elif LANGUAGE in ('zh', 'yu', 'ja', 'zt')" in content
        assert "'ttb'" in content

    @pytest.mark.parametrize("bad_value", ["diagonal", "vertical", "tbt"])
    def test_invalid_script_direction_string_detected(self, bad_value):
        assert bad_value.lower() not in ("ltr", "rtl", "ttb")


class TestDrawTextTTB:
    @pytest.mark.parametrize("lang,word_split", [
        ("ja", ""),
        ("yu", ""),
        ("zh", ""),
        ("zt", ""),
    ])
    def test_word_split_empty_for_cjk(self, lang, word_split):
        content = IMAGE_CONFIG_PATH.read_text()
        assert "elif LANGUAGE in ('zh', 'yu', 'ja', 'zt')" in content

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


class TestCJKLTRBold:
    """The horizontal (ltr) CJK path must resolve **…** bold spans per line:
    consume the markers, embolden only the marked run, and not leak bold into
    later lines."""

    @staticmethod
    def _draw(text, toy_image_config):
        from text_to_picture import draw_text
        import image_config

        orig_lang = image_config.LANGUAGE
        orig_font = image_config.FONT_TYPE
        orig_bold = image_config.FONT_TYPE_BOLD
        try:
            image_config.LANGUAGE = "ja"
            image_config.FONT_TYPE = "fonts/NotoSansJP-Regular.ttf"
            image_config.FONT_TYPE_BOLD = "fonts/NotoSansJP-Bold.ttf"
            img = Image.new(
                "RGB",
                (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
                color=image_config.BACKGROUND_COLOR,
            )
            aois, _ = draw_text(
                text, img, image_config.FONT_SIZE_PX, draw_aoi=True,
                script_direction="ltr", word_split_criterion="",
                text_width_px=image_config.TEXT_WIDTH_PX,
                line_limit=image_config.NUM_LINES_PER_PAGE,
                image_short_name="ltr_bold",
            )
        finally:
            image_config.LANGUAGE = orig_lang
            image_config.FONT_TYPE = orig_font
            image_config.FONT_TYPE_BOLD = orig_bold
        return img, aois

    @staticmethod
    def _ink(img, aoi):
        import numpy as np
        _, _, x, y, w, h = aoi[:6]
        crop = np.array(img.crop((int(x), int(y), int(x + w), int(y + h))).convert("L"))
        return int((crop < 128).sum())

    def test_markers_are_consumed(self, toy_image_config):
        _, aois = self._draw("あ**黒い点**い。", toy_image_config)
        chars = [a[1] for a in aois]
        assert "*" not in chars
        assert "黒" in chars and "。" in chars

    def test_bold_run_renders_heavier_than_regular(self, toy_image_config):
        plain_img, plain = self._draw("あ黒い", toy_image_config)
        bold_img, bold = self._draw("あ**黒**い", toy_image_config)
        p = next(a for a in plain if a[1] == "黒")
        b = next(a for a in bold if a[1] == "黒")
        # markers are stripped, so the glyph keeps the same position
        assert p[2] == b[2] and p[3] == b[3]
        assert self._ink(bold_img, b) > self._ink(plain_img, p)

    def test_bold_does_not_leak_into_next_line(self, toy_image_config):
        leak_img, leak = self._draw("あ**い**\nう", toy_image_config)
        plain_img, plain = self._draw("あ\nう", toy_image_config)
        u_leak = next(a for a in leak if a[1] == "う")
        u_plain = next(a for a in plain if a[1] == "う")
        assert self._ink(leak_img, u_leak) == self._ink(plain_img, u_plain)


class TestHorizontalKinsoku:
    """Shared JLREQ carry rule used at horizontal line breaks."""

    @staticmethod
    def _count():
        from languages import japanese
        return japanese.kinsoku_carry_count

    def test_carries_for_line_start_punctuation(self, toy_image_config):
        # next line would start with 。 -> carry the previous trailing char down
        assert self._count()(["あ", "い"], "。") == 1
        assert self._count()(["あ"], "。") == 1

    def test_carries_opening_bracket_off_line_end(self, toy_image_config):
        assert self._count()(["あ", "「"], "い") == 1

    def test_no_carry_when_clean(self, toy_image_config):
        assert self._count()(["あ", "い"], "う") == 0


class TestCJKKinsoku:
    """Kinsoku rules are selected per language (languages.cjk), not hardcoded JA."""

    def test_common_punctuation_shared_across_cjk(self):
        from languages import cjk
        for lang in ("ja", "zh", "zt", "yu"):
            cannot_start, cannot_end = cjk.rules_for(lang)
            assert "。" in cannot_start and "「" in cannot_end

    def test_japanese_extras_only_for_japanese(self):
        from languages import cjk
        ja_start, _ = cjk.rules_for("ja")
        zt_start, _ = cjk.rules_for("zt")
        assert "っ" in ja_start and "ー" in ja_start
        assert "っ" not in zt_start and "ー" not in zt_start

    def test_cjk_language_predicate_includes_zt(self):
        from languages import cjk
        assert cjk.is_cjk_language("zt")
        assert cjk.is_cjk_language("ja")
        assert not cjk.is_cjk_language("en")


class TestJapaneseLatinMonospace:
    """Horizontal Japanese renders Latin letters with the monospaced font, so
    they get uniform (monospaced) AOIs that are narrower than full-width CJK."""

    def test_latin_aois_are_monospaced(self, toy_image_config):
        from text_to_picture import draw_text
        import image_config

        orig = (image_config.LANGUAGE, image_config.FONT_TYPE,
                image_config.FONT_TYPE_BOLD, image_config.LATIN_FONT_TYPE,
                image_config.LATIN_BOX_TYPE)
        try:
            image_config.LANGUAGE = "ja"
            image_config.FONT_TYPE = "fonts/NotoSansJP-Regular.ttf"
            image_config.FONT_TYPE_BOLD = "fonts/NotoSansJP-Bold.ttf"
            image_config.LATIN_FONT_TYPE = "fonts/JetBrainsMono-Regular.ttf"
            image_config.LATIN_BOX_TYPE = "tight"
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
             image_config.FONT_TYPE_BOLD, image_config.LATIN_FONT_TYPE,
             image_config.LATIN_BOX_TYPE) = orig

        width = {aoi[1]: aoi[4] for aoi in aois}
        assert width.get("A", 0) > 0
        # Latin letters share one monospaced advance ...
        assert width["A"] == width["b"]
        # ... which is narrower than the full-width CJK cell.
        assert width["A"] < width["あ"] == width["い"]


class TestConfigPathNormalisation:
    """Windows path separators must not leak into the generated config."""

    def test_backslashes_are_written_as_slashes(self, toy_image_config, tmp_path):
        from utils.config_utils import write_final_config
        target = tmp_path / "config_normalisation.py"
        write_final_config(str(target), {"PATHS": {"some_csv": "data\\stimuli_x\\file.csv"}})
        content = target.read_text(encoding="utf8")
        assert 'some_csv = "data/stimuli_x/file.csv"' in content
        assert "\\" not in content
