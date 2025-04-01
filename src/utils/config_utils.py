from __future__ import annotations

import json
import os
from pathlib import Path
import image_config
from PIL import ImageFont


def write_final_config(
        config_path: str,
        config_values: dict,
) -> None:
    config_path = os.path.join(image_config.REPO_ROOT, config_path)
    old_content = ''

    # create the config file if it does not exist
    open(config_path, 'w', encoding='utf8').close()

    # read what is already in the file as we want to prepend the new values
    with open(config_path, 'r', encoding='utf8') as configfile:
        old_content = configfile.read()

    # write config values to config file under config header
    with open(config_path, 'a', encoding='utf8') as configfile:
        for header, configuration in config_values.items():
            configfile.write(f'\n# {header} {"#" * 10}\n')

            for key, value in configuration.items():
                if isinstance(value, str):
                    configfile.write(f'{key} = "{value}"\n')
                else:
                    configfile.write(f'{key} = {value}\n')

        configfile.write(old_content)


def parse_true_false(value: str) -> bool:
    if value.lower() in {'true', 'yes', '1', 'on'}:
        return True
    elif value.lower() in {'false', 'no', '0', 'off'}:
        return False
    else:
        raise ValueError(f'Invalid boolean value: {value}. Expected "true", "false", "yes", "no", "1", "0", "on", or "off".')


def read_image_configuration(config_path: Path | str) -> dict:

    config_path = os.path.join(image_config.REPO_ROOT, config_path)

    with open(config_path, 'r', encoding='utf8') as configfile:
        config_content = json.load(configfile)

    # the contact information should be removed from the config file
    # if it is still in there, it is deleted and the file written again
    if 'contact information' in config_content:
        config_content.pop('contact information')
        json.dump(config_content, open(config_path, 'w', encoding='utf8'))

    # check whether all necessary keys are in the config file
    necessary_keys = [
        'Monitor_resolution_in_px', 'Screen_size_in_cm', 'Script_direction', 'Use_of_multiple_devices',
        'Distance_in_cm',
    ]

    for key in necessary_keys:
        if key not in config_content:
            raise ValueError(f'Key "{key}" is missing in the configuration file.')

    # the distance is only in the config if it is NOT 60 cm otherwise the field is empty
    lab_image_config = {
        'RESOLUTION': eval(config_content['Monitor_resolution_in_px']),
        'SCREEN_SIZE_CM': eval(config_content['Screen_size_in_cm']),
        'SCRIPT_DIRECTION': config_content['Script_direction'],
        'MULTIPLE_DEVICES': parse_true_false(config_content['Use_of_multiple_devices']),
        'DISTANCE_CM': 60 if not config_content['Distance_in_cm'] else int(config_content['Distance_in_cm']),
    }

    return lab_image_config


def calculate_font_size():

    # one line on the image should fit approximately 82 latin characters
    size = 0
    text = 'a' * image_config.MAX_CHARS_PER_LINE
    text_width = 0

    while text_width < image_config.TEXT_WIDTH_PX:
        size += 1
        font = ImageFont.truetype(str(image_config.REPO_ROOT / image_config.FONT_TYPE), size)
        text_width = font.font.getsize(text)[0][0]
        if text_width >= image_config.TEXT_WIDTH_PX:
            size -= 1
            break

    return size






