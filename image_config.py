LANGUAGE = 'en'
RESOLUTION = (1920, 1080)
SCREEN_SIZE_CM = (54.4, 30.3)

################################################################
# PLEASE DO NOT CHANGE EVERYTHING BELOW THIS LINE ##############
################################################################
# Set this to true if you want to generate the images with AOI boxes
AOI = False

NUM_STIMULI = 12
NUM_PRACTICE_STIMULI = 2
NUM_OTHER_SCREENS = 9

FONT_TYPE = "fonts/JetBrainsMono-Regular.ttf"
FONT_TYPE_BOLD = "fonts/JetBrainsMono-ExtraBold.ttf"
TEXT_COLOR = (0, 0, 0)
# vertical spacing between lines; in units of font’s default line height proportion
SPACE_LINE = 3

# Set the picture variables
BACKGROUND_COLOR = "#DFDFDF"  # possibly also in rgb: (231, 230, 230)

INCH_IN_CM = 2.54  # Constant; we need it in the formula; 1 inch is 2.54 cm

OUTPUT_TOP_DIR = f'stimuli_{LANGUAGE}/'
IMAGE_DIR = OUTPUT_TOP_DIR + 'stimuli_images/'
AOI_DIR = OUTPUT_TOP_DIR + 'stimuli_aoi/'
AOI_IMG_DIR = OUTPUT_TOP_DIR + 'stimuli_aoi_images/'
PRACTICE_IMAGE_DIR = OUTPUT_TOP_DIR + 'practice_images/'
PRACTICE_AOI_DIR = OUTPUT_TOP_DIR + 'practice_aoi/'
PRACTICE_AOI_IMG_DIR = OUTPUT_TOP_DIR + 'practice_aoi_images/'
OTHER_SCREENS_DIR = OUTPUT_TOP_DIR + 'other_screens/'
OTHER_SCREENS_FILE_PATH = OUTPUT_TOP_DIR + f'multipleye-other-screens-{LANGUAGE}.xlsx'

################################################################
# COPY TO EXPERIMENT FOLDER ####################################
################################################################

# also copy resolution from above!!

# also copy screen size in cm from above!!

IMAGE_SIZE_CM = (37, 28)
IMAGE_SIZE_INCH = (IMAGE_SIZE_CM[0] / INCH_IN_CM,
                   IMAGE_SIZE_CM[1] / INCH_IN_CM)

SCREEN_SIZE_INCH = (SCREEN_SIZE_CM[0] /
                    INCH_IN_CM, SCREEN_SIZE_CM[1] / INCH_IN_CM)

IMAGE_WIDTH_PX = int(IMAGE_SIZE_INCH[0] * RESOLUTION[0] / SCREEN_SIZE_INCH[0])
IMAGE_HEIGHT_PX = int(IMAGE_SIZE_INCH[1] * RESOLUTION[1] / SCREEN_SIZE_INCH[1])

# calculate the margins in inch, we set the margin fixed as fixed percentage of the image size
MARGIN_LEFT_INCH = 2.3 / INCH_IN_CM
MARGIN_RIGHT_INCH = 2 / INCH_IN_CM

MARGIN_BOTTOM_INCH = 3.3 / INCH_IN_CM
MARGIN_TOP_INCH = 1.3 / INCH_IN_CM

# margins from all sides in pixels, at the moment the same for all, but can be changed later
MIN_MARGIN_LEFT_PX = int(MARGIN_LEFT_INCH *
                         RESOLUTION[0] / SCREEN_SIZE_INCH[0])
MIN_MARGIN_RIGHT_PX = int(MARGIN_RIGHT_INCH *
                          RESOLUTION[0] / SCREEN_SIZE_INCH[0])

MIN_MARGIN_TOP_PX = int(MARGIN_TOP_INCH *
                        RESOLUTION[1] / SCREEN_SIZE_INCH[1])
MIN_MARGIN_BOTTOM_PX = int(MARGIN_BOTTOM_INCH *
                           RESOLUTION[1] / SCREEN_SIZE_INCH[1])

# Coordinates that are saying how far from the upper left corner of the image will be the text displayed, in pixels
TOP_LEFT_CORNER_X_PX = MIN_MARGIN_LEFT_PX
TOP_LEFT_CORNER_Y_PX = MIN_MARGIN_TOP_PX

POS_BOTTOM_DOT_X_PX = IMAGE_WIDTH_PX - MIN_MARGIN_RIGHT_PX
POS_BOTTOM_DOT_Y_PX = IMAGE_HEIGHT_PX - (2 / INCH_IN_CM) * RESOLUTION[1] / SCREEN_SIZE_INCH[1]

FONT_SIZE = RESOLUTION[1] // 43
print(FONT_SIZE)

####################################################################
