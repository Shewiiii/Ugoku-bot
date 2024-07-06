from album import download_album, download_artist_albums
from podcast import download_episode, get_show_episodes
from playlist import get_playlist_info, get_playlist_songs
from track import download_track
from utils import regex_input_for_urls
from chinofy import Chinofy

SEARCH_URL = 'https://api.spotify.com/v1/search'

def download_from_urls(urls: list[str]) -> bool:
    """ Downloads from a list of urls """
    download = False

    for spotify_url in urls:
        track_id, album_id, playlist_id, episode_id, show_id, artist_id = regex_input_for_urls(spotify_url)

        if track_id is not None:
            download = True
            download_track('single', track_id)             
        elif artist_id is not None:
            download = True
            download_artist_albums(artist_id)
        elif album_id is not None:
            download = True
            download_album(album_id)
        elif playlist_id is not None:
            download = True
            playlist_songs = get_playlist_songs(playlist_id)
            name, _ = get_playlist_info(playlist_id)
            enum = 1
            char_num = len(str(len(playlist_songs)))
            for song in playlist_songs:
                if not song['track']['name'] or not song['track']['id']:
                    print('###   SKIPPING:  SONG DOES NOT EXIST ANYMORE   ###' + "\n")
                else:
                    if song['track']['type'] == "episode": # Playlist item is a podcast episode
                        download_episode(song['track']['id'])
                    else:
                        download_track('playlist', song['track']['id'], extra_keys=
                        {
                            'playlist_song_name': song['track']['name'],
                            'playlist': name,
                            'playlist_num': str(enum).zfill(char_num),
                            'playlist_id': playlist_id,
                            'playlist_track_id': song['track']['id']
                        })
                    enum += 1
        elif episode_id is not None:
            download = True
            download_episode(episode_id)
        elif show_id is not None:
            download = True
            for episode in get_show_episodes(show_id):
                download_episode(episode)
        

    return download

# Chinofy()
# download_from_urls(["https://open.spotify.com/track/57Bv7VXc2IHBfznHUoOTOM?si=2ca5cba195164a4f"]) # Testing the function
# download_from_urls(["https://open.spotify.com/album/13xiFFc0cBN88k8Nb3X9oR?si=Pp8hpC3-RoSezbRwI_lUmQ"]) # for album
# download_from_urls(["https://open.spotify.com/episode/72MGWsCUCg8PkuoAlzYdoA?si=ed7ad39fdfee4900"]) # for episode

def search(search_term: str, limit: int = 10, offset: int = 0, type: list = ['track','album','artist','playlist']):
    """ Searches download server's API for relevant data """

    # Parse args
    allowed_types = ['track', 'playlist', 'album', 'artist']
    if not type <= allowed_types:      # if type is not a subset of allowed_types
        raise ValueError('Parameters passed after type option must be from this list:\n{}'.
            format('\n'.join(allowed_types)))

    if not search_term:
        raise ValueError("Invalid query.")

    """ Returns search results from Spotify API """
    # It just prints all the data for now, I will implement a way to return the data later
    params = {
        'q': search_term,
        'type': ','.join(type),
        'limit': str(limit),
        'offset': str(offset)
    }
    resp = Chinofy.invoke_url_with_params(SEARCH_URL, **params)

    counter = 1
    dics = []

    """ Tracks section """
    total_tracks = 0
    if 'track' in type:
        tracks = resp['tracks']['items']
        if len(tracks) > 0:
            print('###  TRACKS  ###')
            track_data = []
            for track in tracks:
                if track['explicit']:
                    explicit = '[E]'
                else:
                    explicit = ''

                track_data.append([counter, f'{track['name']} {explicit}',
                                  ','.join([artist['name'] for artist in track['artists']])])
                dics.append({
                    'id': track['id'],
                    'name': track['name'],
                    'type': 'track',
                })

                counter += 1
            total_tracks = counter - 1

    """ Albums section """
    total_albums = 0
    if 'album' in type:
        albums = resp['albums']['items']
        if len(albums) > 0:
            print('###  ALBUMS  ###')
            album_data = []
            for album in albums:
                album_data.append([counter, album['name'],
                                  ','.join([artist['name'] for artist in album['artists']])])
                dics.append({
                    'id': album['id'],
                    'name': album['name'],
                    'type': 'album',
                })

                counter += 1
            total_albums = counter - total_tracks - 1

    """ Artist section """
    total_artists = 0
    if 'artist' in type:
        artists = resp['artists']['items']
        if len(artists) > 0:
            print('###  ARTISTS  ###')
            artist_data = []
            for artist in artists:
                artist_data.append([counter, artist['name']])
                dics.append({
                    'id': artist['id'],
                    'name': artist['name'],
                    'type': 'artist',
                })
                counter += 1
            total_artists = counter - total_tracks - total_albums - 1

    """ Playlist section """
    total_playlists = 0
    if 'playlist' in type:
        playlists = resp['playlists']['items']
        if len(playlists) > 0:
            print('###  PLAYLISTS  ###')
            playlist_data = []
            for playlist in playlists:
                playlist_data.append(
                    [counter, playlist['name'], playlist['owner']['display_name']])
                dics.append({
                    'id': playlist['id'],
                    'name': playlist['name'],
                    'type': 'playlist',
                })
                counter += 1
            total_playlists = counter - total_artists - total_tracks - total_albums - 1

    if total_tracks + total_albums + total_artists + total_playlists == 0:
        print('NO RESULTS FOUND - EXITING...')
        return
    return (dics)
    
# Chinofy()
# print(search("pikasonic")) # Testing the function