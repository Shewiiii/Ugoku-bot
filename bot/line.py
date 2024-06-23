from bs4 import BeautifulSoup
import requests
import re
from pathlib import Path
import shutil
import logging
import os
from apnggif import apnggif
from bot.exceptions import IncorrectURL

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='logs.log'
)


# string from https://www.geeksforgeeks.org/python-check-url-string/
link_grabber = (r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2"
                r",4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+("
                r"?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\""
                r".,<>?«»“”‘’]))")


# Setup the folders
output_path = Path('.') / 'output'

sticker_path = output_path / 'stickers'
sticker_path.mkdir(parents=True, exist_ok=True)

archives_path = output_path / 'archives' / 'stickers'
archives_path.mkdir(parents=True, exist_ok=True)


def get_link(string: str) -> Path:
    return re.findall(
        link_grabber, string
    )[-1][0]


def get_stickerpack(
    link: str | None,
    gif: bool = True
) -> str:
    '''Get every sticker on a LINE Store page.

    Args:
        link: Link of a specific LINE sticker page.

        animated: If true, will save the animated version of the sticker
        if available.

    Returns:
        Create a folder with all the stickers on the page.
    '''
    # Setup
    try:
        request = requests.get(link)
        raw = BeautifulSoup(request.text, features="html.parser")

        # Pack name
        pack_name = raw.find('p', {'data-test': 'sticker-name-title'}).text
    except: # To precise :gura_sleep:
        raise IncorrectURL

    # Remove weird characters
    for c in ['"', '?', ':', '/', '\\', '*', '<', '>', '|']:
        pack_name = pack_name.replace(c, ' ')

    # Setup the folders, path = sticker pack path
    if gif:
        path = sticker_path / 'gif' / pack_name
    else:
        path = sticker_path / 'png' / pack_name

    archive_path = archives_path / pack_name
    path.mkdir(parents=True, exist_ok=True)

    # Get html elements of the stickers
    stickers = raw.find_all(
        'li', {'class': 'FnStickerPreviewItem'}
    )

    # Get sticker type
    sticker_type = stickers[0]['class'][2]

    sticker_count = len(stickers)
    logging.info(f'Downloading {pack_name}, Sticker count: {sticker_count}')

    # Save the stickers
    for i in range(sticker_count):
        link = get_link(stickers[i]['data-preview'])
        neko_arius = requests.get(link).content

        file = path / f'{i+1}.png'
        with open(file, 'wb') as png_file:
            png_file.write(neko_arius)

    # Convert apngs to gif if wanted and if there are
    if gif and sticker_type in ['animation-sticker', 'popup-sticker']:
        for i in range(sticker_count):
            file = path / f'{i+1}.png'
            g_file = path / f'{i+1}.gif'
            apnggif(
                png=file,
                gif=g_file,
                tlevel=255
            )
            os.remove(f'{path}/{i+1}.png')

    # Delete old ARCHIVE if there is
    if os.path.isfile(f'{archive_path}.zip'):
        os.remove(f'{archive_path}.zip')
    # Final zip
    print(path)
    print(path)
    print(path)
    shutil.make_archive(archive_path, 'zip', path)

    return f'{archive_path.absolute()}.zip'


if __name__ == "__main__":
    get_stickerpack('https://store.line.me/stickershop/product/1472670/en')
