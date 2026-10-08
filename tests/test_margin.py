"""Margin and overflow tests, parametrized for ltr, rtl, ttb.

Paints margins when DEBUG_MARGIN is True for visual review.
"""
from pathlib import Path

import pytest
from PIL import Image


@pytest.mark.parametrize("script_dir", ["ltr", "rtl", "ttb"])
def test_aois_inside_margins(toy_image_config, script_dir):
    from text_to_picture import draw_text
    import image_config
    img = Image.new("RGB", (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX), image_config.BACKGROUND_COLOR)
    sample = {"ltr": "Hello world test", "rtl": "مرحبا بالعالم", "ttb": "テスト日本語"}[script_dir]
    word_split = "" if script_dir == "ttb" else " "
    aois, _ = draw_text(sample, img, image_config.FONT_SIZE_PX, draw_aoi=False, script_direction=script_dir, word_split_criterion=word_split, line_limit=image_config.NUM_LINES_PER_PAGE, image_short_name="margin_check")
    for aoi in aois:
        _, ch, x, y, w, h, *_ = aoi
        assert 0 <= y < image_config.IMAGE_HEIGHT_PX
        assert y + h <= image_config.IMAGE_HEIGHT_PX
        assert x < image_config.IMAGE_WIDTH_PX
        assert x + w > -100
        if script_dir == "ttb":
            assert x >= image_config.MIN_MARGIN_LEFT_PX - 5
            assert x + w <= image_config.IMAGE_WIDTH_PX - image_config.MIN_MARGIN_RIGHT_PX + 5


@pytest.mark.parametrize("script_dir,long_text", [
    ("ltr", "word " * 200),
    ("ttb", "あ" * 500),
])
def test_overflow_warning(toy_image_config, script_dir, long_text):
    from text_to_picture import draw_text
    import image_config
    img = Image.new("RGB", (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX), image_config.BACKGROUND_COLOR)
    word_split = "" if script_dir == "ttb" else " "
    with pytest.warns(UserWarning, match="exceeds|extends past"):
        draw_text(long_text, img, image_config.FONT_SIZE_PX, draw_aoi=False, script_direction=script_dir, word_split_criterion=word_split, line_limit=5, image_short_name="overflow_test")


@pytest.mark.visual
@pytest.mark.parametrize("with_margin", [False, True])
def test_margin_painting_visual(toy_image_config, request, with_margin):
    from text_to_picture import draw_text
    import image_config
    from test_visual import _load_baseline, _save_baseline, _image_diff_pixels, _save_diff_report
    image_config.DEBUG_MARGIN = with_margin
    try:
        img = Image.new("RGB", (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX), image_config.BACKGROUND_COLOR)
        draw_text("Hello world", img, image_config.FONT_SIZE_PX, draw_aoi=False, script_direction="ltr", image_short_name="margin_vis")
        name = f"margin_{'on' if with_margin else 'off'}"
        if request.config.getoption("--update-baselines", default=False):
            _save_baseline(name, img)
            pytest.skip("Baseline updated")
        else:
            baseline = _load_baseline(name)
            if baseline is None:
                _save_baseline(name, img)
                pytest.skip("Baseline created")
            diff = _image_diff_pixels(baseline, img)
            if diff > 0:
                _save_diff_report(name, baseline, img, diff)
                assert False, f"Margin visual diff {diff}"
    finally:
        image_config.DEBUG_MARGIN = False


@pytest.mark.visual
def test_ttb_margin_grid_visual(toy_image_config, request):
    from text_to_picture import draw_text
    import image_config
    from test_visual import _load_baseline, _save_baseline, _image_diff_pixels, _save_diff_report
    image_config.DEBUG_MARGIN = True
    image_config.DEBUG_GRID = True
    try:
        img = Image.new("RGB", (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX), image_config.BACKGROUND_COLOR)
        draw_text("テスト、。「」ー〜っゃ大３A", img, image_config.FONT_SIZE_PX, draw_aoi=False, script_direction="ttb", word_split_criterion="", line_limit=image_config.NUM_LINES_PER_PAGE, image_short_name="ttb_both")
        name = "ttb_margin_grid"
        if request.config.getoption("--update-baselines", default=False):
            _save_baseline(name, img)
            pytest.skip("Baseline updated")
        else:
            baseline = _load_baseline(name)
            if baseline is None:
                _save_baseline(name, img)
                pytest.skip("Baseline created")
            diff = _image_diff_pixels(baseline, img)
            if diff > 0:
                _save_diff_report(name, baseline, img, diff)
                assert False, f"Diff {diff}"
    finally:
        image_config.DEBUG_MARGIN = False
        image_config.DEBUG_GRID = False
