from bs4 import BeautifulSoup
import requests
import re
from pathlib import Path
import shutil
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='logs.log',
)

link_grabber = (r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2"
                r",4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+("
                r"?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\""
                r".,<>?«»“”‘’]))")
# string from https://www.geeksforgeeks.org/python-check-url-string/


def get_link(string: str) -> Path:
    return re.findall(
        link_grabber, string
    )[-1][0]


def get_stickers(
    link: str,
) -> None:
    '''Get every sticker on a LINE Store page.

    Args:
        link: Link of a specific LINE sticker page.

        animated: If true, will save the animated version of the sticker
        if available.

    Returns:
        Create a folder with all the stickers on the page.
    '''
    # Setup
    request = requests.get(link)
    raw = BeautifulSoup(request.text, features="html.parser")

    # Pack name
    pack_name = raw.find('p', {'data-test': 'sticker-name-title'}).text

    # Remove weird characters
    for c in ['"', '?', ':', '/', '\\', '*', '<', '>', '|']:
        pack_name = pack_name.replace(c, ' ')

    # Setup the folders
    path = Path(f"output/downloads/{pack_name}")
    path.mkdir(parents=True, exist_ok=True)
    archives_path = Path(f"output/archives")
    archives_path.mkdir(parents=True, exist_ok=True)

    stickers = raw.find_all(
        'li', {'class': 'FnStickerPreviewItem'}
    )
    sticker_count = len(stickers)
    logging.info(f'Downloading {pack_name}, Sticker count: {sticker_count}')

    # Save the stickers
    for i in range(sticker_count):
        link = get_link(stickers[i]['data-preview'])
        image = requests.get(link).content

        open(f'{path}\\{i+1}.png', 'wb').write(image)
        logging.info(f'Downloaded: {link}')

    shutil.make_archive(archives_path / pack_name, 'zip', path)

    return (archives_path / f'{pack_name}.zip').absolute()
