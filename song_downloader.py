from pathlib import Path
from dotenv import load_dotenv
import os
from os import listdir
from os.path import isfile, join
from datetime import datetime, timedelta
import json

from concurrent.futures import ThreadPoolExecutor
from deezer import Deezer
from deezer import TrackFormats
from deemix import generateDownloadObject
from deemix.settings import load as loadSettings
from deemix.utils import getBitrateNumberFromText, formatListener
import deemix.utils.localpaths as localpaths
from deemix.downloader import Downloader
from deemix.itemgen import GenerationError
from deemix.plugins.spotify import Spotify
from deemix.itemgen import generateTrackItem
from deemix.types.DownloadObjects import Single, Collection
from deemix.types.Track import Track
from deemix.utils.pathtemplates import generatePath
from zipfile import ZipFile

import discord


class LogListener:
    @classmethod
    def send(cls, key, value=None):
        logString = formatListener(key, value)
        if logString:
            print(logString)

# Exceptions:


class InvalidARL(Exception):
    pass


class TrackNotFound(Exception):
    pass

# ----------GLOBAL SETTINGS----------


load_dotenv()
ARL = os.getenv('DEEZER_ARL')

# Check for local configFolder
localpath = Path('.')
configFolder = localpath / 'config'

# Load deezer
dz = Deezer()
listener = LogListener()
plugins = {
    "spotify": Spotify(configFolder=configFolder)
}
plugins["spotify"].setup()

# Load account
dz.login_via_arl(ARL)
# country = get_account_country()

# Init setteings, format and bitrate
settings = loadSettings(configFolder)

# Init custom arl
custom_arls = {}

# ------------------------------------


def get_format(bitrate: int | str,):
    if bitrate == TrackFormats.FLAC:
        format_ = 'flac'
    else:
        format_ = 'mp3'

    return format_


# def get_account_country(path: str = 'config/settings.json'):
#     with open(path, 'r') as json_file:
#         settings = json.load(json_file)

#     return settings['country']

def recursive_write(path, zip_file):
    for entry in listdir(path):
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            recursive_write(full_path, zip_file)
        else:
            print('write:', full_path)
            zip_file.write(full_path)


def get_objects(
    url: str | list,
    dz: Deezer,
    bitrate: str,
    plugins: dict,
    listener: LogListener,
) -> list:
    links = []
    for link in url:
        if ';' in link:
            for l in link.split(";"):
                links.append(l)
        else:
            links.append(link)
    print(links)

    downloadObjects = []

    for link in links:
        try:
            downloadObject = generateDownloadObject(
                dz,
                link,
                bitrate,
                plugins,
                listener
            )
        except GenerationError as e:
            print(f"{e.link}: {e.message}")
            continue
        if isinstance(downloadObject, list):
            downloadObjects += downloadObject
        else:
            downloadObjects.append(downloadObject)

    return downloadObjects, links


def download_links(dz, links, format_: str, downloadObjects: list):
    final_paths = []
    for i, obj in enumerate(downloadObjects):
        # Create Track object to get final path
        if obj.__type__ == "Convertable":
            obj = plugins[obj.plugin].convert(
                dz,
                obj,
                settings,
                listener
            )

        if isinstance(obj, Single):
            trackAPI = obj.single.get('trackAPI')
            albumAPI = None
            playlistAPI = None

        elif isinstance(obj, Collection):
            trackAPI = obj.collection['tracks'][0]
            albumAPI = obj.collection.get('albumAPI')
            playlistAPI = obj.collection.get('playlistAPI')

        track = Track().parseData(
            dz=dz,
            track_id=trackAPI['id'],
            trackAPI=trackAPI,
            albumAPI=albumAPI,
            playlistAPI=playlistAPI,
        )

        path = generatePath(track, obj, settings)

        if isinstance(obj, Single):
            # Set the path according to the bitrate/format
            final_path = Path(
                f'{path[-1]}/{path[0]}.{format_}'
            )
            final_paths.append((trackAPI, final_path))

        elif isinstance(obj, Collection):
            # Set the path according to the bitrate/format
            if 'playlist' in links[i]:
                final_paths.append((
                    playlistAPI,
                    Path(f"{settings['downloadLocation']}"
                         f"/{playlistAPI['title']}"),
                ))
            else:
                final_paths.append((
                    albumAPI,
                    Path(f"{settings['downloadLocation']}/"
                         f"{albumAPI['contributors'][0]['name']} - "
                         f"{albumAPI['title']}"),
                ))

        Downloader(dz, obj, settings, listener).start()
    return final_paths


def load_arl(user_id: int, arl: str) -> Deezer:
    global custom_arls
    global dz
    if arl == ARL:
        return dz
    elif user_id in custom_arls:
        return custom_arls[user_id]
    else:
        # New Deezer instance
        new_dz = Deezer()
        new_dz.login_via_arl(arl)
        custom_arls[user_id] = new_dz
        return new_dz


def init_dl(
    url: str,
    guild_id: int,
    brfm: str = 'mp3 320',
    arl: str = ARL,
) -> tuple[list, list]:
    # Check if custom_arl
    dz = load_arl(guild_id, arl)

    # Set the path according to the bitrate/format
    settings['downloadLocation'] = f'output/songs/{brfm}'
    bitrate = getBitrateNumberFromText(str(brfm))
    format_ = get_format(bitrate)

    brfm = brfm.lower()

    # Init objects
    url = [url]
    downloadObjects, links = get_objects(
        url=url,
        dz=dz,
        bitrate=bitrate,
        plugins=plugins,
        listener=listener,
    )

    return downloadObjects, links, format_


def download(
    downloadObjects: list,
    links: list,
    format_: str,
    guild_id: int,
    arl: str = ARL,
) -> dict:
    # Check if custom_arl
    dz = load_arl(guild_id, arl)

    # Download all
    final_paths = download_links(
        dz,
        links,
        format_,
        downloadObjects,
    )

    # [0][0]: API, [0][1]: Path
    real_final = ''
    path_count = len(final_paths)
    # Case 1: It's not a song
    if path_count == 0:
        raise TrackNotFound
    elif path_count > 1 or final_paths[0][1].is_dir():

        # Case 1.1: There is only one folder
        if path_count == 1:
            real_final = ("./output/archives/songs/"
                          f"{final_paths[0][0]['title']}.zip")

        # Case 1.2: There is *not* only one folder
        else:
            now = datetime.now()
            ts = datetime.timestamp(now)
            real_final = ("./output/archives/songs/"
                          f"Compilation {ts}.zip")

        # Init the zip file
        zip_file = ZipFile(real_final, mode='w')

        # Add files associated to each path
        for api, path in final_paths:
            print('path:', path)

            # Case 1.1.1: One of the thing is a folder
            if path.is_dir():
                recursive_write(path, zip_file)
            # Case 1.1.2: One of the thing is a song
            else:
                if format_ in str(path) and path.is_file():
                    zip_file.write(path)

        zip_file.close()
        return {'api': final_paths[0][0], 'path': real_final}
    # Case 2: It's a song
    else:
        return {'api': final_paths[0][0], 'path': final_paths[0][1]}
