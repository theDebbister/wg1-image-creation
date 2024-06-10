from __future__ import annotations

import json
import os
from pathlib import Path
import image_config


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


def read_image_configuration(config_path: Path | str) -> dict:
    lab_image_config = {}

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
        'resolution in px', 'screen size in cm', 'script direction', 'use of multiple devices',
    ]

    for key in necessary_keys:
        if key not in config_content:
            raise ValueError(f'Key "{key}" is missing in the configuration file.')

    lab_image_config = {
        'RESOLUTION': eval(config_content['resolution in px']),
        'SCREEN_SIZE_CM': eval(config_content['screen size in cm']),
        'SCRIPT_DIRECTION': config_content['script direction'],
        'MULTIPLE_DEVICES': config_content['use of multiple devices'],
        'DISTANCE_CM': config_content['distance in cm'],
    }

    return lab_image_config
