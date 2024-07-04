import json
import logging

from pathlib import Path


settings_path = Path('.') / 'bot' / 'config' / 'settings.json'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


async def change_settings(
    id: int,
    setting: str,
    value,
    path: Path = settings_path
) -> None:
    with open(path, 'r') as json_file:
        settings = json.load(json_file)

    # Change value
    settings[setting][str(id)] = value

    # Write new data
    with open(path, 'w') as json_file:
        json.dump(settings, json_file)


def get_setting(
    id: int,
    setting: int | str,
    default,
    path: Path = settings_path,
):
    s_id = str(id)
    with open(path, 'r') as json_file:
        settings = json.load(json_file)

    try:
        value = settings[setting][s_id]
        return value

    except Exception as e:
        logging.info(f'Default setting used: {e}')
        print(e)
        settings[setting][s_id] = default
        with open(path, 'w') as json_file:
            json.dump(settings, json_file)
        return default
 

def get_list(setting: str) -> list:
    with open(settings_path, 'r') as json_file:
            settings = json.load(json_file)
            return settings[setting]
