import csv
import os
import re
from collections import OrderedDict
from pathlib import Path
import random

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from screeninfo import get_monitors
from tqdm import tqdm

import image_config


def create_images(
        stimuli_file_name: str,
        question_file_name: str,
        image_dir: str,
        question_dir: str,
        aoi_dir: str,
        question_aoi_dir: str,
        aoi_image_dir: str
):
    initial_stimulus_df = pd.read_excel(stimuli_file_name)
    initial_stimulus_df.dropna(subset=['stimulus_id'], inplace=True)

    question_df = pd.read_excel(question_file_name)
    question_df.dropna(subset=['stimulus_id'], inplace=True)

    if not os.path.isdir(image_dir):
        os.mkdir(image_dir)

    if not os.path.isdir(aoi_dir):
        os.mkdir(aoi_dir)

    if not os.path.isdir(aoi_image_dir):
        os.mkdir(aoi_image_dir)

    if not os.path.isdir(question_dir):
        os.mkdir(question_dir)

    if not os.path.isdir(question_aoi_dir):
        os.mkdir(question_aoi_dir)

    stimulus_images = {}
    question_images = {}

    for row_index, row in tqdm(initial_stimulus_df.iterrows(), total=len(initial_stimulus_df),
                               desc=f'Creating {image_config.LANGUAGE} stimuli images'):

        practice = True if row['text_type'] == 'practice' else False

        text_file_name = row[f"stimulus_name"]
        text_file_name = re.sub(' ', '_', text_file_name).lower()
        text_id = int(row[f"stimulus_id"])

        aoi_file_name = f'{text_file_name}_{text_id}_aoi.csv'
        aoi_header = ['char', 'x', 'y', 'width', 'height',
                      'char_idx_in_line', 'line_idx', 'page']
        aois = []
        all_words = []

        question_sub_df_stimulus = question_df[question_df['stimulus_id'] == text_id]

        for question_row_index, question_row in question_sub_df_stimulus.iterrows():

            question = question_row['question']
            question_id = question_row['question_id']

            answer_options = OrderedDict({'target': question_row['target'],
                                          'distractor_1': question_row['distractor_1'],
                                          'distractor_2': question_row['distractor_2'],
                                          'distractor_3': question_row['distractor_3']})

            new_col_name_path = f'question_{question_id}_stimulus_{text_id}_img_path'
            new_col_name_file = f'question_{question_id}_stimulus_{text_id}_img_file'

            if new_col_name_path not in question_images:
                question_images[new_col_name_path] = []

            if new_col_name_file not in question_images:
                question_images[new_col_name_file] = []

            annotated_text = question_row['text_annotated_spans']
            target_span_text = question_row['target_span_text']
            distractor_1_span_text = question_row['distractor_1_span_text']

            _get_distractor_spans(annotated_text, target_span_text, distractor_1_span_text)

            question_image = Image.new(
                'RGB', (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
                color=image_config.BACKGROUND_COLOR)

            arrow_img_path = 'logo_imgs/arrow_symbols.png'
            arrow_img = Image.open(arrow_img_path)

            # get size of arrow image and past it on the question image centralized
            arrow_width, arrow_height = arrow_img.size
            arrow_width, arrow_height = arrow_width // 3, arrow_height // 3
            arrow_img = arrow_img.resize((arrow_width, arrow_height))
            x_arrow = (image_config.IMAGE_WIDTH_PX - arrow_width) // 2
            y_arrow = image_config.IMAGE_HEIGHT_PX // 2

            question_image.paste(arrow_img, (x_arrow, y_arrow), mask=arrow_img)

            aois, all_words = draw_text(question, question_image, image_config.FONT_SIZE,
                                        spacing=image_config.SPACE_LINE, column_name=f'question_{question_id}',
                                        draw_aoi=image_config.AOI)

            distractor_positions = {
                'arrow_left': {
                    'x_px': image_config.MIN_MARGIN_LEFT_PX,
                    'y_px': image_config.IMAGE_HEIGHT_PX * 0.44,
                    'text_width_px': image_config.IMAGE_WIDTH_PX * 0.37,
                    'text_height_px': image_config.IMAGE_HEIGHT_PX * 0.28,
                },
                'arrow_up': {
                    'x_px': image_config.IMAGE_WIDTH_PX * 0.15,
                    'y_px': image_config.IMAGE_HEIGHT_PX * 0.25,
                    'text_width_px': image_config.IMAGE_WIDTH_PX * 0.7,
                    'text_height_px': image_config.IMAGE_HEIGHT_PX * 0.17,

                },
                'arrow_right': {
                    'x_px': image_config.IMAGE_WIDTH_PX * 0.57,
                    'y_px': image_config.IMAGE_HEIGHT_PX * 0.44,
                    'text_width_px': image_config.IMAGE_WIDTH_PX * 0.37,
                    'text_height_px': image_config.IMAGE_HEIGHT_PX * 0.28,
                },
                'arrow_down': {
                    'x_px': image_config.IMAGE_WIDTH_PX * 0.15,
                    'y_px': image_config.IMAGE_HEIGHT_PX * 0.75,
                    'text_width_px': image_config.IMAGE_WIDTH_PX * 0.7,
                    'text_height_px': image_config.IMAGE_HEIGHT_PX * 0.17,
                }
            }

            shuffled_distractor_keys = list(distractor_positions.keys())
            random.shuffle(shuffled_distractor_keys)

            for option, distractor in zip(answer_options, shuffled_distractor_keys):
                aois, all_words = draw_text(answer_options[option], question_image, image_config.FONT_SIZE,
                                            spacing=image_config.SPACE_LINE, column_name=f'question_{question_id}',
                                            draw_aoi=image_config.AOI,
                                            x_px=distractor_positions[distractor]['x_px'],
                                            y_px=distractor_positions[distractor]['y_px'],
                                            text_width_px=distractor_positions[distractor]['text_width_px'], )

                draw = ImageDraw.Draw(question_image)
                draw.rectangle(
                    (distractor_positions[distractor]['x_px'], distractor_positions[distractor]['y_px'],
                     distractor_positions[distractor]['x_px'] + distractor_positions[distractor]['text_width_px'],
                     distractor_positions[distractor]['y_px'] + distractor_positions[distractor]['text_height_px']),
                    outline='black', width=2
                )

            filename = f"{text_file_name}_id{text_id}_question_{question_id}_{image_config.LANGUAGE}" \
                       f"{'_practice' if practice else ''}{'_aoi' if image_config.AOI else ''}.png"

            img_path = question_aoi_dir if image_config.AOI else question_dir
            img_path = os.path.join(img_path, filename)
            question_image.save(img_path)

        for col_index, column_name in enumerate(initial_stimulus_df.columns):

            if column_name.startswith('page'):

                new_col_name_path = column_name + '_img_path'
                new_col_name_file = column_name + '_img_file'

                if new_col_name_path not in stimulus_images:
                    stimulus_images[new_col_name_path] = []

                if new_col_name_file not in stimulus_images:
                    stimulus_images[new_col_name_file] = []

                # if page for that text is empty
                if row[[column_name]].isnull().values.any():
                    stimulus_images[new_col_name_path].append(pd.NA)
                    stimulus_images[new_col_name_file].append(pd.NA)
                    continue

                text = str(initial_stimulus_df.iloc[row_index, col_index])

                # Create a new image with a previously defined color background and size
                final_image = Image.new(
                    'RGB', (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
                    color=image_config.BACKGROUND_COLOR)

                aois, all_words = draw_text(text, final_image, image_config.FONT_SIZE,
                                            spacing=image_config.SPACE_LINE, column_name=column_name,
                                            draw_aoi=image_config.AOI)

                filename = f"{text_file_name}_id{text_id}_{column_name}_{image_config.LANGUAGE}" \
                           f"{'_practice' if practice else ''}{'_aoi' if image_config.AOI else ''}.png"

                img_path = aoi_image_dir if image_config.AOI else image_dir
                img_path = os.path.join(img_path, filename)
                final_image.save(img_path)

                stimulus_images[new_col_name_path].append(img_path)
                stimulus_images[new_col_name_file].append(filename)

        aoi_df = pd.DataFrame(aois, columns=aoi_header)
        aoi_df['word'] = all_words
        # here changing sep back to ',' will prevent skipping an actual  ',' value
        aoi_df.to_csv(aoi_dir + aoi_file_name, sep=',', index=False, encoding='UTF-8')

    # Create a new csv file with the names of the pictures in the first column and their paths in the second
    image_df = pd.DataFrame(stimulus_images)
    final_stimulus_df = initial_stimulus_df.join(image_df)

    stimuli_file_name_stem = Path(stimuli_file_name).stem

    full_output_file_name = f'{stimuli_file_name_stem}{"_aoi" if image_config.AOI else ""}_with_img_paths.csv'

    full_path = os.path.join(image_config.OUTPUT_TOP_DIR, full_output_file_name)

    final_stimulus_df.to_csv(full_path,
                             sep=',',
                             index=False)


def _get_distractor_spans(text, target_span, distractor_span):
    pass


def create_stimuli_images():
    stimuli_file_name = image_config.OUTPUT_TOP_DIR + \
                        f'multipleye_stimuli_experiment_{image_config.LANGUAGE}.xlsx'

    create_images(stimuli_file_name, image_config.QUESTION_FILE_PATH, image_config.IMAGE_DIR,
                  image_config.QUESTION_IMAGE_DIR, image_config.AOI_DIR,
                  image_config.AOI_QUESTION_DIR, image_config.AOI_IMG_DIR)


def draw_text(text: str, image: Image, fontsize: int, draw_aoi: bool = False,
              spacing: int = image_config.SPACE_LINE, column_name: str = None,
              x_px: int = image_config.TOP_LEFT_CORNER_X_PX, y_px: int = image_config.TOP_LEFT_CORNER_Y_PX,
              text_width_px: int = image_config.TEXT_WIDTH_PX) -> (list, list):
    # Create a drawing object on the given image
    draw = ImageDraw.Draw(image)

    font = ImageFont.truetype(image_config.FONT_TYPE, fontsize)

    # TODO make sure this works for different scripts!
    paragraphs = re.split(r'\n+', text.strip())

    aois = []
    all_words = []
    line_idx = 0

    for paragraph in paragraphs:
        words_in_paragraph = paragraph.split()
        line = ""
        lines = []

        # create lines based on image margins
        for word in words_in_paragraph:
            left, top, right, bottom = draw.multiline_textbbox(
                (0, 0), line + word, font=font)
            text_width, text_height = right - left, bottom - top

            if text_width < text_width_px:
                line += word.strip() + " "
            else:
                lines.append(line.strip())
                lines.append(spacing * "\n")
                line = word + " "

        lines.append(line.strip())
        lines.append(spacing * "\n")

        for line in lines:
            if len(line) == 0:
                continue

            if line == spacing * "\n":
                y_px += image_config.FONT_SIZE * spacing
                continue

            words_in_line = line.split()
            x_word = x_px

            left, top, right, bottom = draw.multiline_textbbox((0, 0), line, font=font)
            line_width, line_height = right - left, bottom - top

            # calculate aoi boxes for each letter
            top_left_corner_x_letter = x_px
            letter_width = line_width / len(line)
            # TODO hardcode this factor somewhere else
            factor = line_height / 5.25
            words = []

            char_idx_in_line = 0

            stop_bold = False
            num_words = len(words_in_line)

            for word_number, word in enumerate(words_in_line):

                if word.startswith('**'):
                    font = ImageFont.truetype(image_config.FONT_TYPE_BOLD, fontsize)
                    word = word[2:]

                if word.endswith('**'):
                    stop_bold = True
                    word = word[:-2]

                # add a space if it is in the middle of a line
                if word_number < num_words - 1:
                    word = word + ' '

                word_left, word_top, word_right, word_bottom = draw.multiline_textbbox(
                    (0, 0), word, font=font)

                word_width = word_right - word_left

                draw.text((x_word, y_px), word, fill=image_config.TEXT_COLOR, font=font)

                for char_idx, char in enumerate(word):

                    if draw_aoi:
                        draw.rectangle((top_left_corner_x_letter, y_px,
                                        top_left_corner_x_letter + letter_width,
                                        y_px + 5.25 * (factor + 2)),
                                       outline='red', width=1)

                    # aoi_header = ['char', 'x', 'y', 'width', 'height', 'char_idx_in_line', 'line_idx', 'page']
                    # as the image is smaller than the actual screen we need to calculate the aoi boxes
                    aoi_x = top_left_corner_x_letter + ((image_config.RESOLUTION[0] - image_config.IMAGE_WIDTH_PX) // 2)
                    aoi_y = y_px + ((image_config.RESOLUTION[1] - image_config.IMAGE_HEIGHT_PX) // 2)

                    aoi_letter = [
                        char, aoi_x, aoi_y,
                        letter_width, line_height,
                        char_idx_in_line, line_idx, column_name
                    ]

                    # update top left corner x for next letter
                    top_left_corner_x_letter += letter_width

                    aois.append(aoi_letter)

                    char_idx_in_line += 1

                if word_number < num_words - 1:
                    words.extend([word.strip() for _ in range(len(word.strip()))] + [pd.NA])
                else:
                    words.extend([word.strip() for _ in range(len(word))])

                if stop_bold:
                    font = ImageFont.truetype(image_config.FONT_TYPE, fontsize)
                    stop_bold = False

                x_word += word_width

            all_words.extend(words)
            y_px += line_height
            line_idx += 1

    # draw fixation point
    r = 7
    fix_x = image_config.POS_BOTTOM_DOT_X_PX
    fix_y = image_config.POS_BOTTOM_DOT_Y_PX
    draw.ellipse(
        (fix_x - r, fix_y - r, fix_x + r, fix_y + r),
        fill=None,
        outline=image_config.TEXT_COLOR,
        width=5
    )

    return aois, all_words


def create_question_screens():
    pass


# # Extract the text data from the current cell, when it is question also add answers
# if column_name.startswith('question'):
#     # we need to extract order number of the question first
#     name_parts = column_name.split('_')
#     number_of_question = str(name_parts[-2] if practice else name_parts[-1])
#
#     if not practice:
#         answer_1 = str(
#             f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_1_key']}] "
#             + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_1'])
#         answer_2 = str(
#             f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_2_key']}] "
#             + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_2'])
#         answer_3 = str(
#             f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_3_key']}] "
#             + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_3'])
#     else:
#         answer_1 = str(
#             f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_1_key_practice']}] "
#             + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_1_practice'])
#         answer_2 = str(
#             f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_2_key_practice']}] "
#             + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_2_practice'])
#         answer_3 = str(
#             f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_3_key_practice']}] "
#             + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_3_practice'])
#
#     text_question = str(initial_df.iloc[row_index, col_index])
#     text_question = text_question.split()
#     text_question = ' '.join(text_question)
#     answers = "\n\n\n".join([answer_1, answer_2, answer_3])
#
#     # creation of the final text - question with answers
#     text = text_question + "\n\n\n" + answers
#
#     # Create a new image with a previously defined color background and size
#     final_image = Image.new(
#         'RGB', (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
#         color=image_config.BACKGROUND_COLOR)
#
#     # Create a drawing object
#     draw = ImageDraw.Draw(final_image)
#
#     # Draw the text on the image
#     font = ImageFont.truetype(image_config.FONT_TYPE, image_config.FONT_SIZE)
#
#     words = re.split(r' ', text)
#
#     line = ""
#     lines = []
#     for word in words:
#         left, top, right, bottom = draw.multiline_textbbox(
#             (0, 0), line + word, font=font)
#         text_width, text_height = right - left, bottom - top
#
#         if text_width < (image_config.IMAGE_WIDTH_PX - (
#                 image_config.MIN_MARGIN_RIGHT_PX + image_config.MIN_MARGIN_LEFT_PX)):
#             line += word + " "
#         else:
#             lines.append(line.strip())
#             lines.append("\n\n")
#             line = word + " "
#
#     lines.append(line.strip())
#
#     # we need this variable to have the original values in the next
#     # iteration, so we are creating a changing representation for the next iteration
#     top_left_corner_line = image_config.TOP_LEFT_CORNER_Y_PX
#
#     for line in lines:
#         left, top, right, bottom = draw.multiline_textbbox(
#             (0, 0), line, font=font)
#         text_width, text_height = right - left, bottom - top
#         draw.text((image_config.TOP_LEFT_CORNER_X_PX, top_left_corner_line),
#                   line, fill=image_config.TEXT_COLOR, font=font)
#         top_left_corner_line += text_height
#
#         # draw fixation point
#         r = 7
#         fix_x = image_config.POS_BOTTOM_DOT_X_PX
#         fix_y = image_config.POS_BOTTOM_DOT_Y_PX
#         draw.ellipse(
#             (fix_x - r, fix_y - r, fix_x + r, fix_y + r),
#             fill=None,
#             outline=image_config.TEXT_COLOR,
#             width=5
#         )
#
#     # Save the image as a PNG file; jpg has kind of worse quality, maybe we need to check what is the
#     # best
#     filename = (f"{text_file_name}_id{text_id}_{column_name}_{image_config.LANGUAGE}"
#                 f"{'_aoi' if draw_aoi else ''}.png")
#     final_image.save(image_dir + filename)
#
#     # store image names and paths
#     path = image_dir + filename
#     # maybe we can set path in the beginning as an object
#     stimulus_images[new_col_name_path].append(path)
#     stimulus_images[new_col_name_file].append(filename)

def create_welcome_screen(image: Image, text: str) -> None:
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
    our_blue = "#007baf"
    our_red = "#b94128"
    font_size = 38
    font_type = "fonts/open-sans-bold.ttf"

    # Create a drawing object
    draw = ImageDraw.Draw(image)

    # Create coordinates for three different logos
    multipleye_logo_x = (image.width - multipleye_logo.width) // 2
    multipleye_logo_y = 10
    multipleye_logo_position = (multipleye_logo_x, multipleye_logo_y)
    eu_logo_x = (image.width - eu_logo.width) // 6
    eu_logo_y = (image.height - eu_logo.height) - 18
    eu_logo_position = (eu_logo_x, eu_logo_y)
    cost_logo_x = ((image.width - eu_logo.width) // 6) + 580
    cost_logo_y = image.height - cost_logo.height
    cost_logo_position = (cost_logo_x, cost_logo_y)

    # Paste the logos onto the final image at the calculated coordinates
    image.paste(
        multipleye_logo, multipleye_logo_position, mask=multipleye_logo)
    image.paste(eu_logo, eu_logo_position, mask=eu_logo)
    image.paste(cost_logo, cost_logo_position)

    # Paste the text onto the final image
    font = ImageFont.truetype(font_type, font_size)
    left, top, right, bottom = draw.multiline_textbbox(
        (0, 0), text, font=font)
    text_width, text_height = right - left, bottom - top
    # text_width, text_height = draw.textsize(welcome_text, font=font)
    text_x = (image_config.IMAGE_WIDTH_PX - text_width) / 2
    text_y = (image_config.IMAGE_HEIGHT_PX - text_height) / 2
    draw.text((text_x, text_y), text, font=font, fill=our_blue)


def create_fixation_screen(image: Image):
    """
    Creates a fixation screen with a white background and a fixation dot in the top left corner.
    """
    # Create a drawing object
    draw = ImageDraw.Draw(image)

    # The fixation dot is positioned a bit left to the first char in the middle of the line
    r = 7
    fix_x = 0.75 * image_config.MIN_MARGIN_LEFT_PX
    fix_y = 1.25 * image_config.MIN_MARGIN_TOP_PX
    draw.ellipse(
        (fix_x - r, fix_y - r, fix_x + r, fix_y + r),
        fill=None,
        outline=image_config.TEXT_COLOR,
        width=5
    )


def create_final_screen(image: Image, text: str):
    """
    Creates a final screen with a white background, one logo and a blue messages in the middle of the screen.
    """
    multipleye_logo = Image.open("logo_imgs/logo_multipleye.png")

    final_text = text.split('\n')

    our_blue = "#007baf"
    our_red = "#b94128"
    font_size = 38
    font_type = "fonts/open-sans-bold.ttf"

    # Create a drawing object
    draw = ImageDraw.Draw(image)

    # Create coordinates for three different logos
    multipleye_logo_x = (image.width - multipleye_logo.width) // 2
    multipleye_logo_y = 10
    multipleye_logo_position = (multipleye_logo_x, multipleye_logo_y)

    # Paste the logos onto the final image at the calculated coordinates
    image.paste(
        multipleye_logo, multipleye_logo_position, mask=multipleye_logo)
    # final_image.paste(eu_logo, eu_logo_position, mask = eu_logo)
    # final_image.paste(cost_logo, cost_logo_position)

    # Paste the texts onto the final image
    font = ImageFont.truetype(font_type, font_size)
    text_y = 0
    text_x = 0
    for paragraph in final_text:
        left, top, right, bottom = draw.multiline_textbbox(
            (0, 0), paragraph, font=font)
        text_width, text_height = right - left, bottom - top
        if not text_x:
            text_x = (image_config.IMAGE_WIDTH_PX - text_width) // 2
            text_y = (image_config.IMAGE_HEIGHT_PX - text_height) // 2
        else:
            text_x = (image_config.IMAGE_WIDTH_PX - text_width) // 2
            text_y += text_width

        draw.text((text_x, text_y), paragraph, font=font, fill=our_blue)


def create_other_screens():
    other_screen_df = pd.read_excel(image_config.OTHER_SCREENS_FILE_PATH)
    other_screen_df.dropna(subset=['instruction_screen_id'], inplace=True)

    if not os.path.isdir(image_config.OTHER_SCREENS_DIR):
        os.mkdir(image_config.OTHER_SCREENS_DIR)

    file_names = []
    file_paths = []

    for idx, row in tqdm(other_screen_df.iterrows(),
                         desc=f'Creating other screens {image_config.LANGUAGE}:',
                         total=len(other_screen_df)):

        final_image = Image.new(
            'RGB', (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX), color=image_config.BACKGROUND_COLOR)

        title = row["instruction_screen_name"]
        text = row["instruction_screen_text"]

        if title == "welcome_screen":
            create_welcome_screen(final_image, text)

        elif title == "fixation_screen":
            create_fixation_screen(final_image)

        elif title == "final_screen":
            create_final_screen(final_image, text)

        elif title != 'empty_screen':
            draw_text(text, final_image, image_config.FONT_SIZE - 2, spacing=2, draw_aoi=False)

        file_name = f'{title}_{image_config.LANGUAGE}.png'
        file_path = image_config.OTHER_SCREENS_DIR + file_name
        file_names.append(file_name)
        file_paths.append(file_path)

        final_image.save(image_config.OTHER_SCREENS_DIR + file_name)

    other_screen_df['other_screen_img_name'] = file_names
    other_screen_df['other_screen_img_path'] = file_paths

    other_screen_df.to_csv(image_config.OTHER_SCREENS_FILE_PATH[:-5]
                           + f'{"_aoi" if image_config.AOI else ""}_with_img_paths.csv',
                           index=False)


if __name__ == '__main__':
    create_stimuli_images()
    create_other_screens()
