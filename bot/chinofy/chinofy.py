""" This is a modified version of the original Zotify codebase.
I modified it so that it can be used as a library for the discord bot.
Functions that are not needed are removed.
Original codebase can be found here:
https://github.com/zotify-dev/zotify """

import os
from dotenv import load_dotenv
from librespot.core import Session
from librespot.audio.decoders import VorbisOnlyAudioQuality
from librespot.audio.decoders import AudioQuality
from librespot.metadata import TrackId
import requests
import json
import time

from config import CONFIG

""" URLs to interact with Spotify API """
FOLLOWED_ARTISTS_URL = 'https://api.spotify.com/v1/me/following?type=artist'

TRACK_STATS_URL = 'https://api.spotify.com/v1/audio-features/'
SAVED_TRACKS_URL = 'https://api.spotify.com/v1/me/tracks'


# Im renaming the class from Zotify to Chinofy because why not XD
class Chinofy:    
    SESSION: Session = None

    def __init__(self, args=None):
        Chinofy.login(args)
        self.quality_options = {
            'auto': AudioQuality.VERY_HIGH if self.check_premium() else AudioQuality.HIGH,
            'normal': AudioQuality.NORMAL,
            'high': AudioQuality.HIGH,
            'very_high': AudioQuality.VERY_HIGH
        }
        Chinofy.DOWNLOAD_QUALITY = self.quality_options[CONFIG['DOWNLOAD_QUALITY']]

    @classmethod
    def login(cls, args):
        """ Authenticates with Spotify and saves credentials to a file """

        load_dotenv()
        username = os.getenv('SPOTIFY_USERNAME')
        password = os.getenv('SPOTIFY_PASSWORD')

        conf = Session.Configuration.Builder().set_store_credentials(False).build()
        cls.SESSION = Session.Builder(conf).user_pass(username, password).create()

    @classmethod
    def get_content_stream(cls, content_id, quality):
        return cls.SESSION.content_feeder().load(content_id, VorbisOnlyAudioQuality(quality), False, None)

    @classmethod
    def __get_auth_token(cls):
        return cls.SESSION.tokens().get_token(
            'user-read-email', 'playlist-read-private', 'user-library-read', 'user-follow-read'
        ).access_token

    @classmethod
    def get_auth_header(cls):
        return {
            'Authorization': f'Bearer {cls.__get_auth_token()}',
            'Accept-Language': 'en',
            'Accept': 'application/json',
            'app-platform': 'WebPlayer'
        }

    @classmethod
    def get_auth_header_and_params(cls, limit, offset):
        return {
            'Authorization': f'Bearer {cls.__get_auth_token()}',
            'Accept-Language': 'en',
            'Accept': 'application/json',
            'app-platform': 'WebPlayer'
        }, {'limit': limit, 'offset': offset}

    @classmethod
    def invoke_url_with_params(cls, url, limit, offset, **kwargs):
        headers, params = cls.get_auth_header_and_params(limit=limit, offset=offset)
        params.update(kwargs)
        return requests.get(url, headers=headers, params=params).json()

    @classmethod
    def invoke_url(cls, url, tryCount=0):
        # we need to import that here, otherwise we will get circular imports!
        from zotify.termoutput import Printer, PrintChannel
        headers = cls.get_auth_header()
        response = requests.get(url, headers=headers)
        responsetext = response.text
        try:
            responsejson = response.json()
        except json.decoder.JSONDecodeError:
            responsejson = {"error": {"status": "unknown", "message": "received an empty response"}}

        if not responsejson or 'error' in responsejson:
            if tryCount < (CONFIG['RETRY_ATTEMPTS'] - 1):
                Printer.print(PrintChannel.WARNINGS, f"Spotify API Error (try {tryCount + 1}) ({responsejson['error']['status']}): {responsejson['error']['message']}")
                time.sleep(5)
                return cls.invoke_url(url, tryCount + 1)

            Printer.print(PrintChannel.API_ERRORS, f"Spotify API Error ({responsejson['error']['status']}): {responsejson['error']['message']}")

        return responsetext, responsejson

    @classmethod
    def check_premium(cls) -> bool:
        """ If user has spotify premium return true """
        return (cls.SESSION.get_user_attribute('type') == 'premium')
