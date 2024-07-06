from pathlib import PurePath, Path
import time
from typing import Optional, Tuple

from librespot.metadata import EpisodeId

from config import CONFIG
from utils import create_download_directory, fix_filename
from chinofy import Chinofy


EPISODE_INFO_URL = 'https://api.spotify.com/v1/episodes'
SHOWS_URL = 'https://api.spotify.com/v1/shows'


def get_episode_info(episode_id_str) -> Tuple[Optional[str], Optional[str]]:
    print("Fetching episode information...")
    (raw, info) = Chinofy.invoke_url(f'{EPISODE_INFO_URL}/{episode_id_str}')
    if not info:
        print("###   INVALID EPISODE ID   ###")
    duration_ms = info['duration_ms']
    if 'error' in info:
        return None, None
    return fix_filename(info['show']['name']), duration_ms, fix_filename(info['name'])


def get_show_episodes(show_id_str) -> list:
    episodes = []
    offset = 0
    limit = 50

    print("Fetching episodes...")
    while True:
        resp = Chinofy.invoke_url_with_params(
            f'{SHOWS_URL}/{show_id_str}/episodes', limit=limit, offset=offset)
        offset += limit
        for episode in resp['items']:
            episodes.append(episode['id'])
        if len(resp['items']) < limit:
            break

    return episodes


def download_podcast_directly(url, filename):
    import functools
    import shutil
    import requests
    from tqdm.auto import tqdm

    r = requests.get(url, stream=True, allow_redirects=True)
    if r.status_code != 200:
        r.raise_for_status()  # Will only raise for 4xx codes, so...
        raise RuntimeError(
            f"Request to {url} returned status code {r.status_code}")
    file_size = int(r.headers.get('Content-Length', 0))

    path = Path(filename).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    desc = "(Unknown total file size)" if file_size == 0 else ""
    r.raw.read = functools.partial(
        r.raw.read, decode_content=True)  # Decompress if needed
    with tqdm.wrapattr(r.raw, "read", total=file_size, desc=desc) as r_raw:
        with path.open("wb") as f:
            shutil.copyfileobj(r_raw, f)

    return path


def download_episode(episode_id) -> None:
    podcast_name, duration_ms, episode_name = get_episode_info(episode_id)
    extra_paths = podcast_name + '/'
    print("Preparing download...")

    if podcast_name is None:
        print('###   SKIPPING: (EPISODE NOT FOUND)   ###')
    else:
        filename = podcast_name + ' - ' + episode_name

        resp = Chinofy.invoke_url(
            'https://api-partner.spotify.com/pathfinder/v1/query?operationName=getEpisode&variables={"uri":"spotify:episode:' + episode_id + '"}&extensions={"persistedQuery":{"version":1,"sha256Hash":"224ba0fd89fcfdfb3a15fa2d82a6112d3f4e2ac88fba5c6713de04d1b72cf482"}}')[1]["data"]["episode"]
        direct_download_url = resp["audio"]["items"][-1]["url"]

        download_directory = PurePath(CONFIG['ROOT_PODCAST_PATH']).joinpath(extra_paths)
        # download_directory = os.path.realpath(download_directory)
        create_download_directory(download_directory)

        if "anon-podcast.scdn.co" in direct_download_url or "audio_preview_url" not in resp:
            episode_id = EpisodeId.from_base62(episode_id)
            stream = Chinofy.get_content_stream(
                episode_id, Chinofy.DOWNLOAD_QUALITY)

            total_size = stream.input_stream.size

            filepath = PurePath(download_directory).joinpath(f"{filename}.ogg")

            time_start = time.time()
            downloaded = 0
            with open(filepath, 'wb') as file:
                while True:
                #for _ in range(int(total_size / Chinofy.CONFIG.get_chunk_size()) + 2):
                    data = stream.input_stream.stream().read(CONFIG['CHUNK_SIZE'])
                    file.write(data)
                    downloaded += len(data)
                    if data == b'':
                        break
                    if CONFIG['DOWNLOAD_REAL_TIME']:
                        delta_real = time.time() - time_start
                        delta_want = (downloaded / total_size) * (duration_ms/1000)
                        if delta_want > delta_real:
                            time.sleep(delta_want - delta_real)
        else:
            filepath = PurePath(download_directory).joinpath(f"{filename}.mp3")
            download_podcast_directly(direct_download_url, filepath)