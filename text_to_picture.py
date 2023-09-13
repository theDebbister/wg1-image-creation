import csv
import os
import re
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from screeninfo import get_monitors
from tqdm import tqdm

import image_config


def create_images(stimuli_file_name, image_dir, aoi_dir, aoi_image_dir, practice=False):
    # Read the TSV file
    num = image_config.NUM_STIMULI if not practice else image_config.NUM_PRACTICE_STIMULI
    initial_df = pd.read_excel(stimuli_file_name, nrows=num)

    if not os.path.isdir(image_dir):
        os.mkdir(image_dir)

    if not os.path.isdir(aoi_dir):
        os.mkdir(aoi_dir)

    if not os.path.isdir(aoi_image_dir):
        os.mkdir(aoi_image_dir)

    stimulus_images = {}
    draw_aoi = False

    for row_index, row in tqdm(initial_df.iterrows(), total=len(initial_df),
                               desc=f'Creating {image_config.LANGUAGE} images'):
        text_file_name = row[f"stimulus_text_title{'_practice' if practice else ''}"]
        text_file_name = re.sub(' ', '_', text_file_name).lower()
        text_id = int(row[f"stimulus_id{'_practice' if practice else ''}"])

        aoi_file_name = f'{text_file_name}_{text_id}_aoi.csv'
        aoi_header = ['char', 'x', 'y', 'width', 'height',
                      'char_idx_in_line', 'line_idx', 'page']
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
                    number_of_question = str(name_parts[-2] if practice else name_parts[-1])

                    # we need to extract answers and add them to strings
                    # answer_1 = str(f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_1_key' + '_practice' if practice else '']}] "
                    #                + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_1' + '_practice' if practice else ''])
                    # answer_2 = str(f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_2_key' + '_practice' if practice else '']}] "
                    #                + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_2' + '_practice' if practice else ''])
                    # answer_3 = str(f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_3_key' + '_practice' if practice else '']}] "
                    #                + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_3' + '_practice' if practice else ''])
                    if not practice:
                        answer_1 = str(
                            f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_1_key']}] "
                            + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_1'])
                        answer_2 = str(
                            f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_2_key']}] "
                            + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_2'])
                        answer_3 = str(
                            f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_3_key']}] "
                            + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_3'])
                    else:
                        answer_1 = str(
                            f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_1_key_practice']}] "
                            + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_1_practice'])
                        answer_2 = str(
                            f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_2_key_practice']}] "
                            + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_2_practice'])
                        answer_3 = str(
                            f"[{initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_3_key_practice']}] "
                            + initial_df.loc[row_index, 'answer_option_q' + number_of_question + '_3_practice'])

                    text_question = str(initial_df.iloc[row_index, col_index])
                    text_question = text_question.split()
                    text_question = ' '.join(text_question)
                    answers = "\n\n\n".join([answer_1, answer_2, answer_3])

                    # creation of the final text - question with answers
                    text = text_question + "\n\n\n" + answers

                    # Create a new image with a previously defined color background and size
                    final_image = Image.new(
                        'RGB', (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
                        color=image_config.BACKGROUND_COLOR)

                    # Create a drawing object
                    draw = ImageDraw.Draw(final_image)

                    # Draw the text on the image
                    font = ImageFont.truetype(image_config.FONT_TYPE, image_config.FONT_SIZE)

                    # make sure it works for different scripts we need to use re.split (otherwise we will lose "\n"
                    # separating lines between question and answers), but next part of the code is then not properly
                    # working for a sentences that are longer than one row, I do not know why, we need to address it
                    # later <- addressed by splitting at white space only and preserved "\n"
                    # words = re.split(r'(\n)', text)
                    words = re.split(r' ', text)

                    line = ""
                    lines = []
                    for word in words:
                        left, top, right, bottom = draw.multiline_textbbox(
                            (0, 0), line + word, font=font)
                        text_width, text_height = right - left, bottom - top

                        if text_width < (image_config.IMAGE_WIDTH_PX - (
                                image_config.MIN_MARGIN_RIGHT_PX + image_config.MIN_MARGIN_LEFT_PX)):
                            line += word + " "
                        else:
                            lines.append(line.strip())
                            lines.append("\n\n")
                            line = word + " "

                    lines.append(line.strip())

                    # we need this variable to have the original values in the next
                    # iteration, so we are creating a changing representation for the next iteration
                    top_left_corner_line = image_config.TOP_LEFT_CORNER_Y_PX

                    for line in lines:
                        left, top, right, bottom = draw.multiline_textbbox(
                            (0, 0), line, font=font)
                        text_width, text_height = right - left, bottom - top
                        draw.text((image_config.TOP_LEFT_CORNER_X_PX, top_left_corner_line),
                                  line, fill=image_config.TEXT_COLOR, font=font)
                        top_left_corner_line += text_height

                        # draw fixation point
                        r = 7
                        fix_x = image_config.IMAGE_WIDTH_PX - 0.75 * image_config.MIN_MARGIN_LEFT_PX
                        fix_y = image_config.IMAGE_HEIGHT_PX - 1.25 * image_config.MIN_MARGIN_TOP_PX
                        draw.ellipse(
                            (fix_x - r, fix_y - r, fix_x + r, fix_y + r),
                            fill=None,
                            outline=image_config.TEXT_COLOR,
                            width=5
                        )

                    # Save the image as a PNG file; jpg has kind of worse quality, maybe we need to check what is the
                    # best
                    filename = f"{text_file_name}_id{text_id}_{column_name}_{image_config.LANGUAGE}.png"
                    final_image.save(image_dir + filename)

                    # store image names and paths
                    path = image_dir + filename
                    # maybe we can set path in the beginning as an object
                    stimulus_images[new_col_name_path].append(path)
                    stimulus_images[new_col_name_file].append(filename)

                # if it is not a question but a reading text
                else:
                    text = str(initial_df.iloc[row_index, col_index])

                    # Create a new image with a previously defined color background and size
                    final_image = Image.new(
                        'RGB', (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
                        color=image_config.BACKGROUND_COLOR)

                    # Create a drawing object
                    draw = ImageDraw.Draw(final_image)

                    # Draw the text on the image
                    font = ImageFont.truetype(image_config.FONT_TYPE, image_config.FONT_SIZE)

                    # make sure this works for different scripts!
                    paragraphs = re.split(r'\n+', text.strip())

                    # we need this variable to have the original values in the next
                    top_left_corner_y_line = image_config.TOP_LEFT_CORNER_Y_PX

                    for paragraph in paragraphs:
                        words = paragraph.split()
                        line = ""
                        lines = []
                        for word in words:
                            left, top, right, bottom = draw.multiline_textbbox(
                                (0, 0), line + word, font=font)
                            text_width, text_height = right - left, bottom - top

                            if text_width < (image_config.IMAGE_WIDTH_PX - (
                                    image_config.MIN_MARGIN_RIGHT_PX + image_config.MIN_MARGIN_LEFT_PX)):
                                line += word.strip() + " "
                            else:
                                lines.append(line.strip())
                                lines.append(image_config.SPACE_LINE * "\n")
                                line = word + " "

                        lines.append(line.strip())
                        lines.append(image_config.SPACE_LINE * "\n")

                        for line_idx, line in enumerate(lines):
                            if len(line) == 0:
                                continue
                            left, top, right, bottom = draw.multiline_textbbox(
                                (0, 0), line, font=font)
                            text_width, text_height = right - left, bottom - top

                            draw.text(
                                (image_config.TOP_LEFT_CORNER_X_PX, top_left_corner_y_line), line,
                                fill=image_config.TEXT_COLOR, font=font)

                            # calculate aoi boxes for each letter
                            top_left_corner_x_letter = image_config.TOP_LEFT_CORNER_X_PX
                            letter_width = text_width / len(line)
                            factor = text_height / 5.25
                            words = []
                            word = ''

                            for char_idx_in_line, letter in enumerate(line):
                                if line == image_config.SPACE_LINE * "\n":
                                    continue
                                if letter == ' ':
                                    # add the word once for each char
                                    words.extend(
                                        [word for _ in range(len(word))] + [pd.NA])
                                    word = ''
                                else:
                                    word += letter

                                if image_config.AOI:
                                    draw.rectangle((top_left_corner_x_letter, top_left_corner_y_line,
                                                    top_left_corner_x_letter + letter_width,
                                                    top_left_corner_y_line + 5.25 * (factor + 2)),
                                                   outline='red', width=1)
                                    draw_aoi = True

                                # aoi_header = ['char', 'x', 'y', 'width', 'height', 'word', 'line', 'page']

                                # as the image is smaller than the actual screen we need to calculate
                                aoi_letter = [
                                    letter,
                                    top_left_corner_x_letter +
                                    ((image_config.RESOLUTION[0] - image_config.IMAGE_WIDTH_PX) // 2),
                                    top_left_corner_y_line +
                                    ((image_config.RESOLUTION[1] -
                                      image_config.IMAGE_HEIGHT_PX) // 2),
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
                            top_left_corner_y_line += text_height

                    # draw fixation point
                    r = 7
                    fix_x = image_config.IMAGE_WIDTH_PX - image_config.MIN_MARGIN_LEFT_PX * 1.5
                    fix_y = image_config.IMAGE_HEIGHT_PX - image_config.MIN_MARGIN_TOP_PX * 0.5
                    draw.ellipse(
                        (fix_x - r, fix_y - r, fix_x + r, fix_y + r),
                        fill=None,
                        outline=image_config.TEXT_COLOR,
                        width=5
                    )

                    filename = f"{text_file_name}_id{text_id}_{column_name}_{image_config.LANGUAGE}" \
                               f"{'_aoi' if draw_aoi else ''}.png"

                    img_path = aoi_image_dir if draw_aoi else image_dir
                    img_path = os.path.join(img_path, filename)
                    final_image.save(img_path)

                    stimulus_images[new_col_name_path].append(img_path)
                    stimulus_images[new_col_name_file].append(filename)

        aoi_df = pd.DataFrame(aois, columns=aoi_header)
        aoi_df['word'] = all_words
        # here changing sep back to ',' will prevent skipping an actual  ',' value
        aoi_df.to_csv(aoi_dir + aoi_file_name, sep=',',
                      index=False, encoding='UTF-8')

    # Create a new csv file with the names of the pictures in the first column and their paths in the second
    image_df = pd.DataFrame(stimulus_images)
    final_df = initial_df.join(image_df)

    stimuli_file_name_stem = Path(stimuli_file_name).stem

    full_output_file_name = f'{stimuli_file_name_stem}_with_img_paths.csv'

    full_path = os.path.join(image_config.OUTPUT_TOP_DIR, full_output_file_name)

    final_df.to_csv(full_path,
                    sep=',',
                    index=False)


def create_stimuli_images():
    stimuli_file_name = image_config.OUTPUT_TOP_DIR + \
                        f'multipleye-stimuli-experiment-{image_config.LANGUAGE}.xlsx'
    image_config.IMAGE_DIR = image_config.IMAGE_DIR
    image_config.AOI_DIR = image_config.AOI_DIR
    image_config.AOI_IMG_DIR = image_config.AOI_IMG_DIR
    create_images(stimuli_file_name, image_config.IMAGE_DIR, image_config.AOI_DIR,
                  image_config.AOI_IMG_DIR)


def create_practice_images():
    stimuli_file_name = image_config.OUTPUT_TOP_DIR + \
                        f'multipleye-stimuli-practice-{image_config.LANGUAGE}.xlsx'
    image_config.IMAGE_DIR = image_config.PRACTICE_IMAGE_DIR
    image_config.AOI_DIR = image_config.PRACTICE_AOI_DIR
    image_config.AOI_IMG_DIR = image_config.PRACTICE_AOI_IMG_DIR
    create_images(stimuli_file_name, image_config.IMAGE_DIR, image_config.AOI_DIR,
                  image_config.AOI_IMG_DIR, practice=True)


def draw_text(text, image):
    draw = ImageDraw.Draw(image)

    # font size is a bit smaller for these texts
    font_size = image_config.FONT_SIZE -2
    font = ImageFont.truetype(image_config.FONT_TYPE, font_size)
    paragraphs = re.split(r'\n', text.strip())

    top_left_corner_y_line = image_config.TOP_LEFT_CORNER_Y_PX

    for paragraph in paragraphs:
        words = paragraph.split()
        line = ""
        lines = []

        for word in words:
            left, top, right, bottom = draw.multiline_textbbox(
                (0, 0), line + word, font=font)
            text_width = right - left

            if text_width < (
                    image_config.IMAGE_WIDTH_PX - (image_config.MIN_MARGIN_RIGHT_PX + image_config.MIN_MARGIN_LEFT_PX)):
                line += word.strip() + " "
            else:
                lines.append(line.strip())
                lines.append("\n")
                line = word + " "

        lines.append(line.strip())
        lines.append("\n")

        for line in lines:
            if len(line) == 0:
                continue

            words_in_line = line.split()
            x_word = image_config.TOP_LEFT_CORNER_X_PX

            left, top, right, bottom = draw.multiline_textbbox(
                (0, 0), line + '  ', font=font)
            text_height = bottom - top

            stop_bold = False
            for w in words_in_line:

                if w.startswith('**'):
                    font = ImageFont.truetype(image_config.FONT_TYPE_BOLD, font_size)
                    w = w[2:]

                if w.endswith('**'):
                    stop_bold = True
                    w = w[:-2]

                left, top, right, bottom = draw.multiline_textbbox(
                    (0, 0), w + ' ', font=font)
                draw.text(
                    (x_word, top_left_corner_y_line), w, fill=image_config.TEXT_COLOR, font=font)
                x_word += right - left

                if stop_bold:
                    font = ImageFont.truetype(image_config.FONT_TYPE, font_size)
                    stop_bold = False

            top_left_corner_y_line += text_height

            # r = 7
            # fix_x = image_config.IMAGE_WIDTH_PX - 0.75 * image_config.MIN_MARGIN_LEFT_PX
            # fix_y = image_config.IMAGE_HEIGHT_PX - 1.25 * image_config.MIN_MARGIN_TOP_PX
            # draw.ellipse(
            #     (fix_x - r, fix_y - r, fix_x + r, fix_y + r),
            #     fill=None,
            #     outline=image_config.TEXT_COLOR,
            #     width=5
            # )


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
    # We have one multipleye logo - we can load other if needed
    # cost_logo = Image.open("cost_logo.jpg")
    # cost_width, cost_height = cost_logo.size
    # cost_logo_new_size = (cost_width // 7, cost_height // 7)
    # cost_logo = cost_logo.resize(cost_logo_new_size)
    # eu_logo = Image.open("eu_fund_logo.png")
    # eu_width, eu_height = eu_logo.size
    # eu_logo_new_size = (eu_width // 7, eu_height // 7)
    # eu_logo = eu_logo.resize(eu_logo_new_size)
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
    # eu_logo_x = (final_image.width - eu_logo.width) // 6
    # eu_logo_y = (final_image.height - eu_logo.height) - 18
    # eu_logo_position = (eu_logo_x, eu_logo_y)
    # cost_logo_x = ((final_image.width - eu_logo.width) // 6)  + 580
    # cost_logo_y = final_image.height - cost_logo.height
    # cost_logo_position = (cost_logo_x, cost_logo_y)

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
    other_screen_df = pd.read_excel(image_config.OTHER_SCREENS_FILE_PATH, nrows=image_config.NUM_OTHER_SCREENS)

    if not os.path.isdir(image_config.OTHER_SCREENS_DIR):
        os.mkdir(image_config.OTHER_SCREENS_DIR)

    file_names = []
    file_paths = []

    for idx, row in tqdm(other_screen_df.iterrows(),
                         desc=f'Creating other screens {image_config.LANGUAGE}:',
                         total=len(other_screen_df)):

        final_image = Image.new(
            'RGB', (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX), color=image_config.BACKGROUND_COLOR)

        title = row["other_screen_title"]
        text = row["other_screen_text"]

        if title == "welcome_screen":
            create_welcome_screen(final_image, text)

        elif title == "fixation_screen":
            create_fixation_screen(final_image)

        elif title == "final_screen":
            create_final_screen(final_image, text)

        elif title != 'empty_screen':
            draw_text(text, final_image)

        file_name = f'{title}_{image_config.LANGUAGE}.png'
        file_path = image_config.OTHER_SCREENS_DIR + file_name
        file_names.append(file_name)
        file_paths.append(file_path)

        final_image.save(image_config.OTHER_SCREENS_DIR + file_name)

    other_screen_df['other_screen_img_name'] = file_names
    other_screen_df['other_screen_img_path'] = file_paths

    other_screen_df.to_csv(image_config.OTHER_SCREENS_FILE_PATH[:-5] + '_with_img_paths.csv', index=False)


if __name__ == '__main__':
    create_stimuli_images()
    create_practice_images()
    create_other_screens()
