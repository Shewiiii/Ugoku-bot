import json


def get_upload_size_limit(
    guild_id: int | str,
    path: str = 'config/settings.json',
    default: int = 25000000
):
    guild_id = str(guild_id)
    with open('config/settings.json', 'r') as json_file:
        settings = json.load(json_file)
    try:
        settings['uploadSizeLimit'][guild_id]
        
    except:
        settings['uploadSizeLimit'][guild_id] = default
        with open('config/settings.json', 'w') as json_file:
            json.dump(settings, json_file)
        
    return default