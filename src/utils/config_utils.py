import os
from pathlib import Path
import image_config


def write_final_config(
        config_path: str,
        config_values: dict,
) -> None:

    config_path = os.path.join(image_config.REPO_ROOT, config_path)

    # create the config file if it does not exist
    open(config_path, 'w', encoding='utf8').close()

    # write config values to config file under config header
    with open(config_path, 'a', encoding='utf8') as configfile:
        for header, configuration in config_values.items():
            configfile.write(f'\n# {header} {"#" * 10}\n')

            for key, value in configuration.items():
                if isinstance(value, str):
                    configfile.write(f'{key} = "{value}"\n')
                else:
                    configfile.write(f'{key} = {value}\n')


def read_image_configuration(config_path: Path) -> dict:

    lab_image_config = {}

    config_path = os.path.join(image_config.REPO_ROOT, config_path)

    with open(config_path, 'r', encoding='utf8') as configfile:
        for line in configfile:
            if line.startswith('RESOLUTION'):
                lab_image_config['RESOLUTION'] = eval(line.split('=')[1])
            elif line.startswith('SCREEN_SIZE_CM'):
                lab_image_config['SCREEN_SIZE_CM'] = eval(line.split('=')[1])
            elif line.startswith('DISTANCE_CM'):
                lab_image_config['DISTANCE_CM'] = eval(line.split('=')[1])
            elif line.startswith('SCRIPT_DIRECTION'):
                lab_image_config['SCRIPT_DIRECTION'] = eval(line.split('=')[1])
            elif line.startswith('LAB_NUMBER'):
                lab_image_config['LAB_NUMBER'] = eval(line.split('=')[1])

    return lab_image_config

