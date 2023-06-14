import os
import re
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm

# Set the font variables we want
FONT_TYPE = "JetBrainsMono-Regular.ttf"  # or possibly a path like "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
TEXT_COLOR = (0, 0, 0)
SPACE_LINE = 3.0  # vertical spacing between lines; in units of font’s default line height proportion

# Set the picture variables
BACKGROUND_COLOR = "#DFDFDF"  # possibly also in rgb: (231, 230, 230)

INCH_IN_CM = 2.54  # Constant; we need it in the formula; 1 inch is 2.54 cm

# if we want to check the screen information we can use this
# from screeninfo import get_monitors
# #
# for m in get_monitors():
#     print(str(m))

LANGUAGE = 'de'
OUTPUT_TOP_DIR = f'stimuli_{LANGUAGE}/'
IMAGE_DIR = OUTPUT_TOP_DIR + 'stimuli_images/'
AOI_DIR = OUTPUT_TOP_DIR + 'stimuli_aoi/'
OTHER_SCREENS_DIR = OUTPUT_TOP_DIR + 'other_screens/'
# Set this to true fi you want to generate the images with AOI boxes
AOI = False

# IMAGE_SIZE_CM = (36, 28)
IMAGE_SIZE_CM = (25, 19)

RESOLUTION = (1920, 1080)

IMAGE_SIZE_INCH = (IMAGE_SIZE_CM[0] / INCH_IN_CM, IMAGE_SIZE_CM[1] / INCH_IN_CM)

SCREEN_SIZE_CM = (34.4, 19.4)
SCREEN_SIZE_INCH = (SCREEN_SIZE_CM[0] / INCH_IN_CM, SCREEN_SIZE_CM[1] / INCH_IN_CM)

IMAGE_WIDTH_PX= int(IMAGE_SIZE_INCH[0] * RESOLUTION[0] / SCREEN_SIZE_INCH[0])
IMAGE_HEIGHT_PX = int(IMAGE_SIZE_INCH[1] * RESOLUTION[1] / SCREEN_SIZE_INCH[1])

# calculate the margins in inch, we set the margin fixed as fixed percentage of the image size
HORIZONTAL_MARGIN_INCH = 0.25
VERTICAL_MARGIN_INCH = 0.3

# margins from all sides in pixels, at the moment the same for all, but can be changed later
MIN_MARGIN_LEFT_PX = int(HORIZONTAL_MARGIN_INCH * RESOLUTION[0] / SCREEN_SIZE_INCH[0])
MIN_MARGIN_RIGHT_PX = int(HORIZONTAL_MARGIN_INCH * RESOLUTION[0] / SCREEN_SIZE_INCH[0])
MIN_MARGIN_TOP_PX = (RESOLUTION[1] // 41) * 2
MIN_MARGIN_BOTTOM_PX = (RESOLUTION[1] // 41) * 2


# Coordinates that are saying how far from the upper left corner of the image will be the text displayed, in pixels
TOP_LEFT_CORNER_X_PX = MIN_MARGIN_RIGHT_PX
TOP_LEFT_CORNER_Y_PX = MIN_MARGIN_TOP_PX

FONT_SIZE = RESOLUTION[1] // 41

def create_images():

    # Read the TSV file
    stimuli_file_name = OUTPUT_TOP_DIR + f'multipleye-stimuli-experiment-{LANGUAGE}.xlsx'
    initial_df = pd.read_excel(stimuli_file_name, nrows=12)

    if not os.path.isdir(IMAGE_DIR):
        os.mkdir(IMAGE_DIR)

    if not os.path.isdir(AOI_DIR):
        os.mkdir(AOI_DIR)

    stimulus_images = {}
    draw_aoi = False

    create_fixation_screen()

    for row_index, row in tqdm(initial_df.iterrows(), total=len(initial_df), desc='Creating images'):
        text_file_name = row['stimulus_text_title']
        text_file_name = re.sub(' ', '_', text_file_name).lower()
        text_id = int(row['stimulus_id'])

        aoi_file_name = f'{text_file_name}_{text_id}_aoi.csv'
        aoi_header = ['char', 'x', 'y', 'width', 'height', 'char_idx_in_line', 'line_idx', 'page']
        aois = []
        all_words = []

        for col_index, column_name in enumerate(initial_df.columns):

            if column_name.startswith('page') or column_name.startswith('question'):

                new_col_name_path = column_name + '_img_path'
                new_col_name_file = column_name + '_img_file'

                if new_col_name_path not in stimulus_images:
                    stimulus_images[new_col_name_path] = []

                if new_col_name_file not in stimulus_images:
                    stimulus_images[new_col_name_file] = []

                if row[[column_name]].isnull().values.any():
                    stimulus_images[new_col_name_path].append(pd.NA)
                    stimulus_images[new_col_name_file].append(pd.NA)
                    continue

                # Extract the text data from the current cell, when it is question also add answers
                if column_name.startswith('question'):
                    # we need to extract order number of the question first
                    name_parts = column_name.split('_')
                    number_of_question = name_parts[-1]


                    # we need to extract answers and add them to strings
                    answer_1 = str(f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_1_key']}] "
                                   + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_1'])
                    answer_2 = str(f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_2_key']}] "
                                   + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_2'])
                    answer_3 = str(f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_3_key']}] "
                                   + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_3'])

                    text_question = str(initial_df.iloc[row_index, col_index])
                    answers = "\n\n".join([answer_1, answer_2, answer_3])

                    # creation of the final text - question with answers
                    text = text_question + "\n\n\n" + answers

                    # Create a new image with a previously defined color background and size
                    final_image = Image.new('RGB', (IMAGE_WIDTH_PX, IMAGE_HEIGHT_PX), color=BACKGROUND_COLOR)

                    # Create a drawing object
                    draw = ImageDraw.Draw(final_image)

                    # Draw the text on the image
                    font = ImageFont.truetype(FONT_TYPE, FONT_SIZE)

                    # make sure it works for different scripts we need to use re.split (otherwise we will lose "\n"
                    # separating lines between question and answers), but next part of the code is then not properly
                    # working for a sentences that are longer than one row, I do not know why, we need to address it
                    # later
                    words = re.split(r'(\n)', text)
                    line = ""
                    lines = []
                    for word in words:
                        text_width, _ = draw.textsize(line + word, font=font)
                        # print(word,text_width, IMAGE_WIDTH_PX-minimal_right_margin, IMAGE_WIDTH_PX) #just for
                        # sanity check
                        if text_width < (IMAGE_WIDTH_PX- (MIN_MARGIN_RIGHT_PX + MIN_MARGIN_LEFT_PX)):
                            line += word + " "
                        else:
                            lines.append(line.strip())
                            line = word + " "

                    lines.append(line.strip())
                    top_left_corner_line = TOP_LEFT_CORNER_Y_PX  # we need this variable to have the original values in the next
                    # iteration, so we are creating a changing representation for the next iteration
                    for line in lines:
                        text_width, text_height = draw.textsize(line, font=font)
                        draw.text((TOP_LEFT_CORNER_X_PX, top_left_corner_line), line, fill=TEXT_COLOR, font=font)
                        top_left_corner_line += (text_height * SPACE_LINE)

                    # Save the image as a PNG file; jpg has kind of worse quality, maybe we need to check what is the
                    # best
                    filename = f"{text_file_name}_id{text_id}_{column_name}_{LANGUAGE}.png"
                    final_image.save(IMAGE_DIR + filename)

                    # store image names and paths
                    path = IMAGE_DIR + filename  # maybe we can
                    # set path in the beginning as an object
                    stimulus_images[new_col_name_path].append(path)
                    stimulus_images[new_col_name_file].append(filename)

                # if it is not a question but a reading text
                else:
                    text = str(initial_df.iloc[row_index, col_index])

                    # Create a new image with a previously defined color background and size
                    final_image = Image.new('RGB', (IMAGE_WIDTH_PX, IMAGE_HEIGHT_PX), color=BACKGROUND_COLOR)

                    # Create a drawing object
                    draw = ImageDraw.Draw(final_image)

                    # Draw the text on the image
                    font = ImageFont.truetype(FONT_TYPE, FONT_SIZE)

                    # make sure this works for different scripts!
                    paragraphs = text.split('\n')

                    top_left_corner_y_line = TOP_LEFT_CORNER_Y_PX  # we need this variable to have the original values in the next
                    for paragraph in paragraphs:
                        words = paragraph.split()
                        line = ""
                        lines = []
                        for word in words:
                            text_width, text_height = draw.textsize(line + word, font=font)
                            # print(word,text_width, IMAGE_WIDTH_PX-minimal_right_margin, IMAGE_WIDTH_PX) #just for
                            # sanity check

                            if text_width < (IMAGE_WIDTH_PX- (MIN_MARGIN_RIGHT_PX + MIN_MARGIN_LEFT_PX)):
                                line += word.strip() + " "
                            else:
                                lines.append(line.strip())
                                line = word + " "

                        lines.append(line.strip())

                        # iteration, so we are creating a changing representation for the next iteration
                        for line_idx, line in enumerate(lines):
                            if len(line) == 0:
                                continue
                            text_width, text_height = draw.textsize(line, font=font)
                            draw.text((TOP_LEFT_CORNER_X_PX, top_left_corner_y_line), line, fill=TEXT_COLOR, font=font)

                            # calculate aoi boxes for each letter
                            top_left_corner_x_letter = TOP_LEFT_CORNER_X_PX
                            letter_width = text_width / len(line)
                            words = []
                            word = ''

                            for char_idx_in_line, letter in enumerate(line):
                                if letter == ' ':
                                    # add the word once for each char
                                    words.extend([word for _ in range(len(word))] + [pd.NA])
                                    word = ''
                                else:
                                    word += letter

                                if AOI:
                                    draw.rectangle((top_left_corner_x_letter, top_left_corner_y_line,
                                                    top_left_corner_x_letter + letter_width,
                                                    top_left_corner_y_line + text_height),
                                                    outline='red', width=1)
                                    draw_aoi = True

                                # aoi_header = ['char', 'x', 'y', 'width', 'height', 'word', 'line', 'page']

                                # as the image is smaller than the actual screen we need to calculate
                                aoi_letter = [
                                    letter,
                                    top_left_corner_x_letter + ((RESOLUTION[0] - IMAGE_WIDTH_PX)  // 2),
                                    top_left_corner_y_line + ((RESOLUTION[1] - IMAGE_HEIGHT_PX)  // 2),
                                    letter_width,
                                    text_height,
                                    char_idx_in_line,
                                    line_idx,
                                    column_name
                                ]

                                # update top left corner x for next letter
                                top_left_corner_x_letter += letter_width

                                aois.append(aoi_letter)
                            words.extend([word for _ in range(len(word))])

                            all_words.extend(words)

                            # update top left corner y for next line
                            top_left_corner_y_line += (text_height * SPACE_LINE)

                    # Save the image as a PNG file; jpg has kind of worse quality, maybe we need to check what is the
                    # best
                    filename = f"{text_file_name}_id{text_id}_{column_name}_{LANGUAGE}{'_aoi' if draw_aoi else ''}.png"
                    final_image.save(IMAGE_DIR + filename)

                    # store image names and paths
                    path = IMAGE_DIR + filename  # maybe we can
                    # set path in the beginning as an object
                    stimulus_images[new_col_name_path].append(path)
                    stimulus_images[new_col_name_file].append(filename)

        aoi_df = pd.DataFrame(aois, columns=aoi_header)
        aoi_df['word'] = all_words
        aoi_df.to_csv(AOI_DIR + aoi_file_name, sep='\t', index=False)

    # Create a new csv file with the names of the pictures in the first column and their paths in the second
    image_df = pd.DataFrame(stimulus_images)
    final_df = initial_df.join(image_df)

    stimuli_file_name_stem = Path(stimuli_file_name).stem

    full_output_file_name = f'{stimuli_file_name_stem}_with_img_paths{"_aoi" if draw_aoi else ""}.csv'

    full_path = os.path.join(OUTPUT_TOP_DIR, full_output_file_name)

    final_df.to_csv(full_path,
                    sep=',',
                    index=False)


def create_fixation_screen():
    """
    Creates a fixation screen with a black background and a white cross in the middle of the screen.
    """
    # Create a new image with a previously defined color background and size
    final_image = Image.new('RGB', (IMAGE_WIDTH_PX, IMAGE_HEIGHT_PX), color=BACKGROUND_COLOR)

    # Create a drawing object
    draw = ImageDraw.Draw(final_image)

    # The fixation dot is positioned a bit left to the first char in the  middle of the line
    r = 7
    fix_x = 0.75 * MIN_MARGIN_LEFT_PX
    fix_y = 1.25 * MIN_MARGIN_TOP_PX
    draw.ellipse(
        (fix_x - r, fix_y - r, fix_x + r, fix_y + r),
        fill=None,
        outline=TEXT_COLOR,
        width=5
    )

    # Save the image as a PNG file; jpg has kind of worse quality, maybe we need to check what is the
    # best
    filename = f"fixation_screen_{LANGUAGE}.png"
    final_image.save(OTHER_SCREENS_DIR + filename)

def create_empty_screen():
    """
    Creates an empty screen
    """
    # Create a new image with a previously defined color background and size
    final_image = Image.new('RGB', (IMAGE_WIDTH_PX, IMAGE_HEIGHT_PX), color=BACKGROUND_COLOR)

    # Create a drawing object
    draw = ImageDraw.Draw(final_image)

    # Save the image as a PNG file; jpg has kind of worse quality, maybe we need to check what is the
    # best
    filename = f"empty_screen_{LANGUAGE}.png"
    final_image.save(OTHER_SCREENS_DIR + filename)

def create_welcome_screen():
    """
    Creates a welcome screen with a white background, all the logos and a blue greeting in the middle of the screen.
    """

    # We have three different logos - load them and change the size if needed
    cost_logo = Image.open("logo_imgs/cost_logo.jpg")
    cost_width, cost_height = cost_logo.size
    cost_logo_new_size = (cost_width // 7, cost_height // 7)
    cost_logo = cost_logo.resize(cost_logo_new_size)
    eu_logo = Image.open("logo_imgs/eu_fund_logo.png")
    eu_width, eu_height = eu_logo.size
    eu_logo_new_size = (eu_width // 7, eu_height // 7)
    eu_logo = eu_logo.resize(eu_logo_new_size)
    multipleye_logo = Image.open("logo_imgs/logo_multipleye.png")

    # Set the text
    welcome_df = pd.read_csv('examples/PopSci_MultiplEYE_EN_example_welcome.csv', sep=",")
    welcome_text = welcome_df["welcome_text_1"][0]
    our_blue = "#007baf"
    our_red = "#b94128"
    font_size = 38
    font_type = "open-sans-bold.ttf"

    # Create a new image with a white background and previously defined size
    final_image = Image.new('RGB', (IMAGE_WIDTH_PX, IMAGE_HEIGHT_PX), color=BACKGROUND_COLOR)

    # Create a drawing object
    draw = ImageDraw.Draw(final_image)

    # Create coordinates for three different logos
    multipleye_logo_x = (final_image.width - multipleye_logo.width) // 2
    multipleye_logo_y = 10
    multipleye_logo_position = (multipleye_logo_x, multipleye_logo_y)
    eu_logo_x = (final_image.width - eu_logo.width) // 6
    eu_logo_y = (final_image.height - eu_logo.height) - 18
    eu_logo_position = (eu_logo_x, eu_logo_y)
    cost_logo_x = ((final_image.width - eu_logo.width) // 6)  + 580
    cost_logo_y = final_image.height - cost_logo.height
    cost_logo_position = (cost_logo_x, cost_logo_y)

    # Paste the logos onto the final image at the calculated coordinates
    final_image.paste(multipleye_logo, multipleye_logo_position, mask = multipleye_logo)
    final_image.paste(eu_logo, eu_logo_position, mask = eu_logo)
    final_image.paste(cost_logo, cost_logo_position)

    # Paste the text onto the final image
    font = ImageFont.truetype(font_type, font_size)
    text_width, text_height = draw.textsize(welcome_text, font=font)
    text_x = (IMAGE_WIDTH_PX - text_width) / 2
    text_y = (IMAGE_HEIGHT_PX - text_height) / 2
    draw.text((text_x, text_y), welcome_text, font=font, fill=our_blue)

    # Save the image as a PNG file; jpg has kind of worse quality, maybe we need to check what is the
    # best
    filename = f"welcome_screen_{LANGUAGE}.png"
    final_image.save(OTHER_SCREENS_DIR  + filename)

def create_final_screen():
    """
    Creates a final screen with a white background, one logo and a blue messages in the middle of the screen.
    """

    # We have one multipleye logo - we can load other if needed
    #cost_logo = Image.open("cost_logo.jpg")
    #cost_width, cost_height = cost_logo.size
    #cost_logo_new_size = (cost_width // 7, cost_height // 7)
    #cost_logo = cost_logo.resize(cost_logo_new_size)
    #eu_logo = Image.open("eu_fund_logo.png")
    #eu_width, eu_height = eu_logo.size
    #eu_logo_new_size = (eu_width // 7, eu_height // 7)
    #eu_logo = eu_logo.resize(eu_logo_new_size)
    multipleye_logo = Image.open("logo_imgs/logo_multipleye.png")

    # Set the text
    final_df = pd.read_csv('examples/PopSci_MultiplEYE_EN_example_welcome.csv', sep=",")
    final_text_1 = final_df["final_text_1"][0]
    final_text_2 = final_df["final_text_2"][0]
    our_blue = "#007baf"
    our_red = "#b94128"
    font_size = 38
    font_type = "open-sans-bold.ttf"

    # Create a new image with a white background and previously defined size
    final_image = Image.new('RGB', (IMAGE_WIDTH_PX, IMAGE_HEIGHT_PX), color=BACKGROUND_COLOR)

    # Create a drawing object
    draw = ImageDraw.Draw(final_image)

    # Create coordinates for three different logos
    multipleye_logo_x = (final_image.width - multipleye_logo.width) // 2
    multipleye_logo_y = 10
    multipleye_logo_position = (multipleye_logo_x, multipleye_logo_y)
    #eu_logo_x = (final_image.width - eu_logo.width) // 6
    #eu_logo_y = (final_image.height - eu_logo.height) - 18
    #eu_logo_position = (eu_logo_x, eu_logo_y)
    #cost_logo_x = ((final_image.width - eu_logo.width) // 6)  + 580
    #cost_logo_y = final_image.height - cost_logo.height
    #cost_logo_position = (cost_logo_x, cost_logo_y)

    # Paste the logos onto the final image at the calculated coordinates
    final_image.paste(multipleye_logo, multipleye_logo_position, mask = multipleye_logo)
    #final_image.paste(eu_logo, eu_logo_position, mask = eu_logo)
    #final_image.paste(cost_logo, cost_logo_position)

    # Paste the texts onto the final image
    font = ImageFont.truetype(font_type, font_size)
    text_width_A, text_height_A = draw.textsize(final_text_1, font=font)
    text_x_A = (IMAGE_WIDTH_PX - text_width_A) / 2
    text_y_A = (IMAGE_HEIGHT_PX - text_height_A) / 2
    draw.text((text_x_A, text_y_A), final_text_1, font=font, fill=our_blue)

    text_width_B, text_height_B = draw.textsize(final_text_2, font=font)
    text_x_B = (IMAGE_WIDTH_PX - text_width_B) / 2
    text_y_B = (IMAGE_HEIGHT_PX + text_height_B + (text_height_A * 2)) / 2
    draw.text((text_x_B, text_y_B), final_text_2, font=font, fill=our_red)

    # Save the image as a PNG file; jpg has kind of worse quality, maybe we need to check what is the
    # best
    filename = f"final_screen_{LANGUAGE}.png"
    final_image.save(OTHER_SCREENS_DIR  + filename)

if __name__ == '__main__':
    if not os.path.isdir(OTHER_SCREENS_DIR):
        os.mkdir(OTHER_SCREENS_DIR)

    create_images()
    create_welcome_screen()
    create_final_screen()
    create_empty_screen()
    create_fixation_screen()
