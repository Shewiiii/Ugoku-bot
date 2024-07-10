from librespot.core import Session
from librespot.metadata import TrackId
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from bot.search import is_url, similar
from bot.exceptions import NotACollection

from io import BytesIO
import re
from dotenv import load_dotenv
import os
from pathlib import Path


load_dotenv()
# Variables
SPOTIFY_USERNAME = os.getenv('SPOTIFY_USERNAME')
SPOTIFY_PASSWORD = os.getenv('SPOTIFY_PASSWORD')

SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

ogg_path = Path('.') / 'output' / 'vc_songs' / 'OGG'
ogg_path.mkdir(parents=True, exist_ok=True)

# Init session
# librespot
try:
    session = Session.Builder() \
        .user_pass(SPOTIFY_USERNAME, SPOTIFY_PASSWORD) \
        .create()
    spotify_enabled = True
except Session.SpotifyAuthenticationException:
    spotify_enabled = False

# Spotipy
auth_manager = SpotifyClientCredentials()
sp = spotipy.Spotify(auth_manager=auth_manager)


class Spotify_:

    async def get_track_source(self, id: str) -> bytes:
        '''Get the data of a track from a single ID.
        Returns an info dictionary.
        '''
        track_id: TrackId = TrackId.from_uri(f"spotify:track:{id}")
        stream = session.content_feeder().load(
            track_id, VorbisOnlyAudioQuality(
                AudioQuality.VERY_HIGH), False, None
        )

        source: bytes = stream.input_stream.stream().read()
        return source

    def write_track_from_source(self, source: bytes, file_path: str) -> None:
        '''Write an OGG file from bytes.
        '''
        if not os.path.isfile(file_path):
            with open(file_path, 'wb') as audio_file:
                audio_file.write(source)

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

    async def get_id_from_url(self, url: str) -> dict | None:
        track_url_search = re.findall(
            r"^(https?://)?open\.spotify\.com/(track|album|playlist)/(?P<ID>[0-9a-zA-Z]{22})(\?si=.+?)?$",
            string=url
        )
        if not track_url_search:
            return
        id: str = track_url_search[0][2]
        type = track_url_search[0][1]

        if type == 'album' or type == 'playlist':
            is_collection = True
        else:
            is_collection = False

        return {'id': id, 'is_collection': is_collection}

    async def get_id_from_query(self, query: str) -> dict | None:
        search = sp.search(q=query, limit=1)
        if not search:
            return
        # Basically searching if the query is an album or song
        items: str = search['tracks']['items']
        if not items:
            return
        item = items[0]

        track_ratio: float = similar(
            query,
            # E.g: Thaehan Intro
            f"{item['artists'][0]['name']} {item['name']}"
        )
        album_ratio: float = similar(
            query,
            # E.g: Thaehan Two Poles
            f"{item['album']['artists'][0]['name']} {item['album']['name']}"
        )
        if track_ratio > album_ratio:
            id: str = item['id']
            is_collection = False
        else:
            id: str = item['album']['id']
            is_collection = True

        return {'id': id, 'is_collection': is_collection}

    async def get_track_items_from_collection(self, id: str) -> list:
        try:
            return sp.album_tracks(id)['items']
        except spotipy.SpotifyException:
            try:
                items = sp.playlist_items(id)['items']
                return [item['track'] for item in items]
            except spotipy.SpotifyException:
                raise NotACollection

    async def get_collection_track_ids(self, id: str) -> list[str]:
        items: list = await self.get_track_items_from_collection(id)
        track_ids = [item['id'] for item in items]
        return track_ids

    async def get_track_urls(self, user_input: str) -> list | None:
        ids = await self.get_track_ids(user_input)
        if not ids:
            return
        return [f'https://open.spotify.com/track/{id}' for id in ids]

    # Ok so basically only that method should be used in the bot..
    async def get_track_ids(self, user_input: str) -> list | None:
        if is_url(user_input, ['open.spotify.com']):
            result: dict = await self.get_id_from_url(user_input)
        else:
            result: dict = await self.get_id_from_query(query=user_input)
        if not result:
            return

        if result['is_collection']:
            ids: list = await self.get_collection_track_ids(result['id'])
            return ids

        return [result['id']]

    # ..And that one :elaina_magic:
    async def get_track(self, id: str) -> dict[str, BytesIO] | None:
        '''Returns a info dictionary {'display_name': str, 'source': str (the path)}
        '''
        display_name: str = await self.get_track_name(id)
        file_path = ogg_path / f'{display_name}.ogg'

        if not os.path.isfile(file_path):
            source: BytesIO = await self.get_track_source(id)
            self.write_track_from_source(source, file_path)

        info_dict = {
            'display_name': display_name,
            'source': file_path,
            'url': f'https://open.spotify.com/track/{id}'
        }
        return info_dict
