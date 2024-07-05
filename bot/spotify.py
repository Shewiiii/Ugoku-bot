from librespot.core import Session
from librespot.metadata import TrackId
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from bot.search import is_url

from io import BytesIO
import re
from dotenv import load_dotenv
import os


load_dotenv()
# Variables
SPOTIFY_USERNAME = os.getenv('SPOTIFY_USERNAME')
SPOTIFY_PASSWORD = os.getenv('SPOTIFY_PASSWORD')

SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

# Init session
# librespot
session = Session.Builder() \
    .user_pass(SPOTIFY_USERNAME, SPOTIFY_PASSWORD) \
    .create()

# Spotipy
scope = "user-library-read"
auth_manager = SpotifyClientCredentials()
sp = spotipy.Spotify(auth_manager=auth_manager)


class SpotifyDownloader:
    async def get_track_source(self, id: str) -> BytesIO | None:
        '''Get the data of a track from a single ID.
        Returns an info dictionary.
        '''
        track_id: TrackId = TrackId.from_uri(f"spotify:track:{id}")
        stream = session.content_feeder().load(
            track_id, VorbisOnlyAudioQuality(
                AudioQuality.VERY_HIGH), False, None
        )

        source: bytes = stream.input_stream.stream().read()
        io_source = BytesIO(source)
        return io_source

    async def get_track_name(self, id: str) -> str | None:
        try:
            track_API: dict = sp.track(id)
        except TypeError:
            return

        display_name: str = (
            f"{track_API['artists'][0]['name']} "
            f"- {track_API['name']}"
        )
        return display_name

    async def get_id_from_url(self, url: str) -> str | None:
        track_url_search = re.findall(
            r"^(https?://)?open\.spotify\.com/track/(?P<TrackID>[0-9a-zA-Z]{22})(\?si=.+?)?$",
            string=url
        )
        if not track_url_search:
            return
        id: str = track_url_search[0][1]
        return id

    async def get_id_from_query(self, query: str) -> str | None:
        search = sp.search(q=query, limit=1)
        if not search:
            return
        id = search['tracks']['items'][0]['id']
        return id

    async def get_track(self, user_input: str) -> dict[str, BytesIO] | None:
        '''Returns a info dictionary {'display_name': str, 'source': BytesIO}
        '''
        if is_url(user_input, ['open.spotify.com']):
            id: str = await self.get_id_from_url(user_input)
        else:
            id = await self.get_id_from_query(query=user_input)

        if not id:
            return
        display_name = await self.get_track_name(id)
        source: BytesIO = await self.get_track_source(id)

        info_dict = {
            'display_name': display_name,
            'source': source
        }
        return info_dict
