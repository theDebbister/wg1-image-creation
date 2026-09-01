"""Integration tests. Need data/ + fonts present.

These tests exercise the config and rendering pipeline using the
TOY dataset.  They are skipped automatically when data/ is missing
(see conftest.py).
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.integration
class TestReadImageConfiguration:
    """read_image_configuration parses the lab-config JSON correctly."""

    def test_reads_toy_config(self, toy_image_config, toy_lab_config_path):
        from utils.config_utils import read_image_configuration
        config = read_image_configuration(toy_lab_config_path)

        assert "RESOLUTION" in config
        assert "SCREEN_SIZE_CM" in config
        assert "SCRIPT_DIRECTION" in config
        assert "MULTIPLE_DEVICES" in config
        assert "DISTANCE_CM" in config

        assert config["RESOLUTION"] == (1920, 1080)
        assert config["SCRIPT_DIRECTION"] == "LTR"
        assert config["MULTIPLE_DEVICES"] is False
        assert config["DISTANCE_CM"] == 60

    def test_missing_key_raises(self, toy_image_config, tmp_path):
        from utils.config_utils import read_image_configuration
        bad_config = {"Monitor_resolution_in_px": "(1920,1080)"}
        p = tmp_path / "bad_config.json"
        p.write_text(json.dumps(bad_config))
        with pytest.raises(ValueError, match="missing"):
            read_image_configuration(p)

    def test_empty_distance_defaults_to_60(self, toy_image_config, tmp_path):
        from utils.config_utils import read_image_configuration
        config = {
            "Monitor_resolution_in_px": "(1920,1080)",
            "Screen_size_in_cm": "(54.5,30.2)",
            "Script_direction": "LTR",
            "Use_of_multiple_devices": "No",
            "Distance_in_cm": "",
        }
        p = tmp_path / "config.json"
        p.write_text(json.dumps(config))
        result = read_image_configuration(p)
        assert result["DISTANCE_CM"] == 60


@pytest.mark.integration
class TestCalculateFontSize:
    """calculate_font_size produces a reasonable size for each language."""

    def test_ltr_language(self, toy_image_config):
        import image_config
        old_lang = image_config.LANGUAGE
        old_font = image_config.FONT_TYPE
        image_config.LANGUAGE = "en"
        image_config.FONT_TYPE = "fonts/JetBrainsMono-Regular.ttf"
        try:
            from utils.config_utils import calculate_font_size
            size = calculate_font_size("en")
            assert isinstance(size, int)
            assert 8 <= size <= 80
        finally:
            image_config.LANGUAGE = old_lang
            image_config.FONT_TYPE = old_font

    @pytest.mark.filterwarnings("ignore:Please be aware that for Cantonese:UserWarning")
    def test_cjk_language(self, toy_image_config):
        """CJK uses '大' as the reference character."""
        import image_config
        old_lang = image_config.LANGUAGE
        old_font = image_config.FONT_TYPE
        image_config.LANGUAGE = "zh"
        image_config.FONT_TYPE = "fonts/NotoSansMonoCJKsc-VF.ttf"
        try:
            from utils.config_utils import calculate_font_size
            size = calculate_font_size("zh")
            assert isinstance(size, int)
            assert 8 <= size <= 80
        finally:
            image_config.LANGUAGE = old_lang
            image_config.FONT_TYPE = old_font

    @pytest.mark.parametrize("lang", ["ar", "fa", "he"])
    def test_rtl_languages(self, toy_image_config, lang):
        import image_config
        old_lang = image_config.LANGUAGE
        old_font = image_config.FONT_TYPE
        # Use a font that exists
        image_config.LANGUAGE = lang
        image_config.FONT_TYPE = "fonts/JetBrainsMono-Regular.ttf"
        try:
            from utils.config_utils import calculate_font_size
            size = calculate_font_size(lang)
            assert isinstance(size, int)
            assert 8 <= size <= 80
        finally:
            image_config.LANGUAGE = old_lang
            image_config.FONT_TYPE = old_font


@pytest.mark.integration
class TestDrawText:
    """Minimal rendering test. Produces an image and checks it is sane."""

    def test_renders_ascii(self, toy_image_config):
        from text_to_picture import draw_text
        import image_config

        img = Image.new(
            "RGB",
            (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
            color=image_config.BACKGROUND_COLOR,
        )
        aois, words = draw_text(
            "Hello world", img, image_config.FONT_SIZE_PX,
            draw_aoi=False, line_limit=image_config.NUM_LINES_PER_PAGE,
            word_split_criterion=image_config.WORD_SPLIT_CRITERION,
        )
        assert len(aois) > 0, "No AOIs generated"
        assert len(words) > 0, "No words generated"
        assert len(aois) == len(words)

    def test_renders_cjk(self, toy_image_config):
        from text_to_picture import draw_text
        import image_config

        img = Image.new(
            "RGB",
            (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
            color=image_config.BACKGROUND_COLOR,
        )
        aois, words = draw_text(
            "\u5927\u6587\u672c\u65e5\u8a9e", img, image_config.FONT_SIZE_PX,
            draw_aoi=False, line_limit=image_config.NUM_LINES_PER_PAGE,
            word_split_criterion=image_config.WORD_SPLIT_CRITERION,
        )
        assert len(aois) == 5, "CJK five chars should produce exactly 5 AOIs"

    @pytest.mark.parametrize("text, script_label", [
        ("\u0627\u0644\u0639\u0631\u0628\u064a\u0629", "arabic"),
        ("\u05e1\u05e4\u05e8 \u05d8\u05e7\u05e1\u05d8", "hebrew"),
        ("\u0395\u03bb\u03bb\u03b7\u03bd\u03b9\u03ba\u03ac", "greek"),
        ("\u041a\u0438\u0440\u0438\u043b\u043b\u0438\u0446\u0430", "cyrillic"),
        ("\u0e44\u0e17\u0e22\u0e40\u0e2a\u0e14\u0e07", "thai"),
        ("\u0939\u093f\u0928\u094d\u0926\u0940", "hindi"),
    ])
    def test_renders_various_scripts(self, toy_image_config, text, script_label):
        from text_to_picture import draw_text
        import image_config

        img = Image.new(
            "RGB",
            (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
            color=image_config.BACKGROUND_COLOR,
        )
        aois, words = draw_text(
            text, img, image_config.FONT_SIZE_PX,
            draw_aoi=False, line_limit=image_config.NUM_LINES_PER_PAGE,
            word_split_criterion=image_config.WORD_SPLIT_CRITERION,
        )
        assert len(aois) > 0, f"No AOIs generated for {script_label}"
        assert len(words) > 0, f"No words generated for {script_label}"
        assert len(aois) == len(words), f"AOI/word count mismatch for {script_label}"

    def test_aoi_boxes_have_valid_geometry(self, toy_image_config):
        from text_to_picture import draw_text
        import image_config

        img = Image.new(
            "RGB",
            (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
            color=image_config.BACKGROUND_COLOR,
        )
        aois, _ = draw_text(
            "Test text", img, image_config.FONT_SIZE_PX,
            draw_aoi=True, line_limit=image_config.NUM_LINES_PER_PAGE,
            word_split_criterion=image_config.WORD_SPLIT_CRITERION,
        )
        for aoi in aois:
            # aoi = [idx, char, x, y, width, height, char_in_line, line, page, word_idx, word_in_line]
            char_idx, char, x, y, w, h = aoi[0], aoi[1], aoi[2], aoi[3], aoi[4], aoi[5]
            assert isinstance(x, (int, float)), f"AOI x is not numeric: {x}"
            assert isinstance(y, (int, float)), f"AOI y is not numeric: {y}"
            assert w > 0, f"AOI width <= 0 for char '{char}'"
            assert h > 0, f"AOI height <= 0 for char '{char}'"
            assert 0 <= x < image_config.IMAGE_WIDTH_PX, f"AOI x out of bounds: {x}"
            assert 0 <= y < image_config.IMAGE_HEIGHT_PX, f"AOI y out of bounds: {y}"

    def test_fixation_dot_drawn(self, toy_image_config):
        """draw_text should draw a fixation dot at the bottom of the page."""
        from text_to_picture import draw_text
        import image_config

        img = Image.new(
            "RGB",
            (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
            color=image_config.BACKGROUND_COLOR,
        )
        draw_text(
            "Fixation test", img, image_config.FONT_SIZE_PX,
            draw_aoi=False, line_limit=image_config.NUM_LINES_PER_PAGE,
            word_split_criterion=image_config.WORD_SPLIT_CRITERION,
        )
        # The fixation dot is drawn at POS_BOTTOM_DOT_{X,Y}_PX with a black outline.
        # We verify that at least one pixel near the dot position is not the background color.
        dot_x = int(image_config.POS_BOTTOM_DOT_X_PX)
        dot_y = int(image_config.POS_BOTTOM_DOT_Y_PX)
        r = image_config.FIX_DOT_RADIUS_PX
        # Sample a small region around the dot
        pixel = img.getpixel((dot_x, dot_y))
        # The dot is an outline (not filled), so the center pixel may still be background.
        # Check a pixel on the ring instead.
        ring_pixel = img.getpixel((dot_x + r, dot_y))
        bg = image_config.BACKGROUND_COLOR
        # At least the ring pixel should differ from background (it's the black outline)
        assert ring_pixel != bg, f"Fixation dot ring pixel is background color at ({dot_x + r}, {dot_y})"
