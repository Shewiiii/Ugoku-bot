from pathlib import Path
from dotenv import load_dotenv
import os
from os import listdir
from datetime import datetime
from typing import Literal
from copy import deepcopy

from deezer import Deezer
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
from bot.arls import load_arl
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
plugins['spotify'].setup()

# Load account
try:
    dz.login_via_arl(ARL)
    deezer_enabled = True
except:
    deezer_enabled = False
    print('Deezer features not enabled !!')
# country = get_account_country()

# Init custom arl
custom_arls = {}

# ------------------------------------


class DeezerDownloader:
    def get_extension(self, format: str) -> str:
        '''format can be like mp3 320, mp3 120, flac, ...
        '''
        format = format.lower()
        for extension in ['mp3', 'flac', 'ogg']:
            if extension in format:
                return extension

    def recursive_write(self, path, zip_file):
        for entry in listdir(path):
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                self.recursive_write(full_path, zip_file)
            else:
                zip_file.write(full_path)

    def get_objects(
        self,
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

    async def init_dl(
        self,
        url: str,
        dz: Deezer,
        format: str = 'MP3 320',
        arl_info: dict = {'arl': ARL, 'country': ARL_COUNTRY},
        settings: dict = settings
    ) -> list:
        '''Create a list of converted download objects from a Spotify/Deezer URL.
        '''
        bitrate = getBitrateNumberFromText(format)

        # Init objects
        downloadObjects = self.get_objects(
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

        return converted_objs

    async def download_links(
        self,
        dz: Deezer,
        downloadObjects: list,
        format: str,
        ctx: discord.ApplicationContext | None = None,
        timer: Timer | None = None,
        settings: dict = settings
    ) -> list:
        '''Download a single or a collection from download objects.
        Returns a list of info dictionaries.

        info_dict = {
            'trackAPI': trackAPI,
            'albumAPI': albumAPI,
            'playlistAPI': playlistAPI,
            'title': trackAPI['title'],
            'artist': trackAPI['contributors'][0]['name'],
            'source': Path(writepath),
        }

        '''
        all_data = []
        for obj in downloadObjects:
            # Create Track object to get final path
            temp_settings = deepcopy(settings)
            try:
                temp_settings['downloadLocation'] = (
                    f"{settings['downloadLocation']}/{format}"
                )
                all_data += await Downloader(
                    dz=dz,
                    downloadObject=obj,
                    ctx=ctx,
                    listener=listener,
                    timer=timer,
                    settings=temp_settings
                ).start()
            except TrackNotFound:
                if len(downloadObjects) > 1 and ctx:
                    ctx.respond("A song could not be downloaded, "
                                "try using a different ARL.")
                else:
                    raise TrackNotFound

        return all_data

    async def download(
        self,
        downloadObjects: list,
        format: str,
        ctx: discord.ApplicationContext,
        arl: str | int | None = ARL,
        timer: Timer | None = None,
    ) -> dict | None:
        '''Download a single or a collection from download objects.
        Archive collections in zip files.
        '''
        extension = self.get_extension(format)
        arl = str(arl)
        # Check if custom_arl
        dz = load_arl(ctx.user.id, arl)
        if not dz:
            return

        # Download all
        all_data = await self.download_links(
            dz,
            downloadObjects,
            ctx=ctx,
            timer=timer,
            format=format
        )

        real_final = ''
        path_count = len(all_data)
        if path_count == 0:
            raise TrackNotFound

        # ALL THE CODE BELOW IS COMPLETE MADNESS:
        # Case 1: It's not a song
        elif path_count > 1 or all_data[0]['source'].is_dir():

            # Case 1.1: There is only one folder
            if path_count == 1:
                real_final = (
                    "./output/archives/songs/"
                    f"{all_data[0]['title']}.zip"
                )

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
                path = info_dict['source']

                # Case 1.1.1: One of the thing is a folder
                if path.is_dir():
                    self.recursive_write(path, zip_file)
                # Case 1.1.2: One of the thing is a song
                else:
                    if extension in str(path) and path.is_file():
                        zip_file.write(path)

            zip_file.close()
            return {'all_data': all_data, 'source': real_final}
        # Case 2: It's a song
        else:
            return {'all_data': all_data, 'source': all_data[0]['source']}

    async def complete_dl(
        self,
        ctx: discord.ApplicationContext,
        url: str,
        arl_info: dict,
        timer: Timer,
        format: str
    ) -> str:
        '''Download a track or a collection then returns their path.
        Format examples: MP3 320, MP3 128, FLAC.
        '''
        downloadObjects = await self.init_dl(
            url=url,
            dz=load_arl(ctx.user.id, arl_info['arl']),
            arl_info=arl_info,
            format=format
        )
        if not downloadObjects:
            raise TrackNotFound

        await ctx.edit(
            content=f'Download objects got, {timer.round()}. '
            'Fetching track data...'
        )
        results = await self.download(
            downloadObjects,
            format=format,
            ctx=ctx,
            arl=arl_info['arl'],
            timer=timer,
        )
        if not results:
            raise TrackNotFound

        path = results['source']
        return path
