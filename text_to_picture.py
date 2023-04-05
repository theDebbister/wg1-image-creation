import os
import re
import math

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm

# Set the input table variables, can be hard coded in the final script; nan cells are later skipped, so we can use
# the whole range of the table, I just do not know what will be the final size of the table
row_range = 4
column_range = 14

# Set the font variables we want
font_size = 25
font_type = "Cascadia.ttf"  # or possibly a path like "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
text_color = (0, 0, 0)
space_line = 3.0  # vertical spacing between lines; in units of font’s default line height proporton

# Set the picture variables
background_color = "#E7E7E7"  # possibly also in rgb: (231, 230, 230)

# # Calculate size of the image from centimeters to pixels However we can start with pixel sizes and then calculate how
# # big the picture will be, but this is the whole topic we probably need to discuss later
# dpi = 72  # variable, it can be changed; dots per inch; how many pixels are in one inch aka 2.54 cm; the value 72 is
# # taken from the properties of one already created image from this script
# inch_in_cm = 2.54  # Constant; we need it in the formula; 1 inch is 2.54 cm
# image_width_px = int((image_width_cm * dpi) / inch_in_cm)  # in pixels, for 34 cm it is 963 px
# image_height_px = int((image_height_cm * dpi) / inch_in_cm)  # in pixels, for 26 cm it is 737 px

# if we want to check the screen information we can use this
# from screeninfo import get_monitors
#
# for m in get_monitors():
#     print(str(m))

IMAGE_DIR = 'stimuli_images/'

IMAGE_SIZE_CM = (34, 26)

RESOLUTION = (1920, 1080)
# IMAGE_SIZE_INCH = (13.3, 10.2) # my screen is too small, so I'm temporally using a different image size
IMAGE_SIZE_INCH = (9.1, 6.5)
SCREEN_SIZE_INCH = (13.9, 7.5)

image_width_px = int(IMAGE_SIZE_INCH[0] * RESOLUTION[0] / SCREEN_SIZE_INCH[0])
image_height_px = int(IMAGE_SIZE_INCH[1] * RESOLUTION[1] / SCREEN_SIZE_INCH[1])

# calculate the margins in inch, we set the margin fixed as fixed percentage of the image size
HORIZONTAL_MARGIN_INCH = IMAGE_SIZE_INCH[0] * 0.1
VERTICAL_MARGIN_INCH = IMAGE_SIZE_INCH[1] * 0.15

# margins from all sides in pixels, at the moment the same for all, but can be changed later
min_margin_left_px = int(HORIZONTAL_MARGIN_INCH * RESOLUTION[0] / SCREEN_SIZE_INCH[0])
min_margin_right_px = int(HORIZONTAL_MARGIN_INCH * RESOLUTION[0] / SCREEN_SIZE_INCH[0])
min_margin_top_px = int(VERTICAL_MARGIN_INCH * RESOLUTION[1] / SCREEN_SIZE_INCH[1])
min_margin_bottom_px = int(VERTICAL_MARGIN_INCH * RESOLUTION[1] / SCREEN_SIZE_INCH[1])


# Coordinates that are saying how far from the upper left corner of the image will be the text displayed, in pixels
coordinate_x_px = min_margin_right_px
coordinate_y_px = min_margin_top_px


def create_images():

    # Read the TSV file
    initial_df = pd.read_csv('PopSci_MultiplEYE_EN_example_stimuli.csv', sep="\t")

    if not os.path.isdir(IMAGE_DIR):
        os.mkdir(IMAGE_DIR)

    # Set a list where will be stored the names of the png files and their paths
    file_list = []

    # Loop through the rows and columns of the DataFrame

    stimulus_images = {}

    for row_index, row in tqdm(initial_df.iterrows(), total=len(initial_df), desc='Creating images'):
        text_file_name = row['stimulus_text_title']
        text_file_name = re.sub(' ', '_', text_file_name).lower()
        text_id = row['stimulus_id']

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
                    answer_1 = str(f"[{initial_df.loc[row_index, 'answer_option_' + number_of_question + '_1_key']}] "
                                   + initial_df.loc[row_index, 'answer_option_' + number_of_question + '_1'])
                    answer_2 = str(f"[{initial_df.loc[row_index, 'answer_option_' + number_of_question + '_2_key']}] "
                                   + initial_df.loc[row_index, 'answer_option_' + number_of_question + '_2'])
                    answer_3 = str(f"[{initial_df.loc[row_index, 'answer_option_' + number_of_question + '_3_key']}] "
                                   + initial_df.loc[row_index, 'answer_option_' + number_of_question + '_3'])

                    text_question = str(initial_df.iloc[row_index, col_index])
                    answers = "\n\n".join([answer_1, answer_2, answer_3])

                    # creation of the final text - question with answers
                    text = text_question + "\n\n\n" + answers

                    # Create a new image with a previously defined color background and size
                    final_image = Image.new('RGB', (image_width_px, image_height_px), color=background_color)

                    # Create a drawing object
                    draw = ImageDraw.Draw(final_image)

                    # Draw the text on the image
                    font = ImageFont.truetype(font_type, font_size)

                    # make sure it works for different scripts we need to use re.split (otherwise we will lose "\n"
                    # separating lines between question and answers), but next part of the code is then not properly
                    # working for a sentences that are longer than one row, I do not know why, we need to address it
                    # later
                    words = re.split(r'(\n)', text)
                    line = ""
                    lines = []
                    for word in words:
                        text_width, text_height = draw.textsize(line + word, font=font)
                        # print(word,text_width, image_width_px-minimal_right_margin, image_width_px) #just for
                        # sanity check
                        if text_width < (image_width_px - (
                                min_margin_right_px * 2)):  # This is kind of weird, it sets the distance from the right
                            # margin but it must be twice the size of the "minimal_right_margin", otherwise it does not
                            # work, I have no idea why; however it displays unmultipled distance, it is probably some
                            # logic flaw i do not see
                            line += word + " "
                        else:
                            lines.append(line.strip())
                            line = word + " "
                    lines.append(line.strip())
                    coordinate_y_line = coordinate_y_px  # we need this variable to have the original values in the next
                    # iteration, so we are creating a changing representation for the next iteration
                    for line in lines:
                        draw.text((coordinate_x_px, coordinate_y_line), line, fill=text_color, font=font)
                        coordinate_y_line += (text_height * space_line)

                    # Save the image as a PNG file; jpg has kind of worse quality, maybe we need to check what is the
                    # best
                    filename = f"{text_file_name}_id{text_id}_{column_name}.png"
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
                    final_image = Image.new('RGB', (image_width_px, image_height_px), color=background_color)

                    # Create a drawing object
                    draw = ImageDraw.Draw(final_image)

                    # Draw the text on the image
                    font = ImageFont.truetype(font_type, font_size)

                    # make sure it works for different scripts
                    words = text.split()
                    line = ""
                    lines = []
                    for word in words:
                        text_width, text_height = draw.textsize(line + word, font=font)
                        # print(word,text_width, image_width_px-minimal_right_margin, image_width_px) #just for
                        # sanity check
                        if text_width < (image_width_px - (
                                min_margin_right_px * 2)):  # This is kind of weird, it sets the distance from the right
                            # margin but it must be twice the size of the "minimal_right_margin", otherwise it does not
                            # work, I have no idea why; however it displays unmultipled distance, it is probably some
                            # logic flaw i do not see
                            line += word + " "
                        else:
                            lines.append(line.strip())
                            line = word + " "
                    lines.append(line.strip())
                    coordinate_y_line = coordinate_y_px  # we need this variable to have the original values in the next
                    # iteration, so we are creating a changing representation for the next iteration
                    for line in lines:
                        draw.text((coordinate_x_px, coordinate_y_line), line, fill=text_color, font=font)
                        coordinate_y_line += (text_height * space_line)

                    # Save the image as a PNG file; jpg has kind of worse quality, maybe we need to check what is the
                    # best
                    filename = f"{text_file_name}_id{text_id}_{column_name}.png"
                    final_image.save(IMAGE_DIR + filename)

                    # store image names and paths
                    path = IMAGE_DIR + filename  # maybe we can
                    # set path in the beginning as an object
                    stimulus_images[new_col_name_path].append(path)
                    stimulus_images[new_col_name_file].append(filename)

    # Create a new csv file with the names of the pictures in the first column and their paths in the second
    image_df = pd.DataFrame(stimulus_images)
    final_df = initial_df.join(image_df)

    final_df.to_csv('PopSci_MultiplEYE_EN_example_stimuli_with_img_paths.csv', sep=',', index=False)


if __name__ == '__main__':
    create_images()
