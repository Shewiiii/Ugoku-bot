import subprocess
from datetime import datetime
import pandas as pd
from pathlib import Path, WindowsPath
import os
import shutil


class SpotifyDownloader:
    # def __init__(self) -> None:
    # pass

    def from_url(self, url: str) -> list[dict]:
        id: str = str(datetime.timestamp(datetime.now())).replace('.', '')
        path = Path('.').absolute() / 'output' / 'vc_songs' / 'OGG 320' / id
        subprocess.run(
            f'zotify {url} --root-path "{path}" --output "{path}"/''"{artist} - {song_name}.{ext}"',
            shell=True
        )
        df: pd.DataFrame = pd.read_csv(
            path / '.song_ids',
            sep="	",
            header=None,
            names=['id', 'date', 'artist', 'title', 'file']
        )
        all_data = []
        for file, artist, title in zip(df['file'], df['artist'], df['title']):
            all_data.append(
                {
                    'path': path / file,
                    'display_name': f'{artist} - {title}'
                }
            )

        return all_data

    def from_query(self, query: str) -> None:
        raise NotImplementedError

    def clean(self) -> None:
        folder = Path('.').absolute() / 'output' / 'vc_songs' / 'OGG 320'

        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))
