from pathlib import Path
from dotenv import load_dotenv
import os
from os import listdir
from datetime import datetime
from typing import Literal

from deezer import Deezer
from deezer import TrackFormats
from deemix import generateDownloadObject
from deemix.settings import load as loadSettings
from deemix.utils import getBitrateNumberFromText, formatListener
from deemix.downloader import Downloader
from deemix.itemgen import GenerationError
from deemix.types.DownloadObjects import Single, Collection
from deemix.plugins.spotify import Spotify
from zipfile import ZipFile

import discord
from bot.timer import Timer
from bot.arls import get_arl, get_countries, load_arl
from bot.search import ISO3166, A_ISO3166

from bot.exceptions import *


class LogListener:
    @classmethod
    def send(cls, key, value=None):
        logString = formatListener(key, value)
        if logString:
            print(logString)

# ----------GLOBAL SETTINGS----------


# env things
load_dotenv()
ARL = str(os.getenv('DEEZER_ARL'))
ARL_COUNTRY = os.getenv('ARL_COUNTRY')

config_path = Path('.') / 'deemix' / 'config'

# Init settings
settings = loadSettings(config_path)

# Init folders
output_path = Path('.') / 'output'

a_songs_path = output_path / 'archives' / 'songs'
a_songs_path.mkdir(parents=True, exist_ok=True)

# Load deezer
dz = Deezer()
listener = LogListener()
plugins = {
    "spotify": Spotify(configFolder=config_path)
}
plugins["spotify"].setup()

# Load account
dz.login_via_arl(ARL)
# country = get_account_country()

# Init custom arl
custom_arls = {}

# ------------------------------------


def get_format(bitrate: Literal[9, 3, 1, 15, 14, 13] | None):
    if bitrate == TrackFormats.FLAC:
        format_ = 'flac'
    else:
        format_ = 'mp3'

    return format_


def recursive_write(path, zip_file):
    for entry in listdir(path):
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            recursive_write(full_path, zip_file)
        else:
            zip_file.write(full_path)


def get_objects(
    url: list,
    dz: Deezer | None,
    bitrate: Literal[9, 3, 1, 15, 14, 13] | None,
    plugins: dict,
    listener: LogListener,
) -> list | None:
    if not dz:
        return
    links = []
    for link in url:
        if ';' in link:
            for l in link.split(";"):
                links.append(l)
        else:
            links.append(link)

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

    return downloadObjects


def init_dl(
    url: str,
    user_id: int,
    brfm: str = 'mp3 320',
    arl_info: dict = {'arl': ARL, 'country': ARL_COUNTRY},
    settings: dict = settings
) -> tuple[list, str]:
    # Check if custom_arl
    dz = load_arl(user_id, arl_info['arl'])

    # Set the path according to the bitrate/format
    og_path = settings['downloadLocation']
    settings['downloadLocation'] = f"{settings['downloadLocation']}/{brfm}"

    bitrate = getBitrateNumberFromText(str(brfm))
    format_ = get_format(bitrate)

    brfm = brfm.lower()

    # Init objects
    downloadObjects = get_objects(
        url=[url],
        dz=dz,
        bitrate=bitrate,
        plugins=plugins,
        listener=listener,
    )
    if not downloadObjects:
        raise TrackNotFound
    else:
        converted_objs = []
        for obj in downloadObjects:
            if obj.__type__ == "Convertable":
                obj: Collection = plugins[obj.plugin].convert(
                    dz,
                    obj,
                    settings,
                    listener
                )
            converted_objs.append(obj)

    # Put the normal path again
    settings['downloadLocation'] = og_path
    return converted_objs, format_


async def download_links(
    dz: Deezer,
    downloadObjects: list,
    ctx: discord.ApplicationContext | None = None,
    timer: Timer | None = None,
    settings: dict = settings
) -> list:
    all_data = []
    for obj in downloadObjects:
        # Create Track object to get final path
        try:
            all_data += await Downloader(
                dz=dz,
                downloadObject=obj,
                settings=settings,
                ctx=ctx,
                listener=listener,
                timer=timer
            ).start()
        except TrackNotFound:
            if len(downloadObjects) > 1 and ctx:
                ctx.respond("A song could not be downloaded, "
                            "try using a different ARL.")
            else:
                raise TrackNotFound

    return all_data


async def download(
    downloadObjects: list,
    format_: str,
    ctx: discord.ApplicationContext,
    arl: str | int | None = ARL,
    timer: Timer | None = None,
) -> dict | None:
    arl = str(arl)
    # Check if custom_arl
    dz = load_arl(ctx.user.id, arl)
    if not dz:
        return

    # Download all
    all_data = await download_links(
        dz,
        downloadObjects,
        ctx=ctx,
        timer=timer,
    )

    # [0][0]: API, [0][1]: Path
    real_final = ''
    path_count = len(all_data)
    if path_count == 0:
        raise TrackNotFound
    # Case 1: It's not a song
    elif path_count > 1 or all_data[0]['path'].is_dir():

        # Case 1.1: There is only one folder
        if path_count == 1:
            real_final = ("./output/archives/songs/"
                          f"{all_data[0]['title']}.zip")

        # Case 1.2: There is *not* only one folder
        else:
            now = datetime.now()
            ts = datetime.timestamp(now)
            real_final = ("./output/archives/songs/"
                          f"Compilation {ts}.zip")

        # Init the zip file
        zip_file = ZipFile(real_final, mode='w')

        # Add files associated to each path
        for info_dict in all_data:
            path = info_dict['path']

            # Case 1.1.1: One of the thing is a folder
            if path.is_dir():
                recursive_write(path, zip_file)
            # Case 1.1.2: One of the thing is a song
            else:
                if format_ in str(path) and path.is_file():
                    zip_file.write(path)

        zip_file.close()
        return {'all_data': all_data, 'path': real_final}
    # Case 2: It's a song
    else:
        return {'all_data': all_data, 'path': all_data[0]['path']}


async def dl(
    ctx: discord.ApplicationContext,
    url: str,
    arl_info: dict,
    timer: Timer,
    format: str
) -> str:
    '''Download a track or a collection then returns ther path.
    '''
    downloadObjects, format_ = init_dl(
        url=url,
        user_id=ctx.user.id,
        arl_info=arl_info,
        brfm=format
    )
    if not downloadObjects:
        raise TrackNotFound

    await ctx.edit(
        content=f'Download objects got, {timer.round()}. '
        'Fetching track data...'
    )
    results = await download(
        downloadObjects,
        format_,
        ctx=ctx,
        arl=arl_info['arl'],
        timer=timer,
    )
    if not results:
        raise TrackNotFound
    
    path = results['path']
    return path
