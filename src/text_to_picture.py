from __future__ import annotations

import json
import os
import random
import warnings
import re
from collections import OrderedDict
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm

import image_config
from utils import config_utils, checks

pd.options.mode.chained_assignment = None  # default='warn'

CONFIG = {}


def create_images(
        stimuli_csv_file_name: str,
        question_csv_file_name: str,
        image_dir: str = image_config.IMAGE_DIR,
        question_dir: str = image_config.QUESTION_IMAGE_DIR,
        aoi_dir: str = image_config.AOI_DIR,
        question_aoi_dir: str = image_config.AOI_QUESTION_DIR,
        aoi_image_dir: str = image_config.AOI_IMG_DIR,
        draw_aoi=False,
):
    initial_stimulus_df = pd.read_excel(stimuli_csv_file_name)
    # initial_stimulus_df = pd.read_csv(stimuli_csv_file_name, sep=',', encoding='utf-8')
    initial_stimulus_df.dropna(subset=['stimulus_id'], inplace=True)

    stimulus_types = initial_stimulus_df['stimulus_type'].unique()
    checks.check_stimulus_types(stimulus_types)

    # check whether question excel exists as file, stimuli can be created independent of questions
    if os.path.isfile(question_csv_file_name):
        initial_question_df = pd.read_excel(question_csv_file_name)
        initial_question_df.dropna(subset=['stimulus_id'], inplace=True)

        stimulus_types = initial_question_df['stimulus_type'].unique()
        checks.check_stimulus_types(stimulus_types)

        cols = initial_question_df.columns.to_list().extend(
            ['question_img_path', 'question_img_file', 'target_key', 'distractor_a_key', 'distractor_b_key',
             'distractor_c_key']
        )
        new_question_df = pd.DataFrame(columns=cols)
    else:
        question_csv_file_name = None

    block_config = pd.read_csv(image_config.REPO_ROOT / image_config.BLOCK_CONFIG_PATH, sep=',', encoding='UTF-8')

    image_dir_with_root = image_config.REPO_ROOT / image_dir
    aoi_dir_with_root = image_config.REPO_ROOT / aoi_dir
    aoi_image_dir_with_root = image_config.REPO_ROOT / aoi_image_dir
    question_dir_with_root = image_config.REPO_ROOT / question_dir
    question_aoi_dir_with_root = image_config.REPO_ROOT / question_aoi_dir

    if not os.path.isdir(image_dir_with_root):
        os.mkdir(image_dir_with_root)

    if not os.path.isdir(aoi_dir_with_root):
        os.mkdir(aoi_dir_with_root)

    if not os.path.isdir(aoi_image_dir_with_root):
        os.mkdir(aoi_image_dir_with_root)

    if not os.path.isdir(question_dir_with_root):
        os.mkdir(question_dir_with_root)

    if not os.path.isdir(question_aoi_dir_with_root):
        os.mkdir(question_aoi_dir_with_root)

    stimulus_images = {}

    for row_index, row in (pbar := tqdm(initial_stimulus_df.iterrows(), total=len(initial_stimulus_df))):
        stimulus_name = row[f"stimulus_name"]
        stimulus_id = int(row[f"stimulus_id"])
        pbar.set_description(
            f'Creating {image_config.LANGUAGE}{" aoi" if draw_aoi else ""} stimuli images for {stimulus_id}'
            f' {stimulus_name}'
        )

        # check whether stimulus id and name exist
        try:
            block_config[((block_config['stimulus_id'] == stimulus_id)
                          & (block_config['stimulus_name'] == stimulus_name))]
        except IndexError:
            raise ValueError(
                f'Something is wrong with the stimulus id and name of : {stimulus_id} {stimulus_name}. '
                f'Please check it is the same as in the English files.'
            )
        stimulus_name = re.sub(' ', '_', stimulus_name)

        aoi_file_name = f'{stimulus_name.lower()}_{stimulus_id}_aoi.csv'
        aoi_header = ['char_idx', 'char', 'top_left_x', 'top_left_y', 'width', 'height',
                      'char_idx_in_line', 'line_idx', 'page', 'word_idx', 'word_idx_in_line']
        all_aois = []
        all_words = []
        question_image_versions = []

        # check whether question excel exists
        if question_csv_file_name:

            # get all questions for that text
            question_sub_df_stimulus = initial_question_df.loc[(initial_question_df['stimulus_id'] == stimulus_id) &
                                                               (initial_question_df['stimulus_name'] == stimulus_name)]
            if len(question_sub_df_stimulus) == 0:
                warnings.warn(f'No questions found for {stimulus_name} {stimulus_id}')

            for i in range(image_config.VERSION_START, image_config.NUM_PERMUTATIONS + image_config.VERSION_START):

                # the answer options are shuffeled for each participant (each gets a new item version)
                session_id = 'question_images_version_' + str(i)

                question_csv_filename_stem = Path(question_csv_file_name).stem
                new_session_question_df_name = (f'{question_csv_filename_stem}{"_aoi" if draw_aoi else ""}_'
                                                f'{session_id}_with_img_paths.csv')
                full_path_root_question_df = os.path.join(
                    question_dir_with_root if not draw_aoi else question_aoi_dir_with_root,
                    session_id,
                    new_session_question_df_name
                )

                full_path_question_df = os.path.join(
                    question_dir if not draw_aoi else question_aoi_dir,
                    session_id,
                    new_session_question_df_name
                )

                # if there already is a file and we did not start a new image creation, we open the existing file
                if os.path.isfile(full_path_root_question_df) and not row_index == 0:
                    new_session_question_df = pd.read_csv(full_path_root_question_df)

                else:
                    new_session_question_df = new_question_df

                shuffeled_answer_options_path = os.path.join(
                    image_config.ANSWER_OPTION_FOLDER +
                    f'shuffled_option_keys_{image_config.LANGUAGE}_{session_id}.json'
                )
                # if we have already once shuffeled some of the options for this item, we open the existing file
                if os.path.isfile(image_config.REPO_ROOT / shuffeled_answer_options_path):
                    with open(image_config.REPO_ROOT / shuffeled_answer_options_path, 'r') as f:
                        shuffled_option_dict = json.load(f)
                else:
                    shuffled_option_dict = {}

                question_sub_csv_copy = question_sub_df_stimulus.copy()

                temp_paths = []
                temp_files_names = []
                temp_target_keys = []
                temp_distractor_a_keys = []
                temp_distractor_b_keys = []
                temp_distractor_c_keys = []
                for question_row_index, question_row in question_sub_df_stimulus.iterrows():

                    question = question_row['question']
                    snippet_no = question_row['snippet_no']
                    condition_no = question_row['condition_no']
                    question_no = question_row['question_no']
                    question_id = str(stimulus_id) + str(snippet_no) + str(condition_no) + str(question_no)
                    # item_id = question_row['item_id']

                    question_identifier = f'question_{question_id}_stimulus_{stimulus_id}'

                    answer_options = OrderedDict(
                        {'target': question_row['target'],
                         'distractor_a': question_row['distractor_a'],
                         'distractor_b': question_row['distractor_b'],
                         'distractor_c': question_row['distractor_c']}
                    )

                    annotated_text = question_row['stimulus_text_with_annotated_spans']
                    target_span_text = question_row['target_span_target_distractor_a_text']
                    distractor_1_span_text = question_row['distractor_span_distractor_b_text']

                    get_option_span_indices(annotated_text, target_span_text, distractor_1_span_text)

                    question_image = Image.new(
                        'RGB', (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
                        color=image_config.BACKGROUND_COLOR
                    )

                    aois, words = draw_text(
                        question, question_image, image_config.FONT_SIZE_PX,
                        spacing=image_config.LINE_SPACING,
                        image_short_name=f'question_{question_id}',
                        draw_aoi=draw_aoi, line_limit=2,
                        word_split_criterion=image_config.WORD_SPLIT_CRITERION,
                    )

                    all_aois.extend(aois)
                    all_words.extend(words)
                    question_image_versions.extend([session_id for _ in range(len(aois))])

                    option_keys = {
                        'left': {
                            'x_px': image_config.MIN_MARGIN_LEFT_PX,
                            'y_px': image_config.IMAGE_HEIGHT_PX * 0.44,
                            'text_width_px': image_config.IMAGE_WIDTH_PX * 0.41,
                            'text_height_px': image_config.IMAGE_HEIGHT_PX * 0.28,
                        },
                        'up': {
                            'x_px': image_config.IMAGE_WIDTH_PX * 0.15,
                            'y_px': image_config.IMAGE_HEIGHT_PX * 0.25,
                            'text_width_px': image_config.IMAGE_WIDTH_PX * 0.7,
                            'text_height_px': image_config.IMAGE_HEIGHT_PX * 0.17,

                        },
                        'right': {
                            'x_px': image_config.IMAGE_WIDTH_PX * 0.53,
                            'y_px': image_config.IMAGE_HEIGHT_PX * 0.44,
                            'text_width_px': image_config.IMAGE_WIDTH_PX * 0.41,
                            'text_height_px': image_config.IMAGE_HEIGHT_PX * 0.28,
                        },
                        'down': {
                            'x_px': image_config.IMAGE_WIDTH_PX * 0.15,
                            'y_px': image_config.IMAGE_HEIGHT_PX * 0.75,
                            'text_width_px': image_config.IMAGE_WIDTH_PX * 0.7,
                            'text_height_px': image_config.IMAGE_HEIGHT_PX * 0.17,
                        }
                    }

                    # if we already have the shuffled options file for this item version, but we have not yet
                    # shuffled the options for this question
                    if question_identifier not in shuffled_option_dict:
                        # TESTING ANSWER OPTION LENGTH: refer to README.md
                        shuffled_option_keys = ['left', 'up', 'right', 'down']
                        # shuffled_option_keys = ['up', 'left', 'down', 'right']
                        random.shuffle(shuffled_option_keys)
                        shuffled_option_keys = {k: v for k, v in zip(answer_options, shuffled_option_keys)}
                        shuffled_option_dict[question_identifier] = shuffled_option_keys

                    else:
                        shuffled_option_keys = shuffled_option_dict[question_identifier]

                    temp_target_keys.append(shuffled_option_keys['target'])
                    temp_distractor_a_keys.append(shuffled_option_keys['distractor_a'])
                    temp_distractor_b_keys.append(shuffled_option_keys['distractor_b'])
                    temp_distractor_c_keys.append(shuffled_option_keys['distractor_c'])

                    for option, distractor_key in shuffled_option_keys.items():
                        aois, words = draw_text(
                            answer_options[option], question_image, image_config.FONT_SIZE_PX,
                            spacing=image_config.LINE_SPACING,
                            image_short_name=f'{stimulus_name}_{stimulus_id}_question_{question_id}_{option}',
                            draw_aoi=draw_aoi,
                            anchor_x_px=option_keys[distractor_key]['x_px'],
                            anchor_y_px=option_keys[distractor_key]['y_px'],
                            text_width_px=option_keys[distractor_key]['text_width_px'],
                            question_option_type=distractor_key,
                            word_split_criterion=image_config.WORD_SPLIT_CRITERION,
                        )

                        draw = ImageDraw.Draw(question_image)

                        # draw a box around the answer options: x, y, x + width, y + height, x must be a bit smaller
                        # otherwise it is too close to the letters
                        new_x = option_keys[distractor_key]['x_px'] - image_config.MIN_MARGIN_LEFT_PX * 0.1
                        new_width = option_keys[distractor_key]['text_width_px'] + image_config.MIN_MARGIN_LEFT_PX * 0.1
                        box_coordinates = (
                            new_x,
                            option_keys[distractor_key]['y_px'],
                            new_x + new_width,
                            option_keys[distractor_key]['y_px'] + option_keys[distractor_key][
                                'text_height_px'])

                        draw.rectangle(box_coordinates, outline='black', width=1)

                        CONFIG.setdefault('QUESTION_OPTION_BOXES', {}).update({distractor_key: box_coordinates})

                        all_aois.extend(aois)
                        all_words.extend(words)
                        question_image_versions.extend([session_id for _ in range(len(aois))])

                    question_image_file = f"{stimulus_name}_id{stimulus_id}_question_{question_id}_{image_config.LANGUAGE}" \
                                          f"{'_aoi' if draw_aoi else ''}.png"
                    question_image_path_root = question_aoi_dir_with_root if draw_aoi else question_dir_with_root

                    if not os.path.isdir(os.path.join(question_image_path_root, session_id)):
                        os.mkdir(os.path.join(question_image_path_root, session_id))

                    question_image.save(question_image_path_root / session_id / question_image_file)

                    question_image_path = question_aoi_dir if draw_aoi else question_dir
                    question_image_path = Path(question_image_path) / session_id / question_image_file
                    question_image_path = str(question_image_path).replace('\\', '/')

                    temp_paths.append(question_image_path)
                    temp_files_names.append(question_image_file)

                question_sub_csv_copy.loc[
                    question_sub_df_stimulus['stimulus_id'] == stimulus_id, 'question_img_path'] = temp_paths
                question_sub_csv_copy['question_img_file'] = temp_files_names
                question_sub_csv_copy['target_key'] = temp_target_keys
                question_sub_csv_copy['distractor_a_key'] = temp_distractor_a_keys
                question_sub_csv_copy['distractor_b_key'] = temp_distractor_b_keys
                question_sub_csv_copy['distractor_c_key'] = temp_distractor_c_keys
                new_session_question_df = pd.concat([new_session_question_df, question_sub_csv_copy], axis=0)

                new_session_question_df.to_csv(
                    full_path_root_question_df,
                    sep=',',
                    index=False
                )
                # save relative path without root
                CONFIG.setdefault('QUESTION_CSV_PATHS', {}).update(
                    {
                        f'question_images_{session_id}{"_aoi" if draw_aoi else ""}_csv': full_path_question_df
                    }
                )

                output_file = Path(image_config.REPO_ROOT / shuffeled_answer_options_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)

                with open(image_config.REPO_ROOT / shuffeled_answer_options_path, 'w', encoding='utf8') as f:
                    json.dump(shuffled_option_dict, f, indent=4)

        empty_page = False
        empty_page_inbetween = False
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
                    empty_page = True
                    continue

                if empty_page:
                    empty_page_inbetween = True
                    empty_page = False

                text = str(initial_stimulus_df.iloc[row_index, col_index])

                # Create a new image with a previously defined color background and size
                final_image = Image.new(
                    'RGB', (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX),
                    color=image_config.BACKGROUND_COLOR
                )

                aois, words = draw_text(
                    text, final_image, image_config.FONT_SIZE_PX,
                    spacing=image_config.LINE_SPACING, image_short_name=column_name,
                    draw_aoi=draw_aoi,
                    word_split_criterion=image_config.WORD_SPLIT_CRITERION,
                )

                filename = f"{stimulus_name.lower()}_id{stimulus_id}_{column_name}_{image_config.LANGUAGE}" \
                           f"{'_aoi' if draw_aoi else ''}.png"

                # save the image to paht with root, but save the path without only rela tive to the data folder
                img_path_root = aoi_image_dir_with_root if draw_aoi else image_dir_with_root
                img_path = aoi_image_dir if draw_aoi else image_dir
                img_path_root = os.path.join(img_path_root, filename)
                img_path = os.path.join(img_path, filename)
                final_image.save(img_path_root)

                stimulus_images[new_col_name_path].append(img_path)
                stimulus_images[new_col_name_file].append(filename)

                all_aois.extend(aois)
                all_words.extend(words)
                question_image_versions.extend([pd.NA for _ in range(len(aois))])

        if empty_page_inbetween and not draw_aoi:
            warnings.warn(f'Empty page for {stimulus_name} {stimulus_id}')

        aoi_df = pd.DataFrame(all_aois, columns=aoi_header)
        aoi_df['word'] = all_words
        aoi_df['question_image_version'] = question_image_versions
        aoi_df_path = os.path.join(aoi_dir, aoi_file_name)
        aoi_df.to_csv(image_config.REPO_ROOT / aoi_df_path, sep=',', index=False, encoding='UTF-8')

    # Create a new csv file with the names of the pictures in the first column and their paths in the second
    image_df = pd.DataFrame(stimulus_images)
    final_stimulus_df = initial_stimulus_df.join(image_df)
    stimuli_file_name_stem = Path(stimuli_csv_file_name).stem
    full_output_file_name = f'{stimuli_file_name_stem}_{image_config.COUNTRY_CODE}_{image_config.LAB_NUMBER}{"_aoi" if draw_aoi else ""}_with_img_paths.csv'
    full_path = os.path.join(image_config.OUTPUT_TOP_DIR, full_output_file_name)
    CONFIG.setdefault('PATHS', {}).update({f'stimuli_images{"_aoi" if draw_aoi else ""}_csv': full_path})
    final_stimulus_df.to_csv(
        image_config.REPO_ROOT / full_path,
        sep=',',
        index=False
    )


def get_option_span_indices(text: str, span: str, span_marker: str) -> list:
    """
    Searches a text span in a text and returns the word and char indices in the text of the span.
    :param text: Text with annotated spans
    :param span: That span that is marked in the text
    :param span_marker: The marker that is used to mark the span in the text
    :return: Word and char indices of the span in the text

    see: https://pynative.com/python-find-position-of-regex-match-using-span-start-end/
    """
    pass


def create_stimuli_images():
    if os.path.isfile(image_config.REPO_ROOT / image_config.STIMULI_FILE_PATH):
        create_images(
            image_config.REPO_ROOT / image_config.STIMULI_FILE_PATH,
            image_config.REPO_ROOT / image_config.QUESTION_FILE_PATH,
            draw_aoi=False
        )

        create_images(
            image_config.REPO_ROOT / image_config.STIMULI_FILE_PATH,
            image_config.REPO_ROOT / image_config.QUESTION_FILE_PATH,
            draw_aoi=True
        )
    else:
        warnings.warn(
            f'No excel file for stimuli found at {image_config.REPO_ROOT / image_config.STIMULI_FILE_PATH}. '
            f'No stimuli images will be created.'
        )

    # check whether excel for other screens exists
    if os.path.isfile(image_config.REPO_ROOT / image_config.OTHER_SCREENS_FILE_PATH):

        create_other_screens(draw_aoi=False)

    else:
        print(
            f'No excel file for other screens found at {image_config.REPO_ROOT / image_config.OTHER_SCREENS_FILE_PATH}. '
            f'No other screens will be created.'
        )

    # create randomization file for the stimuli
    # read the stimulus order version from the global config and select the versions ranging from
    # image_config.VERSION_START to image_config.NUM_PERMUTATIONS + image_config.VERSION_START
    all_versions_df = pd.read_csv(image_config.RANDOMIZATION_CSV, sep=',', encoding='UTF-8')
    # get those entries between the version start and the number of permutations + version start
    language_versions_df = all_versions_df[all_versions_df['version_number'].between(
        image_config.VERSION_START, image_config.NUM_PERMUTATIONS + image_config.VERSION_START,
        inclusive='left'
    )]

    language_versions_df.to_csv(
        image_config.REPO_ROOT / image_config.OUTPUT_TOP_DIR / 'config' /
        f'stimulus_order_versions_{image_config.LANGUAGE}_'
        f'{image_config.COUNTRY_CODE}_{image_config.LAB_NUMBER}.csv',
        sep=',',
        index=False
    )


def draw_text(text: str, image: Image, fontsize: int, draw_aoi: bool = False,
              spacing: int = image_config.LINE_SPACING, image_short_name: str = None,
              anchor_x_px: int = image_config.ANCHOR_POINT_X_PX,
              anchor_y_px: int = image_config.ANCHOR_POINT_Y_PX,
              text_width_px: int = None,
              script_direction: str = image_config.SCRIPT_DIRECTION,
              question_option_type: str | None = None,
              word_split_criterion: str = '\\s',
              line_limit: int = 9, character_limit: int = None) -> (list[list], list):
    """
    Draws text on an image and creates aoi boxes for each letter
    :param text: str
        text to draw on the image
    :param image: Image
        a previously created Pillow Image object
    :param fontsize: int
        the height of the font in pixels
    :param draw_aoi: bool
        Whether to draw aoi boxes around each letter
    :param spacing:
        spacing between the lines of the text in. Will be multiplied with the font size
    :param image_short_name: str
       the image short name is the name of the image that is currently being created
    :param anchor_x_px: int
        the top left corner x coordinate of the text
    :param anchor_y_px: int
        the top left corner y coordinate of the text
    :param text_width_px: int
        the width of the text in pixels
    :param script_direction: str
        the direction of the script, either 'ltr' or 'rtl'
    :param question_option_type: str
        if the text is a question option, the type of the question option, e.g. 'left', 'up', 'right', 'down'
    :param word_split_criterion:
        defines where to split words in the input text. Default '\\s' means split at white spaces. None will split each
        character separately.
    :param line_limit: int
        how many lines are allowed on the image. If more, a warning will be raised but the image will still be created!
    :param character_limit: int
        how many characters are allowed on each line. Mutally exclusive with text_width_px

    :return: list[list], list
        the first list contains a list for each character aoi together with the information about the size and position
        the second list contains all words in text order as many times as there are characters in the word
    """
    if script_direction not in ['ltr', 'rtl']:
        raise ValueError(f'Script direction must be either "ltr" or "rtl", not {script_direction}')

    if not text_width_px and not character_limit:
        character_limit = image_config.MAX_CHARS_PER_LINE
    elif text_width_px and character_limit:
        raise ValueError('Only one of text_width_px and character_limit can be set')

    # Create a drawing object on the given image
    draw = ImageDraw.Draw(image)

    font = ImageFont.truetype(str(image_config.REPO_ROOT / image_config.FONT_TYPE), fontsize)

    # TODO make sure this works for different scripts!
    try:
        paragraphs = re.split(r'\n+', text.strip())
    except AttributeError as e:
        print(text, image_short_name)
        raise e

    aois = []
    all_words = []
    line_idx = 0
    all_lines = []

    num_text_lines = 0
    word_idx = 0
    aoi_idx = 0

    for paragraph in paragraphs:
        if word_split_criterion == '':
            words_in_paragraph = [char.strip() for char in paragraph]
            character_limit = None
            text_width_px = image_config.TEXT_WIDTH_PX
        elif word_split_criterion == ' ':
            words_in_paragraph = paragraph.split()
        else:
            words_in_paragraph = paragraph.split(word_split_criterion)
        line = ""
        lines = []

        # create lines based on image margins
        for word in words_in_paragraph:
            left, top, right, bottom = draw.multiline_textbbox(
                (0, 0), line + word, font=font
            )
            text_width = right - left

            if character_limit:
                if len(line) + len(word) > character_limit:
                    lines.append(line.strip())
                    num_text_lines += 1
                    line = word + word_split_criterion
                else:
                    line += word.strip() + word_split_criterion
            else:
                if text_width < text_width_px:
                    line += word.strip() + word_split_criterion
                else:
                    lines.append(line.strip())
                    num_text_lines += 1
                    line = word + word_split_criterion

        lines.append(line.strip())
        num_text_lines += 1

        if num_text_lines > line_limit and not draw_aoi:
            warnings.warn(f'Too many lines for {image_short_name}: {num_text_lines}')

        for line in lines:

            if len(line) == 0:
                continue

            all_lines.append(line)

            words_in_line = line.split()
            x_word = anchor_x_px

            left, top, right, bottom = draw.multiline_textbbox(
                (0, 0), line, font=font,
                anchor='ra' if script_direction == 'rtl' else 'la'
            )
            line_width = right - left

            # get metrics returns the ascent and descent of the font from the baseline
            line_height = font.getmetrics()[0] + font.getmetrics()[1]
            # calculate aoi boxes for each letter
            top_left_corner_x_letter = anchor_x_px
            words = []

            char_idx_in_line = 0
            word_idx_in_line = 0

            stop_bold = False
            num_words = len(words_in_line)

            for word_number, word in enumerate(words_in_line):

                if word.startswith('**'):
                    font = ImageFont.truetype(str(image_config.REPO_ROOT / image_config.FONT_TYPE_BOLD), fontsize)
                    word = word[2:]

                if word.endswith('**'):
                    stop_bold = True
                    word = word[:-2]

                # TODO: add case for Chinese, if word == '*'

                # add a space if it is in the middle of a line
                if word_number < num_words - 1:
                    word = word + word_split_criterion

                word_left, word_top, word_right, word_bottom = draw.multiline_textbbox(
                    (0, 0), word, font=font
                )

                word_width = word_right - word_left

                draw.text(
                    (x_word, anchor_y_px), word, fill=image_config.TEXT_COLOR,
                    font=font, anchor='ra' if script_direction == 'rtl' else 'la'
                )

                for char_idx, char in enumerate(word):

                    aoi_y = anchor_y_px

                    char_left, _, char_right, _ = draw.multiline_textbbox(
                        (0, 0), char, font=font, anchor='ra' if script_direction == 'rtl' else 'la'
                    )

                    letter_width = char_right - char_left

                    if script_direction == 'rtl':
                        aoi_x = top_left_corner_x_letter - letter_width
                    else:
                        aoi_x = top_left_corner_x_letter

                    if draw_aoi:
                        draw.rectangle(
                            (aoi_x, aoi_y,
                             aoi_x + letter_width,
                             aoi_y + line_height),
                            outline='red', width=1
                        )

                    # aoi_header = ['char_idx', 'char', 'x', 'y', 'width', 'height', 'char_idx_in_line',
                    # 'line_idx', 'page',
                    # 'word_idx', 'word_idx_in_line']
                    # as the image is smaller than the actual screen we need to calculate the aoi boxes
                    aoi_x = aoi_x  # + ((image_config.RESOLUTION[0] - image_config.IMAGE_WIDTH_PX) // 2)
                    aoi_y = aoi_y  # + ((image_config.RESOLUTION[1] - image_config.IMAGE_HEIGHT_PX) // 2)

                    aoi_letter = [
                        aoi_idx, char, aoi_x, aoi_y,
                        letter_width, line_height,
                        char_idx_in_line, line_idx, image_short_name, word_idx, word_idx_in_line
                    ]

                    # update top left corner x for next letter
                    if script_direction == 'rtl':
                        top_left_corner_x_letter -= letter_width
                    else:
                        top_left_corner_x_letter += letter_width

                    aois.append(aoi_letter)

                    char_idx_in_line += 1
                    aoi_idx += 1

                word_idx_in_line += 1
                word_idx += 1

                if word_number < num_words - 1:
                    words.extend([word.strip() for _ in range(len(word.strip()))] + [pd.NA])
                else:
                    words.extend([word.strip() for _ in range(len(word))])

                if stop_bold:
                    font = ImageFont.truetype(str(image_config.REPO_ROOT / image_config.FONT_TYPE), fontsize)
                    stop_bold = False

                x_word = x_word + word_width if script_direction == 'ltr' else x_word - word_width

            all_words.extend(words)
            anchor_y_px += line_height * spacing
            line_idx += 1

    if question_option_type and not draw_aoi:
        num_lines = len(all_lines)
        num_words = len(text.split())
        num_chars = len(text.strip())
        if question_option_type == 'left' or 'right':
            # count only the lines with text
            if num_lines > 3:
                warnings.warn(
                    f'Questions options that do not fit:\n{image_short_name},{num_lines} lines,{num_words} words,{num_chars} chars'
                )
        else:

            if num_lines > 2:
                warnings.warn(
                    f'Questions options that do not fit:\n{image_short_name},{num_lines} lines,{num_words} words,{num_chars} chars'
                )

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


def create_welcome_screen(image: Image, text: str) -> None:
    """
    Creates a welcome screen with a white background, all the logos and a blue greeting in the middle of the screen.
    """
    root = Path(__file__).parent.parent
    # We have three different logos - load them and change the size if needed
    cost_logo = Image.open(root / "logo_imgs/cost_logo.jpg")
    cost_width, cost_height = cost_logo.size
    cost_logo_new_size = (cost_width // 7, cost_height // 7)
    cost_logo = cost_logo.resize(cost_logo_new_size)

    eu_logo = Image.open(root / "logo_imgs/eu_fund_logo.png")
    eu_width, eu_height = eu_logo.size
    eu_logo_new_size = (eu_width // 7, eu_height // 7)
    eu_logo = eu_logo.resize(eu_logo_new_size)

    multipleye_logo = Image.open(root / "logo_imgs/logo_multipleye.png")

    # Set the text
    our_blue = "#007baf"
    our_red = "#b94128"
    font_size_title = 38
    font_size_text = 28
    font_type = str(root / "fonts/open-sans-bold.ttf")

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
        multipleye_logo, multipleye_logo_position, mask=multipleye_logo
    )
    image.paste(eu_logo, eu_logo_position, mask=eu_logo)
    image.paste(cost_logo, cost_logo_position)

    texts = text.split('\n')

    text_y = image_config.IMAGE_HEIGHT_PX // 3
    for idx, t in enumerate(texts):
        if idx == 0:
            font = ImageFont.truetype(font_type, font_size_title)

        else:
            font = ImageFont.truetype(font_type, font_size_text)

        left, top, right, bottom = draw.multiline_textbbox(
            (0, 0), t, font=font
        )

        text_width, text_height = right - left, bottom - top
        text_x = (image_config.IMAGE_WIDTH_PX - text_width) // 2
        text_y += text_height * 5
        draw.text((text_x, text_y), t, font=font, fill=our_blue)


def create_fixation_screen(image: Image):
    """
    Creates a fixation screen with a white background and a fixation dot in the top left corner.
    """
    # Create a drawing object
    draw = ImageDraw.Draw(image)

    # The fixation dot is positioned a bit left to the first char in the middle of the line
    r = 7
    fix_x = 0.75 * image_config.MIN_MARGIN_LEFT_PX if image_config.SCRIPT_DIRECTION == 'ltr' else image_config.IMAGE_WIDTH_PX - 0.75 * image_config.MIN_MARGIN_RIGHT_PX
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
    root = Path(__file__).parent.parent
    multipleye_logo = Image.open(root / "logo_imgs/logo_multipleye.png")

    final_text = text.split('\n')

    our_blue = "#007baf"
    our_red = "#b94128"
    font_size = 38
    font_type = str(root / "fonts/open-sans-bold.ttf")

    # Create a drawing object
    draw = ImageDraw.Draw(image)

    # Create coordinates for three different logos
    multipleye_logo_x = (image.width - multipleye_logo.width) // 2
    multipleye_logo_y = 10
    multipleye_logo_position = (multipleye_logo_x, multipleye_logo_y)

    # Paste the logos onto the final image at the calculated coordinates
    image.paste(
        multipleye_logo, multipleye_logo_position, mask=multipleye_logo
    )
    # final_image.paste(eu_logo, eu_logo_position, mask = eu_logo)
    # final_image.paste(cost_logo, cost_logo_position)

    # Paste the texts onto the final image
    font = ImageFont.truetype(font_type, font_size)
    text_y = 0
    text_x = 0
    for paragraph in final_text:
        left, top, right, bottom = draw.multiline_textbbox(
            (0, 0), paragraph, font=font
        )
        text_width, text_height = right - left, bottom - top
        if not text_x:
            text_x = (image_config.IMAGE_WIDTH_PX - text_width) // 2
            text_y = (image_config.IMAGE_HEIGHT_PX - text_height) // 2
        else:
            text_x = (image_config.IMAGE_WIDTH_PX - text_width) // 2
            text_y += text_width

        draw.text((text_x, text_y), paragraph, font=font, fill=our_blue)


def create_rating_screens(image: Image, text: str, title: str):
    sentences = text.split('\n')
    question = sentences[0]
    options = sentences[1:]

    draw_text(question, image, image_config.FONT_SIZE_PX, draw_aoi=False, line_limit=12,
              word_split_criterion=image_config.WORD_SPLIT_CRITERION,)

    option_y_px = 3.1 * image_config.MIN_MARGIN_TOP_PX

    option_x_px = 1.2 * image_config.MIN_MARGIN_LEFT_PX

    font = ImageFont.truetype(str(image_config.REPO_ROOT / image_config.FONT_TYPE), image_config.FONT_SIZE_PX)

    for idx, option in enumerate(options):
        if option == '':
            continue
        draw_text(
            option, image, image_config.FONT_SIZE_PX, draw_aoi=False,
            anchor_x_px=option_x_px, anchor_y_px=option_y_px, text_width_px=image_config.IMAGE_WIDTH_PX * 0.4,
            line_limit=12, word_split_criterion=image_config.WORD_SPLIT_CRITERION,
        )

        draw = ImageDraw.Draw(image)
        text_height = font.getmetrics()[0] + font.getmetrics()[1]
        new_x = option_x_px - image_config.MIN_MARGIN_LEFT_PX * 0.1
        new_width = image_config.IMAGE_WIDTH_PX * 0.4
        box_coordinates = (
            new_x,
            option_y_px,
            new_x + new_width,
            option_y_px + text_height
        )

        # draw.rectangle(box_coordinates, outline='black', width=1)

        CONFIG.setdefault('RATING_QUESTION_BOXES', {}).update({f'option_{idx}': box_coordinates})

        option_y_px += image_config.MIN_MARGIN_TOP_PX


def write_final_image_config() -> None:
    """
    Some settings from the image creation need to be imported in the experiment.
    This function writes them to a language config file.
    """

    CONFIG.setdefault('EXPERIMENT', {}).update(
        {
            'LANGUAGE': image_config.LANGUAGE,
            'NUM_PERMUTATIONS': image_config.NUM_PERMUTATIONS,
            'VERSION_START': image_config.VERSION_START,
        }
    )

    CONFIG.setdefault('IMAGE', {}).update(
        {
            'FONT_SIZE': image_config.FONT_SIZE_PX,
            'FONT': image_config.FONT_TYPE,
            'FGC': image_config.TEXT_COLOR,
            'IMAGE_BGC': image_config.BACKGROUND_COLOR,
            'IMAGE_WIDTH_PX': image_config.IMAGE_WIDTH_PX,
            'IMAGE_HEIGHT_PX': image_config.IMAGE_HEIGHT_PX,
            'MIN_MARGIN_LEFT_PX': image_config.MIN_MARGIN_LEFT_PX,
            'MIN_MARGIN_RIGHT_PX': image_config.MIN_MARGIN_RIGHT_PX,
            'MIN_MARGIN_TOP_PX': image_config.MIN_MARGIN_TOP_PX,
            'MIN_MARGIN_BOTTOM_PX': image_config.MIN_MARGIN_BOTTOM_PX,
            'IMAGE_SIZE_CM': image_config.IMAGE_SIZE_CM,
            'MAX_CHARS_PER_LINE': image_config.MAX_CHARS_PER_LINE
        }
    )

    CONFIG.setdefault('SCREEN', {}).update(
        {
            'RESOLUTION': image_config.RESOLUTION,
            'SCREEN_SIZE_CM': image_config.SCREEN_SIZE_CM,
            'DISTANCE_CM': image_config.DISTANCE_CM,
        }
    )

    CONFIG.setdefault('PATHS', {}).update(
        {
            'question_file_excel': image_config.QUESTION_FILE_PATH,
            'participant_instruction_excel': image_config.OTHER_SCREENS_FILE_PATH,
            'stimuli_file_excel': image_config.STIMULI_FILE_PATH,
            'randomization_csv': image_config.RANDOMIZATION_CSV,
        }
    )

    CONFIG.setdefault('DIRECTORIES', {}).update(
        {
            'question_image_dir': image_config.QUESTION_IMAGE_DIR,
            'image_dir': image_config.IMAGE_DIR,
            'aoi_dir': image_config.AOI_DIR,
            'aoi_question_dir': image_config.AOI_QUESTION_DIR,
            'aoi_image_dir': image_config.AOI_IMG_DIR,
            'other_screens_dir': image_config.OTHER_SCREENS_DIR,
            'output_top_dir': image_config.OUTPUT_TOP_DIR,
        }
    )

    # probably need to refactor this method, but whatever
    config_utils.write_final_config(image_config.FINAL_CONFIG, CONFIG)


def create_other_screens(draw_aoi=False):
    other_screen_df = pd.read_excel(image_config.REPO_ROOT / image_config.OTHER_SCREENS_FILE_PATH)
    other_screen_df.dropna(subset=['instruction_screen_id'], inplace=True)

    if not os.path.isdir(image_config.REPO_ROOT / image_config.OTHER_SCREENS_DIR):
        os.mkdir(image_config.REPO_ROOT / image_config.OTHER_SCREENS_DIR)

    file_names = []
    file_paths = []

    for idx, row in tqdm(
            other_screen_df.iterrows(),
            desc=f'Creating {image_config.LANGUAGE}{" aoi" if draw_aoi else ""} participant instruction images',
            total=len(other_screen_df)
    ):

        final_image = Image.new(
            'RGB', (image_config.IMAGE_WIDTH_PX, image_config.IMAGE_HEIGHT_PX), color=image_config.BACKGROUND_COLOR
        )

        title = row["instruction_screen_name"]
        text = row["instruction_screen_text"]

        if title == "welcome_screen":
            create_welcome_screen(final_image, text)

        elif title == "fixation_screen":
            create_fixation_screen(final_image)

        elif title == "final_screen":
            create_final_screen(final_image, text)

        elif title == 'familiarity_rating_screen_1':
            create_rating_screens(final_image, text, title)

        elif title == 'subject_difficulty_screen' or title == 'familiarity_rating_screen_2':
            create_rating_screens(final_image, text, title)

        # for all other text screens
        elif title != 'empty_screen':
            draw_text(text, final_image, image_config.FONT_SIZE_PX - 2, spacing=2, draw_aoi=False, line_limit=12,
                      word_split_criterion=image_config.WORD_SPLIT_CRITERION)

        file_name = f'{title}_{image_config.LANGUAGE}.png'
        file_path = image_config.OTHER_SCREENS_DIR + file_name
        file_names.append(file_name)
        file_paths.append(file_path)

        final_image.save(image_config.REPO_ROOT / image_config.OTHER_SCREENS_DIR / file_name)

    other_screen_df['instruction_screen_img_name'] = file_names
    other_screen_df['instruction_screen_img_path'] = file_paths

    participant_instruction_csv_path = (image_config.OTHER_SCREENS_FILE_PATH[:-5]
                                        + f'{"_aoi" if draw_aoi else ""}_with_img_paths.csv')

    CONFIG.setdefault('PATHS', {}).update(
        {f'participant_instruction{"_aoi" if draw_aoi else ""}_csv': participant_instruction_csv_path}
    )

    other_screen_df.to_csv(
        image_config.REPO_ROOT / participant_instruction_csv_path,
        index=False
    )


if __name__ == '__main__':
    create_stimuli_images()
    write_final_image_config()

    # get_option_span_indices('This is <tb>a test sentence.<te>', '<tb>', '<te>')
