import configparser
import os


def write_to_config(
        config_path: str,
        config_header: str,
        config_value: dict,
) -> None:

    # create new config if it does not already exist
    if not os.path.isfile(config_path):
        open(config_path, 'w').close()

    # write config values to config file under config header
    config = configparser.ConfigParser()
    config.read(config_path)

    for key, value in config_value.items():
        config.set(config_header, key, str(value))

    with open(config_path, 'w') as configfile:
        config.write(configfile)
