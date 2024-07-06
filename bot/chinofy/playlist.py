from track import download_track
from chinofy import Chinofy

PLAYLISTS_URL = 'https://api.spotify.com/v1/playlists'


def get_playlist_songs(playlist_id):
    """ returns list of songs in a playlist """
    songs = []
    offset = 0
    limit = 100

    while True:
        resp = Chinofy.invoke_url_with_params(f'{PLAYLISTS_URL}/{playlist_id}/tracks', limit=limit, offset=offset)
        offset += limit
        songs.extend(resp['items'])
        if len(resp['items']) < limit:
            break

    return songs


def get_playlist_info(playlist_id):
    """ Returns information scraped from playlist """
    (raw, resp) = Chinofy.invoke_url(f'{PLAYLISTS_URL}/{playlist_id}?fields=name,owner(display_name)&market=from_token')
    return resp['name'].strip(), resp['owner']['display_name'].strip()


def download_playlist(playlist):
    """Downloads all the songs from a playlist"""

    playlist_songs = [song for song in get_playlist_songs(playlist['id']) if song['track'] is not None and song['track']['id']]
    enum = 1
    for song in playlist_songs:
        download_track('extplaylist', song['track']['id'], extra_keys={'playlist': playlist['name'], 'playlist_num': str(enum).zfill(2)})
        enum += 1