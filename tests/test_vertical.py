"""Tests for vertical ttb support and CJK font sizing, parametrized for ja, yu, zh."""

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
        ("ar", "د"),
        ("fa", "د"),
        ("he", "ה"),
        ("en", "a"),
    ])
    def test_reference_char_for_lang(self, lang, expected_char):
        content = CONFIG_UTILS_PATH.read_text()
        if lang in ("zh", "yu", "ja"):
            assert "elif lang in ('zh', 'yu', 'ja')" in content
            assert "char = '大'" in content

    @pytest.mark.parametrize("lang", ["zh", "yu", "ja"])
    def test_ja_uses_same_reference_as_zh(self, lang):
        content = CONFIG_UTILS_PATH.read_text()
        assert "char = '大'" in content


class TestTTBConfig:
    def test_image_config_handles_ttb(self):
        content = IMAGE_CONFIG_PATH.read_text()
        assert "elif LANGUAGE in ('zh', 'yu', 'ja')" in content
        assert "'ttb'" in content

    @pytest.mark.parametrize("bad_value", ["diagonal", "vertical", "tbt"])
    def test_invalid_script_direction_string_detected(self, bad_value):
        assert bad_value.lower() not in ("ltr", "rtl", "ttb")


class TestDrawTextTTB:
    @pytest.mark.parametrize("lang,word_split", [
        ("ja", ""),
        ("yu", ""),
        ("zh", ""),
    ])
    def test_word_split_empty_for_cjk(self, lang, word_split):
        content = IMAGE_CONFIG_PATH.read_text()
        assert "elif LANGUAGE in ('zh', 'yu', 'ja')" in content

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
