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
    guild_id: int,
    setting: str,
    value,
    path: Path = settings_path
) -> None:
    with open(path, 'r') as json_file:
        settings = json.load(json_file)

    # Change value
    settings[setting][str(guild_id)] = value

    # Write new data
    with open(path, 'w') as json_file:
        json.dump(settings, json_file)


def get_setting(
    guild_id: int,
    setting: int | str,
    default: int | str | None,
    path: Path = settings_path,
) -> int | str | None:
    s_guild_id = str(guild_id)
    with open(path, 'r') as json_file:
        settings = json.load(json_file)

    try:
        value = settings[setting][s_guild_id]
        return value

    except Exception as e:
        logging.info(f'Default setting used: {e}')
        print(e)
        settings[setting][s_guild_id] = default
        with open(path, 'w') as json_file:
            json.dump(settings, json_file)
        return default
