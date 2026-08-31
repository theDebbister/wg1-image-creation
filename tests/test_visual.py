"""Visual regression tests. Slow, needs full env, produces diff images.

Baselines are generated on-the-fly from the base branch (no committed binaries).
In CI: base branch output is generated in a worktree, PR output is generated
here, and diffs are saved as workflow artifacts.
Locally: run pytest with --update-baselines to create/update baselines, then
run without the flag to compare.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageStat

REPO_ROOT = Path(__file__).resolve().parent.parent
VISUAL_BASELINE_DIR = REPO_ROOT / "data" / "_visual_baselines"
VISUAL_DIFF_DIR = REPO_ROOT / "data" / "_visual_diffs"


def _ensure_dirs():
    VISUAL_BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    VISUAL_DIFF_DIR.mkdir(parents=True, exist_ok=True)


def _save_baseline(name: str, img: Image.Image):
    """Save a baseline image."""
    _ensure_dirs()
    img.save(VISUAL_BASELINE_DIR / f"{name}.png")


def _load_baseline(name: str) -> Image.Image | None:
    """Load a baseline image, or None if not found."""
    path = VISUAL_BASELINE_DIR / f"{name}.png"
    if path.is_file():
        return Image.open(path).convert("RGB")
    return None


def _image_diff_pixels(img1: Image.Image, img2: Image.Image) -> int:
    """Count the number of differing pixels between two images."""
    if img1.size != img2.size:
        return max(img1.size[0] * img1.size[1], img2.size[0] * img2.size[1])
    diff = ImageChops.difference(img1, img2)
    stat = ImageStat.Stat(diff)
    # A pixel is "different" if any channel differs by more than a threshold
    threshold = 5
    pixels = 0
    for i in range(3):
        channel_data = list(stat.mean)
    # Simple approach: count non-zero diff pixels
    diff_data = diff.load()
    w, h = diff.size
    for y in range(h):
        for x in range(w):
            r, g, b = diff_data[x, y]
            if r > threshold or g > threshold or b > threshold:
                pixels += 1
    return pixels


def _create_diff_image(
    img1: Image.Image, img2: Image.Image, name: str
) -> Image.Image:
    """Create a visual diff image highlighting changed pixels in red."""
    if img1.size != img2.size:
        # Resize img2 to match img1 for comparison
        img2 = img2.resize(img1.size, Image.NEAREST)
    diff = ImageChops.difference(img1, img2)
    # Amplify the diff and color it red
    threshold = 5
    diff_data = diff.load()
    w, h = diff.size
    result = img1.copy()
    result_data = result.load()
    for y in range(h):
        for x in range(w):
            r, g, b = diff_data[x, y]
            if r > threshold or g > threshold or b > threshold:
                result_data[x, y] = (255, 0, 0)
    return result


def _save_diff_report(name: str, img1: Image.Image, img2: Image.Image, diff_pixels: int):
    """Save the diff image and a side-by-side comparison."""
    _ensure_dirs()
    diff_img = _create_diff_image(img1, img2, name)
    diff_img.save(VISUAL_DIFF_DIR / f"{name}_diff.png")
    # Also save a side-by-side: baseline | current | diff
    w1, h1 = img1.size
    w2, h2 = img2.size
    max_h = max(h1, h2)
    side_by_side = Image.new("RGB", (w1 + w2 + w1, max_h), (200, 200, 200))
    side_by_side.paste(img1, (0, 0))
    side_by_side.paste(img2, (w1, 0))
    side_by_side.paste(diff_img, (w1 + w2, 0))
    side_by_side.save(VISUAL_DIFF_DIR / f"{name}_side_by_side.png")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.visual
class TestVisualRegression:
    """Compare rendered images against baselines.

    If --update-baselines is passed, save current output as new baselines.
    Otherwise, compare against existing baselines and fail on diff.
    """

    def test_stimulus_page_ascii(self, toy_image_config, request):
        """Render a simple ASCII stimulus page and compare."""
        from text_to_picture import draw_text
        import image_config

        img = Image.new(
            "RGB",
            (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
            color=image_config.BACKGROUND_COLOR,
        )
        draw_text(
            "The quick brown fox jumps over the lazy dog",
            img, image_config.FONT_SIZE_PX,
            draw_aoi=False, line_limit=image_config.NUM_LINES_PER_PAGE,
            word_split_criterion=image_config.WORD_SPLIT_CRITERION,
            anchor_x_px=image_config.ANCHOR_POINT_X_PX,
            anchor_y_px=image_config.ANCHOR_POINT_Y_PX,
            spacing=image_config.LINE_SPACING,
            script_direction=image_config.SCRIPT_DIRECTION,
        )

        name = "stimulus_page_ascii"
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
                assert False, (
                    f"Visual diff detected: {diff_pixels} pixels changed. "
                    f"See data/_visual_diffs/{name}_side_by_side.png"
                )

    def test_stimulus_page_cjk(self, toy_image_config, request):
        """Render a CJK stimulus page and compare."""
        from text_to_picture import draw_text
        import image_config

        img = Image.new(
            "RGB",
            (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
            color=image_config.BACKGROUND_COLOR,
        )
        draw_text(
            "\u65e5\u672c\u8a9e\u306e\u30c6\u30ad\u30b9\u30c8\u306f\u5927\u6587\u672c\u65e5\u8a9e\u3067\u3059",
            img, image_config.FONT_SIZE_PX,
            draw_aoi=False, line_limit=image_config.NUM_LINES_PER_PAGE,
            word_split_criterion=image_config.WORD_SPLIT_CRITERION,
            anchor_x_px=image_config.ANCHOR_POINT_X_PX,
            anchor_y_px=image_config.ANCHOR_POINT_Y_PX,
            spacing=image_config.LINE_SPACING,
            script_direction=image_config.SCRIPT_DIRECTION,
        )

        name = "stimulus_page_cjk"
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
                assert False, (
                    f"Visual diff detected: {diff_pixels} pixels changed. "
                    f"See data/_visual_diffs/{name}_side_by_side.png"
                )

    def test_fixation_screen(self, toy_image_config, request):
        """Render a fixation screen and compare."""
        from text_to_picture import draw_text
        import image_config

        img = Image.new(
            "RGB",
            (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
            color=image_config.BACKGROUND_COLOR,
        )
        # Fixation screen is just a dot on blank background
        from text_to_picture import create_fixation_screen
        create_fixation_screen(img)

        name = "fixation_screen"
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
                assert False, (
                    f"Visual diff detected: {diff_pixels} pixels changed. "
                    f"See data/_visual_diffs/{name}_side_by_side.png"
                )
