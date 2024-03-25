LANGUAGE = 'en'
FULL_LANGUAGE = 'English'
COUNTRY_CODE = 'gb'
LAB_NUMBER = 1

################################################################
# PLEASE DO NOT CHANGE ANYTHING BELOW THIS LINE ##############
################################################################
from utils.config_utils import read_image_configuration
from pathlib import Path

CODE_SCR = Path(__file__).parent

REPO_ROOT = CODE_SCR.parent

# set the font based on the language
if LANGUAGE == 'he':
    FONT_TYPE = "fonts/FreeMono.ttf"
    FONT_TYPE_BOLD = "fonts/FreeMonoBold.ttf"
else:
    FONT_TYPE = "fonts/JetBrainsMono-Regular.ttf"
    FONT_TYPE_BOLD = "fonts/JetBrainsMono-ExtraBold.ttf"

TEXT_COLOR = (0, 0, 0)
BACKGROUND_COLOR = (231, 230, 230)

# vertical spacing between lines
LINE_SPACING = 2.9

NUM_PERMUTATIONS = 2

OUTPUT_TOP_DIR = f'data/stimuli_{LANGUAGE}_{COUNTRY_CODE}_{LAB_NUMBER}/'
IMAGE_DIR = OUTPUT_TOP_DIR + f'stimuli_images_{LANGUAGE}_{COUNTRY_CODE}_{LAB_NUMBER}/'
QUESTION_IMAGE_DIR = OUTPUT_TOP_DIR + f'question_images_{LANGUAGE}_{COUNTRY_CODE}_{LAB_NUMBER}/'
AOI_DIR = OUTPUT_TOP_DIR + f'aoi_stimuli_{LANGUAGE}_{COUNTRY_CODE}_{LAB_NUMBER}/'
AOI_IMG_DIR = OUTPUT_TOP_DIR + f'aoi_stimuli_images_{LANGUAGE}_{COUNTRY_CODE}_{LAB_NUMBER}/'
AOI_QUESTION_DIR = OUTPUT_TOP_DIR + f'aoi_question_images_{LANGUAGE}_{COUNTRY_CODE}_{LAB_NUMBER}/'
OTHER_SCREENS_DIR = OUTPUT_TOP_DIR + f'participant_instructions_images_{LANGUAGE}_{COUNTRY_CODE}_{LAB_NUMBER}/'

OTHER_SCREENS_FILE_PATH = OUTPUT_TOP_DIR + f'multipleye_participant_instructions_{LANGUAGE}.xlsx'
STIMULI_FILE_PATH = OUTPUT_TOP_DIR + f'multipleye_stimuli_experiment_{LANGUAGE}.xlsx'
QUESTION_FILE_PATH = OUTPUT_TOP_DIR + f'multipleye_comprehension_questions_{LANGUAGE}.xlsx'

BLOCK_CONFIG_PATH = CODE_SCR / "global_configs/stimulus_to_block_mapping.csv"

FINAL_CONFIG = (f'data/stimuli_{LANGUAGE}_{COUNTRY_CODE}_{LAB_NUMBER}/config/config_'
                f'{LANGUAGE}_{COUNTRY_CODE}_{LAB_NUMBER}.py')

ANSWER_OPTION_FOLDER = OUTPUT_TOP_DIR + (f'config/question_answer_option_shuffling_'
                                         f'{LANGUAGE}_{COUNTRY_CODE}_{LAB_NUMBER}/')

LAB_CONFIGURATION_PATH = OUTPUT_TOP_DIR + f'config/{LANGUAGE}_{COUNTRY_CODE}_{LAB_NUMBER}_lab_configuration.txt'
LAB_CONFIGURATION = read_image_configuration(LAB_CONFIGURATION_PATH)

RESOLUTION = LAB_CONFIGURATION['RESOLUTION']
SCREEN_SIZE_CM = LAB_CONFIGURATION['SCREEN_SIZE_CM']
DISTANCE_CM = LAB_CONFIGURATION['DISTANCE_CM']
SCRIPT_DIRECTION = LAB_CONFIGURATION['SCRIPT_DIRECTION']

IMAGE_SIZE_CM = (37, 28)

MAX_CHARS_PER_LINE = 82

IMAGE_WIDTH_PX = int(IMAGE_SIZE_CM[0] * RESOLUTION[0] / SCREEN_SIZE_CM[0])
IMAGE_HEIGHT_PX = int(IMAGE_SIZE_CM[1] * RESOLUTION[1] / SCREEN_SIZE_CM[1])

MARGIN_LEFT_CM = 2.3
MARGIN_RIGHT_CM = 2.1
MARGIN_BOTTOM_CM = 3.3
MARGIN_TOP_CM = 2.5

# margins from all sides in pixels, at the moment the same for all, but can be changed later
MIN_MARGIN_LEFT_PX = MARGIN_LEFT_CM * RESOLUTION[0] / SCREEN_SIZE_CM[0]
MIN_MARGIN_RIGHT_PX = MARGIN_RIGHT_CM * RESOLUTION[0] / SCREEN_SIZE_CM[0]

MIN_MARGIN_TOP_PX = MARGIN_TOP_CM * RESOLUTION[1] / SCREEN_SIZE_CM[1]
MIN_MARGIN_BOTTOM_PX = MARGIN_BOTTOM_CM * RESOLUTION[1] / SCREEN_SIZE_CM[1]

ANCHOR_POINT_X_PX = MIN_MARGIN_LEFT_PX if SCRIPT_DIRECTION == 'ltr' else IMAGE_WIDTH_PX - MIN_MARGIN_RIGHT_PX
ANCHOR_POINT_Y_PX = MIN_MARGIN_TOP_PX

MARGIN_LEFT_CM_RTL, MARGIN_RIGHT_CM_RTL = MARGIN_RIGHT_CM, MARGIN_LEFT_CM
MIN_MARGIN_LEFT_PX_RTL, MIN_MARGIN_RIGHT_PX_RTL = MIN_MARGIN_RIGHT_PX, MIN_MARGIN_LEFT_PX


TEXT_WIDTH_PX = IMAGE_WIDTH_PX - (MIN_MARGIN_RIGHT_PX + MIN_MARGIN_LEFT_PX)
POS_BOTTOM_DOT_X_PX = IMAGE_WIDTH_PX - MIN_MARGIN_RIGHT_PX if SCRIPT_DIRECTION == 'ltr' else MIN_MARGIN_LEFT_PX
POS_BOTTOM_DOT_Y_PX = IMAGE_HEIGHT_PX - 2 * RESOLUTION[1] / SCREEN_SIZE_CM[1]

FONT_SIZE_CM = 0.67
FONT_SIZE_PX = FONT_SIZE_CM * RESOLUTION[1] / SCREEN_SIZE_CM[1]

####################################################################
