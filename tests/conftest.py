"""Shared fixtures for the test suite.

Fixtures are grouped by marker:
- unit: no data/ or font dependencies
- integration: needs data/ + fonts present
- visual: slow, needs full env, produces diff images
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
DATA_DIR = REPO_ROOT / "data"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _toy_dataset_dir() -> Path:
    """Return the TOY dataset directory, or skip if absent."""
    d = DATA_DIR / "stimuli_MultiplEYE_TOY_X_x_1_1"
    if not d.is_dir():
        pytest.skip("TOY dataset not present under data/")
    return d


def _toy_lab_config_path() -> Path:
    p = _toy_dataset_dir() / "config" / "MultiplEYE_TOY_X_x_1_1_lab_configuration.json"
    if not p.is_file():
        pytest.skip("TOY lab-configuration JSON not found")
    return p


# ---------------------------------------------------------------------------
# Markers / skips
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(config, items):
    """Auto-skip integration/visual tests when data/ is missing."""
    if not (DATA_DIR / "stimuli_MultiplEYE_TOY_X_x_1_1").is_dir():
        skip_no_data = pytest.mark.skip(reason="data/ fixture not present")
        for item in items:
            if "integration" in item.keywords or "visual" in item.keywords:
                item.add_marker(skip_no_data)


def pytest_addoption(parser):
    parser.addoption(
        "--update-baselines", action="store_true", default=False,
        help="Update visual regression baselines instead of comparing",
    )


# ---------------------------------------------------------------------------
# Fixtures: unit (no data needed)
# ---------------------------------------------------------------------------

@pytest.fixture
def repo_root():
    return REPO_ROOT


# ---------------------------------------------------------------------------
# Fixtures: integration (needs data/ + fonts)
# ---------------------------------------------------------------------------

@pytest.fixture
def toy_dataset_dir():
    return _toy_dataset_dir()


@pytest.fixture
def toy_lab_config_path():
    return _toy_lab_config_path()


@pytest.fixture
def toy_image_config():
    """Import image_config patched to the TOY dataset.

    This re-imports image_config with the TOY globals so that downstream
    modules (text_to_picture, config_utils, randomization) pick up the
    correct paths.  Only call from integration / visual tests.
    """
    import importlib
    import image_config as ic

    # Save ALL module-level attributes that will be patched
    _PATCH_KEYS = [
        "LANGUAGE", "COUNTRY_CODE", "CITY", "YEAR", "LAB_NUMBER",
        "SUBCORPUS", "TESTING_IMAGES",
        "OUTPUT_TOP_DIR", "IMAGE_DIR", "QUESTION_IMAGE_DIR", "AOI_DIR",
        "AOI_IMG_DIR", "AOI_QUESTION_DIR", "OTHER_SCREENS_DIR",
        "OTHER_SCREENS_FILE_PATH", "STIMULI_FILE_PATH", "QUESTION_FILE_PATH",
        "FINAL_CONFIG", "ANSWER_OPTION_FOLDER", "LAB_CONFIGURATION_PATH",
        "LAB_CONFIGURATION", "RESOLUTION", "SCREEN_SIZE_CM", "DISTANCE_CM",
        "SCRIPT_DIRECTION", "MULTIPLE_DEVICES",
        "IMAGE_WIDTH_PX", "IMAGE_HEIGHT_PX",
        "MIN_MARGIN_LEFT_PX", "MIN_MARGIN_RIGHT_PX",
        "MIN_MARGIN_TOP_PX", "MIN_MARGIN_BOTTOM_PX",
        "ANCHOR_POINT_X_PX", "ANCHOR_POINT_Y_PX", "TEXT_WIDTH_PX",
        "FONT_TYPE", "FONT_TYPE_BOLD", "WORD_SPLIT_CRITERION",
        "NUM_PERMUTATIONS", "VERSION_START", "FONT_SIZE_PX",
        "NUM_LINES_PER_PAGE", "NUM_LINES_PER_INSTRUCTION_PAGE",
        "POS_BOTTOM_DOT_X_PX", "POS_BOTTOM_DOT_Y_PX",
        "POS_TOP_DOT_X_PX", "POS_TOP_DOT_Y_PX",
        "FIX_DOT_RADIUS_PX", "FIX_DOT_WIDTH_PX",
    ]
    orig = {k: getattr(ic, k) for k in _PATCH_KEYS if hasattr(ic, k)}

    # Patch to TOY
    ic.LANGUAGE = "toy"
    ic.COUNTRY_CODE = "X"
    ic.CITY = "X"
    ic.YEAR = 1
    ic.LAB_NUMBER = 1
    ic.SUBCORPUS = ""
    ic.TESTING_IMAGES = True

    # Re-evaluate derived paths that depend on the above
    # (they are computed at module level, so we must re-run those lines)
    ic.OUTPUT_TOP_DIR = (
        f'data/stimuli_MultiplEYE_{ic.SUBCORPUS + "_" if ic.SUBCORPUS else ""}'
        f'{ic.LANGUAGE.upper()}_{ic.COUNTRY_CODE.upper()}_{ic.CITY}_{ic.LAB_NUMBER}_{ic.YEAR}/'
    )
    ic.IMAGE_DIR = ic.OUTPUT_TOP_DIR + f'stimuli_images_{ic.SUBCORPUS + "_" if ic.SUBCORPUS else ""}{ic.LANGUAGE}_{ic.COUNTRY_CODE}_{ic.LAB_NUMBER}/'
    ic.QUESTION_IMAGE_DIR = ic.OUTPUT_TOP_DIR + f'question_images_{ic.SUBCORPUS + "_" if ic.SUBCORPUS else ""}{ic.LANGUAGE}_{ic.COUNTRY_CODE}_{ic.LAB_NUMBER}/'
    ic.AOI_DIR = ic.OUTPUT_TOP_DIR + f'aoi_stimuli_{ic.SUBCORPUS + "_" if ic.SUBCORPUS else ""}{ic.LANGUAGE}_{ic.COUNTRY_CODE}_{ic.LAB_NUMBER}/'
    ic.AOI_IMG_DIR = ic.OUTPUT_TOP_DIR + f'aoi_stimuli_images_{ic.SUBCORPUS + "_" if ic.SUBCORPUS else ""}{ic.LANGUAGE}_{ic.COUNTRY_CODE}_{ic.LAB_NUMBER}/'
    ic.AOI_QUESTION_DIR = ic.OUTPUT_TOP_DIR + f'aoi_question_images_{ic.SUBCORPUS + "_" if ic.SUBCORPUS else ""}{ic.LANGUAGE}_{ic.COUNTRY_CODE}_{ic.LAB_NUMBER}/'
    ic.OTHER_SCREENS_DIR = ic.OUTPUT_TOP_DIR + f'participant_instructions_images_{ic.SUBCORPUS + "_" if ic.SUBCORPUS else ""}{ic.LANGUAGE}_{ic.COUNTRY_CODE}_{ic.LAB_NUMBER}/'

    ic.OTHER_SCREENS_FILE_PATH = ic.OUTPUT_TOP_DIR + f'multipleye_{ic.SUBCORPUS + "_" if ic.SUBCORPUS else ""}participant_instructions_{ic.LANGUAGE}.xlsx'
    ic.STIMULI_FILE_PATH = ic.OUTPUT_TOP_DIR + f'multipleye_{ic.SUBCORPUS + "_" if ic.SUBCORPUS else ""}stimuli_experiment_{ic.LANGUAGE}.xlsx'
    ic.QUESTION_FILE_PATH = ic.OUTPUT_TOP_DIR + f'multipleye_{ic.SUBCORPUS + "_" if ic.SUBCORPUS else ""}comprehension_questions_{ic.LANGUAGE}.xlsx'

    ic.FINAL_CONFIG = ic.OUTPUT_TOP_DIR + ('config/config_'
        f'{ic.SUBCORPUS + "_" if ic.SUBCORPUS else ""}{ic.LANGUAGE}_{ic.COUNTRY_CODE}_{ic.CITY}_{ic.LAB_NUMBER}_{ic.YEAR}.py')

    ic.ANSWER_OPTION_FOLDER = ic.OUTPUT_TOP_DIR + (f'config/question_answer_option_shuffling_'
        f'{ic.SUBCORPUS + "_" if ic.SUBCORPUS else ""}{ic.LANGUAGE}_{ic.COUNTRY_CODE}_{ic.LAB_NUMBER}/')

    ic.LAB_CONFIGURATION_PATH = ic.OUTPUT_TOP_DIR + (f'config/MultiplEYE_{ic.SUBCORPUS + "_" if ic.SUBCORPUS else ""}'
        f'{ic.LANGUAGE.upper()}_{ic.COUNTRY_CODE.upper()}_{ic.CITY}_{ic.LAB_NUMBER}_{ic.YEAR}_lab_configuration.json')

    # Font for 'toy' language. Fall back to the default (JetBrains Mono)
    # since there's no TOY-specific font.  If the font file is missing,
    # skip the test rather than crashing at import time.
    from utils.config_utils import read_image_configuration, calculate_font_size
    ic.LAB_CONFIGURATION = read_image_configuration(ic.LAB_CONFIGURATION_PATH)

    ic.RESOLUTION = ic.LAB_CONFIGURATION['RESOLUTION']
    ic.SCREEN_SIZE_CM = ic.LAB_CONFIGURATION['SCREEN_SIZE_CM']
    ic.DISTANCE_CM = ic.LAB_CONFIGURATION['DISTANCE_CM']
    ic.SCRIPT_DIRECTION = ic.LAB_CONFIGURATION['SCRIPT_DIRECTION'].lower()
    ic.MULTIPLE_DEVICES = ic.LAB_CONFIGURATION['MULTIPLE_DEVICES']

    ic.IMAGE_WIDTH_PX = int(37 * ic.RESOLUTION[0] / ic.SCREEN_SIZE_CM[0])
    ic.IMAGE_WIDTH_PX = ic.IMAGE_WIDTH_PX if ic.IMAGE_WIDTH_PX % 2 == 0 else ic.IMAGE_WIDTH_PX + 1
    ic.IMAGE_HEIGHT_PX = int(28 * ic.RESOLUTION[1] / ic.SCREEN_SIZE_CM[1])
    ic.IMAGE_HEIGHT_PX = ic.IMAGE_HEIGHT_PX if ic.IMAGE_HEIGHT_PX % 2 == 0 else ic.IMAGE_HEIGHT_PX + 1

    ic.MIN_MARGIN_LEFT_PX = int(2.3 * ic.RESOLUTION[0] / ic.SCREEN_SIZE_CM[0])
    ic.MIN_MARGIN_RIGHT_PX = int(2.1 * ic.RESOLUTION[0] / ic.SCREEN_SIZE_CM[0])
    ic.MIN_MARGIN_TOP_PX = int(2.5 * ic.RESOLUTION[1] / ic.SCREEN_SIZE_CM[1])
    ic.MIN_MARGIN_BOTTOM_PX = int(3.3 * ic.RESOLUTION[1] / ic.SCREEN_SIZE_CM[1])

    ic.ANCHOR_POINT_X_PX = ic.MIN_MARGIN_LEFT_PX if ic.SCRIPT_DIRECTION == 'ltr' else ic.IMAGE_WIDTH_PX - ic.MIN_MARGIN_RIGHT_PX
    ic.ANCHOR_POINT_Y_PX = ic.MIN_MARGIN_TOP_PX

    ic.TEXT_WIDTH_PX = ic.IMAGE_WIDTH_PX - (ic.MIN_MARGIN_RIGHT_PX + ic.MIN_MARGIN_LEFT_PX)

    # Font: for 'toy' use the default font (JetBrains Mono) if it exists,
    # otherwise fall back to NotoSansJP (which is guaranteed present in the
    # test env since the TOY dataset was set up with it).
    default_font = REPO_ROOT / "fonts" / "JetBrainsMono-Regular.ttf"
    fallback_font = REPO_ROOT / "fonts" / "NotoSansJP-Regular.ttf"
    if default_font.is_file():
        ic.FONT_TYPE = "fonts/JetBrainsMono-Regular.ttf"
        ic.FONT_TYPE_BOLD = "fonts/JetBrainsMono-ExtraBold.ttf"
    elif fallback_font.is_file():
        ic.FONT_TYPE = "fonts/NotoSansJP-Regular.ttf"
        ic.FONT_TYPE_BOLD = "fonts/NotoSansJP-Bold.ttf"
    else:
        pytest.skip("No font files found under fonts/")

    ic.WORD_SPLIT_CRITERION = ' '
    ic.NUM_PERMUTATIONS = 10
    ic.VERSION_START = 1
    ic.FONT_SIZE_PX = calculate_font_size(lang=ic.LANGUAGE)

    ic.NUM_LINES_PER_PAGE = round(
        (ic.IMAGE_HEIGHT_PX - ic.MIN_MARGIN_BOTTOM_PX - ic.MIN_MARGIN_TOP_PX)
        / (ic.FONT_SIZE_PX * ic.LINE_SPACING), 0
    )
    ic.NUM_LINES_PER_INSTRUCTION_PAGE = round(
        (ic.IMAGE_HEIGHT_PX - ic.MIN_MARGIN_BOTTOM_PX - ic.MIN_MARGIN_TOP_PX)
        / (ic.FONT_SIZE_PX * ic.LINE_SPACING_INSTRUCTION), 0
    )

    ic.POS_BOTTOM_DOT_X_PX = ic.IMAGE_WIDTH_PX - ic.MIN_MARGIN_RIGHT_PX if ic.SCRIPT_DIRECTION == 'ltr' else ic.MIN_MARGIN_LEFT_PX
    ic.POS_BOTTOM_DOT_Y_PX = int(ic.IMAGE_HEIGHT_PX - 2 * ic.RESOLUTION[1] / ic.SCREEN_SIZE_CM[1])
    ic.POS_TOP_DOT_X_PX = 0.75 * ic.MIN_MARGIN_RIGHT_PX if ic.SCRIPT_DIRECTION == 'ltr' else ic.IMAGE_WIDTH_PX - 0.75 * ic.MIN_MARGIN_RIGHT_PX
    ic.POS_TOP_DOT_Y_PX = 1.25 * ic.MIN_MARGIN_TOP_PX
    ic.FIX_DOT_RADIUS_PX = int(0.1 * ic.MIN_MARGIN_LEFT_PX) if int(0.1 * ic.MIN_MARGIN_LEFT_PX) > 7 else 7
    ic.FIX_DOT_WIDTH_PX = int(ic.FIX_DOT_RADIUS_PX * 5 // 7)

    yield ic

    # Restore originals
    for k, v in orig.items():
        setattr(ic, k, v)
