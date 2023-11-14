LANGUAGE = 'toy'
FULL_LANGUAGE = 'English'
COUNTRY_CODE = 'toy'
LAB_NUMBER = 0

################################################################
# PLEASE DO NOT CHANGE ANYTHING BELOW THIS LINE ##############
################################################################
from utils.config_utils import read_image_configuration

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
LINE_SPACING = 3

OUTPUT_TOP_DIR = f'data/stimuli_{LANGUAGE}/'
IMAGE_DIR = OUTPUT_TOP_DIR + f'stimuli_images_{LANGUAGE}/'
QUESTION_IMAGE_DIR = OUTPUT_TOP_DIR + f'question_images_{LANGUAGE}/'
QUESTION_FILE_PATH = OUTPUT_TOP_DIR + f'multipleye_comprehension_questions_{LANGUAGE}.xlsx'
AOI_DIR = OUTPUT_TOP_DIR + f'aoi_stimuli_{LANGUAGE}/'
AOI_IMG_DIR = OUTPUT_TOP_DIR + f'aoi_stimuli_images_{LANGUAGE}/'
AOI_QUESTION_DIR = OUTPUT_TOP_DIR + f'aoi_question_images_{LANGUAGE}/'
OTHER_SCREENS_DIR = OUTPUT_TOP_DIR + f'participant_instructions_images_{LANGUAGE}/'
OTHER_SCREENS_FILE_PATH = OUTPUT_TOP_DIR + f'multipleye_participant_instructions_{LANGUAGE}.xlsx'

SHUFFLED_ANSWER_OPTIONS = OUTPUT_TOP_DIR + f'config/shuffled_option_keys_{LANGUAGE}.json'

FINAL_CONFIG = f'data/stimuli_{LANGUAGE}/config/config_{LANGUAGE}.py'

LAB_CONFIGURATION_PATH = OUTPUT_TOP_DIR + f'config/{LANGUAGE}_{COUNTRY_CODE}_{LAB_NUMBER}_lab_configuration.txt'
LAB_CONFIGURATION = read_image_configuration(LAB_CONFIGURATION_PATH)

RESOLUTION = LAB_CONFIGURATION['RESOLUTION']
SCREEN_SIZE_CM = LAB_CONFIGURATION['SCREEN_SIZE_CM']
DISTANCE_CM = LAB_CONFIGURATION['DISTANCE_CM']
SCRIPT_DIRECTION = LAB_CONFIGURATION['SCRIPT_DIRECTION']

IMAGE_SIZE_CM = (37, 28)

IMAGE_WIDTH_PX = int(IMAGE_SIZE_CM[0] * RESOLUTION[0] / SCREEN_SIZE_CM[0])
IMAGE_HEIGHT_PX = int(IMAGE_SIZE_CM[1] * RESOLUTION[1] / SCREEN_SIZE_CM[1])

MARGIN_LEFT_CM = 2.3
MARGIN_RIGHT_CM = 2.1
MARGIN_BOTTOM_CM = 3.3
MARGIN_TOP_CM = 2.3

# margins from all sides in pixels, at the moment the same for all, but can be changed later
MIN_MARGIN_LEFT_PX = int(MARGIN_LEFT_CM *
                         RESOLUTION[0] / SCREEN_SIZE_CM[0])
MIN_MARGIN_RIGHT_PX = int(MARGIN_RIGHT_CM *
                          RESOLUTION[0] / SCREEN_SIZE_CM[0])

MIN_MARGIN_TOP_PX = int(MARGIN_TOP_CM *
                        RESOLUTION[1] / SCREEN_SIZE_CM[1])
MIN_MARGIN_BOTTOM_PX = int(MARGIN_BOTTOM_CM *
                           RESOLUTION[1] / SCREEN_SIZE_CM[1])

ANCHOR_POINT_X_PX = MIN_MARGIN_LEFT_PX if SCRIPT_DIRECTION == 'LTR' else IMAGE_WIDTH_PX - MIN_MARGIN_RIGHT_PX
ANCHOR_POINT_Y_PX = MIN_MARGIN_TOP_PX

MARGIN_LEFT_CM_RTL, MARGIN_RIGHT_CM_RTL = MARGIN_RIGHT_CM, MARGIN_LEFT_CM
MIN_MARGIN_LEFT_PX_RTL, MIN_MARGIN_RIGHT_PX_RTL = MIN_MARGIN_RIGHT_PX, MIN_MARGIN_LEFT_PX


TEXT_WIDTH_PX = IMAGE_WIDTH_PX - (MIN_MARGIN_RIGHT_PX + MIN_MARGIN_LEFT_PX)
POS_BOTTOM_DOT_X_PX = IMAGE_WIDTH_PX - MIN_MARGIN_RIGHT_PX if SCRIPT_DIRECTION == 'LTR' else MIN_MARGIN_LEFT_PX
POS_BOTTOM_DOT_Y_PX = IMAGE_HEIGHT_PX - 2 * RESOLUTION[1] / SCREEN_SIZE_CM[1]

FONT_SIZE = RESOLUTION[1] // 43

####################################################################
