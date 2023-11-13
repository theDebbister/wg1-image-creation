import os


def write_final_config(
        config_path: str,
        config_values: dict,
) -> None:

    open(config_path, 'w').close()

    # write config values to config file under config header

    with open(config_path, 'a') as configfile:

        for header, configuration in config_values.items():

            configfile.write(f'\n# {header} {"#" * 10}\n')

            for key, value in configuration.items():

                if isinstance(value, str):
                    configfile.write(f'{key} = "{value}"\n')
                else:
                    configfile.write(f'{key} = {value}\n')


def read_image_configuration(config_path: str) -> dict:

    image_config = {}

    with open(config_path, 'r', encoding='utf8') as configfile:
        for line in configfile:
            if line.startswith('RESOLUTION'):
                image_config['RESOLUTION'] = eval(line.split('=')[1])
            elif line.startswith('SCREEN_SIZE_CM'):
                image_config['SCREEN_SIZE_CM'] = eval(line.split('=')[1])
            elif line.startswith('DISTANCE_CM'):
                image_config['DISTANCE_CM'] = eval(line.split('=')[1])
            elif line.startswith('SCRIPT_DIRECTION'):
                image_config['SCRIPT_DIRECTION'] = eval(line.split('=')[1])
            elif line.startswith('LAB_NUMBER'):
                image_config['LAB_NUMBER'] = eval(line.split('=')[1])

    return image_config

