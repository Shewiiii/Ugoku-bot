from chinofy import Chinofy
from track import download_track
from utils import fix_filename


ALBUM_URL = 'https://api.spotify.com/v1/albums'
ARTIST_URL = 'https://api.spotify.com/v1/artists'


def get_album_tracks(album_id):
    """ Returns album tracklist """
    songs = []
    offset = 0
    limit = 50

    while True:
        resp = Chinofy.invoke_url_with_params(f'{ALBUM_URL}/{album_id}/tracks', limit=limit, offset=offset)
        offset += limit
        songs.extend(resp['items'])
        if len(resp['items']) < limit:
            break

    return songs


def get_album_name(album_id):
    """ Returns album name """
    (raw, resp) = Chinofy.invoke_url(f'{ALBUM_URL}/{album_id}')
    return resp['artists'][0]['name'], fix_filename(resp['name'])


def get_artist_albums(artist_id):
    """ Returns artist's albums """
    (raw, resp) = Chinofy.invoke_url(f'{ARTIST_URL}/{artist_id}/albums?include_groups=album%2Csingle')
    # Return a list each album's id
    album_ids = [resp['items'][i]['id'] for i in range(len(resp['items']))]
    # Recursive requests to get all albums including singles an EPs
    while resp['next'] is not None:
        (raw, resp) = Chinofy.invoke_url(resp['next'])
        album_ids.extend([resp['items'][i]['id'] for i in range(len(resp['items']))])

    return album_ids


def download_album(album):
    """ Downloads songs from an album """
    artist, album_name = get_album_name(album)
    tracks = get_album_tracks(album)
    for n, track in enumerate(tracks, 1):
        download_track('album', track['id'], extra_keys={'album_num': str(n).zfill(2), 'artist': artist, 'album': album_name, 'album_id': album})


def download_artist_albums(artist):
    """ Downloads albums of an artist """
    albums = get_artist_albums(artist)
    for album_id in albums:
        download_album(album_id)