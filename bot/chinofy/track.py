import math
from pathlib import Path, PurePath
import re
import time
import traceback
import uuid
import ffmpy
from typing import Any, List, Tuple
from librespot.metadata import TrackId

from chinofy import Chinofy
from config import CONFIG
from const import CODEC_MAP, EXT_MAP
from utils import add_to_directory_song_ids, create_download_directory, fix_filename, fmt_seconds, get_directory_song_ids, set_audio_tags, set_music_thumbnail

TRACKS_URL = 'https://api.spotify.com/v1/tracks'

OUTPUT_DEFAULT_PLAYLIST = '{playlist}/{artist} - {song_name}.{ext}'
OUTPUT_DEFAULT_PLAYLIST_EXT = '{playlist}/{playlist_num} - {artist} - {song_name}.{ext}'
OUTPUT_DEFAULT_LIKED_SONGS = 'Liked Songs/{artist} - {song_name}.{ext}'
OUTPUT_DEFAULT_SINGLE = '{artist}/{album}/{artist} - {song_name}.{ext}'
OUTPUT_DEFAULT_ALBUM = '{artist}/{album}/{album_num} - {artist} - {song_name}.{ext}'

def get_song_info(song_id) -> Tuple[List[str], List[Any], str, str, Any, Any, Any, Any, Any, Any, int]: # Chinono: WTF is this long list of Any XDD
    """ Retrieves metadata for downloaded songs """
    print("Fetching track information...")
    (raw, info) = Chinofy.invoke_url(f'{TRACKS_URL}?ids={song_id}&market=from_token')

    if not 'tracks' in info:
        raise ValueError(f'Invalid response from TRACKS_URL:\n{raw}')

    try:
        artists = []
        for data in info['tracks'][0]['artists']:
            artists.append(data['name'])

        album_name = info['tracks'][0]['album']['name']
        name = info['tracks'][0]['name']
        release_year = info['tracks'][0]['album']['release_date'].split('-')[0]
        disc_number = info['tracks'][0]['disc_number']
        track_number = info['tracks'][0]['track_number']
        scraped_song_id = info['tracks'][0]['id']
        is_playable = info['tracks'][0]['is_playable']
        duration_ms = info['tracks'][0]['duration_ms']

        image = info['tracks'][0]['album']['images'][0]
        for i in info['tracks'][0]['album']['images']:
            if i['width'] > image['width']:
                image = i
        image_url = image['url']

        return artists, info['tracks'][0]['artists'], album_name, name, image_url, release_year, disc_number, track_number, scraped_song_id, is_playable, duration_ms
    except Exception as e:
        raise ValueError(f'Failed to parse TRACKS_URL response: {str(e)}\n{raw}')
    
def get_song_genres(rawartists: List[str], track_name: str) -> List[str]:
    if CONFIG['MD_SAVE_GENRES']:
        try:
            genres = []
            for data in rawartists:
                # query artist genres via href, which will be the api url
                with print("Fetching artist information..."):
                    (raw, artistInfo) = Chinofy.invoke_url(f'{data['href']}')
                if CONFIG['MD_ALLGENRES'] and len(artistInfo['genres']) > 0:
                    for genre in artistInfo['genres']:
                        genres.append(genre)
                elif len(artistInfo['genres']) > 0:
                    genres.append(artistInfo['genres'][0])

            if len(genres) == 0:
                print('###    No Genres found for song ' + track_name)
                genres.append('')

            return genres
        except Exception as e:
            raise ValueError(f'Failed to parse GENRES response: {str(e)}\n{raw}')
    else:
        return ['']
    
def get_song_lyrics(song_id: str, file_save: str) -> None:
    raw, lyrics = Chinofy.invoke_url(f'https://spclient.wg.spotify.com/color-lyrics/v2/track/{song_id}')

    if lyrics:
        try:
            formatted_lyrics = lyrics['lyrics']['lines']
        except KeyError:
            raise ValueError(f'Failed to fetch lyrics: {song_id}')
        if(lyrics['lyrics']['syncType'] == "UNSYNCED"):
            with open(file_save, 'w+', encoding='utf-8') as file:
                for line in formatted_lyrics:
                    file.writelines(line['words'] + '\n')
            return
        elif(lyrics['lyrics']['syncType'] == "LINE_SYNCED"):
            with open(file_save, 'w+', encoding='utf-8') as file:
                for line in formatted_lyrics:
                    timestamp = int(line['startTimeMs'])
                    ts_minutes = str(math.floor(timestamp / 60000)).zfill(2)
                    ts_seconds = str(math.floor((timestamp % 60000) / 1000)).zfill(2)
                    ts_millis = str(math.floor(timestamp % 1000))[:2].zfill(2)
                    file.writelines(f'[{ts_minutes}:{ts_seconds}.{ts_millis}]' + line['words'] + '\n')
            return
    raise ValueError(f'Failed to fetch lyrics: {song_id}')

def get_output_template(mode: str) -> str:
    """ Returns the output template for the given mode """
    if CONFIG['OUTPUT']:
        return CONFIG['OUTPUT']
    elif mode == 'single':
        return OUTPUT_DEFAULT_SINGLE
    elif mode == 'album':
        return OUTPUT_DEFAULT_ALBUM
    elif mode == 'playlist':
        return OUTPUT_DEFAULT_PLAYLIST
    elif mode == 'liked':
        return OUTPUT_DEFAULT_LIKED_SONGS
    elif mode == 'extplaylist':
        return OUTPUT_DEFAULT_PLAYLIST_EXT
    else:
        raise ValueError(f'Invalid mode: {mode}')

def download_track(mode: str, track_id: str, extra_keys=None) -> None: # mode can be 'single', 'album', 'playlist', 'liked', 'extplaylist, Im not bothering them for now
    """ Downloads raw song audio from Spotify """

    if extra_keys is None:
        extra_keys = {}

    print("Preparing Download...")

    try:
        output_template = get_output_template(mode)

        (artists, raw_artists, album_name, name, image_url, release_year, disc_number,
         track_number, scraped_song_id, is_playable, duration_ms) = get_song_info(track_id)

        song_name = fix_filename(artists[0]) + ' - ' + fix_filename(name)

        for k in extra_keys:
            output_template = output_template.replace("{"+k+"}", fix_filename(extra_keys[k]))

        ext = EXT_MAP.get(CONFIG['DOWNLOAD_FORMAT'].lower())

        output_template = output_template.replace("{artist}", fix_filename(artists[0]))
        output_template = output_template.replace("{album}", fix_filename(album_name))
        output_template = output_template.replace("{song_name}", fix_filename(name))
        output_template = output_template.replace("{release_year}", fix_filename(release_year))
        output_template = output_template.replace("{disc_number}", fix_filename(disc_number))
        output_template = output_template.replace("{track_number}", fix_filename(track_number))
        output_template = output_template.replace("{id}", fix_filename(scraped_song_id))
        output_template = output_template.replace("{track_id}", fix_filename(track_id))
        output_template = output_template.replace("{ext}", ext)

        filename = PurePath(CONFIG['ROOT_PATH']).joinpath(output_template)
        filedir = PurePath(filename).parent

        filename_temp = filename
        if CONFIG['TEMP_DOWNLOAD_DIR'] != '':
            filename_temp = PurePath(CONFIG['TEMP_DOWNLOAD_DIR']).joinpath(f'zotify_{str(uuid.uuid4())}_{track_id}.{ext}')

        check_name = Path(filename).is_file() and Path(filename).stat().st_size
        check_id = scraped_song_id in get_directory_song_ids(filedir)

        # a song with the same name is installed
        if not check_id and check_name:
            c = len([file for file in Path(filedir).iterdir() if re.search(f'^{filename}_', str(file))]) + 1

            fname = PurePath(PurePath(filename).name).parent
            ext = PurePath(PurePath(filename).name).suffix

            filename = PurePath(filedir).joinpath(f'{fname}_{c}{ext}')

    except Exception as e:
        print('###   SKIPPING SONG - FAILED TO QUERY METADATA   ###')
        print('Track_ID: ' + str(track_id))
        for k in extra_keys:
            print(k + ': ' + str(extra_keys[k]))
        print("\n")
        print(str(e) + "\n")
        print("".join(traceback.TracebackException.from_exception(e).format()) + "\n")

    else:
        try:
            if not is_playable:
                print('\n###   SKIPPING: ' + song_name + ' (SONG IS UNAVAILABLE)   ###' + "\n")
            else:
                if track_id != scraped_song_id:
                    track_id = scraped_song_id
                track = TrackId.from_base62(track_id)
                stream = Chinofy.get_content_stream(track, Chinofy.DOWNLOAD_QUALITY)
                create_download_directory(filedir)
                total_size = stream.input_stream.size


                time_start = time.time()
                downloaded = 0
                with open(filename_temp, 'wb') as file:
                    b = 0
                    while b < 5:
                        data = stream.input_stream.stream().read(CONFIG['CHUNK_SIZE'])
                        file.write(data)
                        downloaded += len(data)
                        b += 1 if data == b'' else 0
                        if CONFIG['DOWNLOAD_REAL_TIME']:
                            delta_real = time.time() - time_start
                            delta_want = (downloaded / total_size) * (duration_ms/1000)
                            if delta_want > delta_real:
                                time.sleep(delta_want - delta_real)

                time_downloaded = time.time()

                genres = get_song_genres(raw_artists, name)

                if(CONFIG['DOWNLOAD_LYRICS']):
                    try:
                        get_song_lyrics(track_id, PurePath(str(filename)[:-3] + "lrc"))
                    except ValueError:
                        print(f"###   Skipping lyrics for {song_name}: lyrics not available   ###")
                convert_audio_format(filename_temp)
                try:
                    set_audio_tags(filename_temp, artists, genres, name, album_name, release_year, disc_number, track_number)
                    set_music_thumbnail(filename_temp, image_url)
                except Exception:
                    print("Unable to write metadata, ensure ffmpeg is installed and added to your PATH.")

                if filename_temp != filename:
                    Path(filename_temp).rename(filename)

                time_finished = time.time()

                print(f'###   Downloaded "{song_name}" to "{Path(filename).relative_to(CONFIG['ROOT_PATH'])}" in {fmt_seconds(time_downloaded - time_start)} (plus {fmt_seconds(time_finished - time_downloaded)} converting)   ###' + "\n")

                # add song id to download directory's .song_ids file
                if not check_id:
                    add_to_directory_song_ids(filedir, scraped_song_id, PurePath(filename).name, artists[0], name)

                if not CONFIG['BULK_WAIT_TIME']:
                    time.sleep(CONFIG['BULK_WAIT_TIME'])
        except Exception as e:
            print('###   SKIPPING: ' + song_name + ' (GENERAL DOWNLOAD ERROR)   ###')
            print('Track_ID: ' + str(track_id))
            for k in extra_keys:
                print(k + ': ' + str(extra_keys[k]))
            print("\n")
            print(str(e) + "\n")
            print("".join(traceback.TracebackException.from_exception(e).format()) + "\n")
            if Path(filename_temp).exists():
                Path(filename_temp).unlink()

def convert_audio_format(filename) -> None:
    """ Converts raw audio into playable file """
    temp_filename = f'{PurePath(filename).parent}.tmp'
    Path(filename).replace(temp_filename)

    download_format = CONFIG['DOWNLOAD_FORMAT'].lower()
    file_codec = CODEC_MAP.get(download_format, 'copy')
    if file_codec != 'copy':
        bitrate = CONFIG['TRANSCODE_BITRATE']
        bitrates = {
            'auto': '320k' if Chinofy.check_premium() else '160k',
            'normal': '96k',
            'high': '160k',
            'very_high': '320k'
        }
        bitrate = bitrates[CONFIG['DOWNLOAD_QUALITY']]
    else:
        bitrate = None

    output_params = ['-c:a', file_codec]
    if bitrate:
        output_params += ['-b:a', bitrate]

    try:
        ff_m = ffmpy.FFmpeg(
            global_options=['-y', '-hide_banner', '-loglevel error'],
            inputs={temp_filename: None},
            outputs={filename: output_params}
        )
        print("Converting file...")
        ff_m.run()

        if Path(temp_filename).exists():
            Path(temp_filename).unlink()

    except ffmpy.FFExecutableNotFoundError:
        print(f'###   SKIPPING {file_codec.upper()} CONVERSION - FFMPEG NOT FOUND   ###')
