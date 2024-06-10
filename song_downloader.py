from pathlib import Path
from dotenv import load_dotenv
import os
from os import listdir
from os.path import isfile, join
from datetime import datetime
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
from deezer.errors import WrongLicense


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


load_dotenv()
ARL = os.getenv('DEEZER_ARL')


def get_format(
    bitrate: int | str,
):

    if bitrate == TrackFormats.FLAC:
        format_ = 'flac'
    else:
        format_ = 'mp3'

    return format_


def get_account_country(path: str = 'config/settings.json'):
    with open(path, 'r') as json_file:
        settings = json.load(json_file)

    return settings['country']


def get_downloadObjects(
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
                dz, link, bitrate, plugins, listener)
        except GenerationError as e:
            print(f"{e.link}: {e.message}")
            continue
        if isinstance(downloadObject, list):
            downloadObjects += downloadObject
        else:
            downloadObjects.append(downloadObject)

    return downloadObjects


def download(
    url: str,
    brfm: str = 'mp3 320',
) -> dict | bool:
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
    if not dz.login_via_arl(ARL):
        raise InvalidARL
    country = get_account_country()

    # Init setteings, format and bitrate
    brfm = brfm.lower()
    settings = loadSettings(configFolder)
    bitrate = getBitrateNumberFromText(str(brfm))
    format_ = get_format(bitrate)

    # Init objects
    url = [url]
    downloadObjects = get_downloadObjects(
        url=url,
        dz=dz,
        bitrate=bitrate,
        plugins=plugins,
        listener=listener,
    )

    def downloadLinks(url, format_: str, downloadObjects: list):
        final_paths = []
        for i, obj in enumerate(downloadObjects):
            # Create Track object to get final path
            if obj.__type__ == "Convertable":
                obj = plugins[obj.plugin].convert(dz, obj, settings, listener)

            if isinstance(obj, Single):
                trackAPI = obj.single.get('trackAPI')
                albumAPI = obj.single.get('albumAPI')
                playlistAPI = obj.single.get('playlistAPI')

            elif isinstance(obj, Collection):
                temp_track = obj.collection['tracks'][0]
                trackAPI = temp_track
                trackAPI['size'] = obj.size
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
            if (isinstance(obj, Single)
                    and country in trackAPI['available_countries']):
                # Set the path according to the bitrate/format
                final_path = Path(
                    f'{path[-1]}/{brfm}/{path[0]}.{format_}'
                )
                final_paths.append((trackAPI, final_path))

            elif isinstance(obj, Collection):
                # Set the path according to the bitrate/format
                final_path = Path(f'{brfm}/{path[-1]}')
                if 'playlist' in url[i]:
                    final_paths.append((playlistAPI, final_path))
                else:
                    final_paths.append((albumAPI, final_path))
                    
            # Set the path according to the bitrate/format
            settings['downloadLocation'] = f'output/songs/{brfm}'
            Downloader(dz, obj, settings, listener).start()

        return final_paths

    # If first url is filepath readfile and use them as URLs
    try:
        isfile = Path(url[0]).is_file()
    except Exception:
        isfile = False
    if isfile:
        filename = url[0]
        with open(filename, encoding="utf-8") as f:
            url = f.readlines()

    final_paths = downloadLinks(url, format_, downloadObjects)

    # [0][0]: API, [0][1]: Path
    # ultra spaghetti, recursion would be much cleaner...
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

        # Delete the old zip if exists
        if os.path.isfile(real_final):
            os.remove(real_final)

        # Init the zip file
        zip_file = ZipFile(real_final, mode='w')

        # Add files associated to each path
        for api, path in final_paths:
            print(path)
            # Case 1.1.1: One of the thing is a folder
            if path.is_dir():

                things = listdir(path)
                # Checking sub repos
                for thing in things:
                    if (path / thing).is_dir():
                        files = listdir(path / thing)
                        for file in files:
                            if format_ in file:
                                zip_file.write(path / thing / file)
                    else:
                        if format_ in thing:
                            zip_file.write(path / thing)

            # Case 1.1.2: One of the thing is a song
            else:
                if format_ in str(path):
                    zip_file.write(path)

        zip_file.close()
        return {'api': final_paths[0][0], 'path': real_final}
    # Case 2: It's a song
    else:
        return {'api': final_paths[0][0], 'path': final_paths[0][1]}

# if __name__ == '__main__':
#     download('https://open.spotify.com/album/7CGrlFSDFczGuz2Kx14fZU?si=Ip7RfFt-QGq-Zxr2zBnplQ')
