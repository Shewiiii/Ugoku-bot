from bs4 import BeautifulSoup
import requests
import os
from pathlib import Path

from dotenv import load_dotenv
from deezer import Deezer
from deemix.settings import load as loadSettings

request = requests.get('https://rentry.org/firehawk52#deezer-arls')
raw = BeautifulSoup(request.text, features="html.parser")
url: str = 'https://rentry.org/firehawk52#deezer-arls'


# ----------GLOBAL SETTINGS----------

# env things
load_dotenv()
ARL = str(os.getenv('DEEZER_ARL'))
ARL_COUNTRY = os.getenv('ARL_COUNTRY')

config_path = Path('.') / 'deemix' / 'config'

# Init settings
settings = loadSettings(config_path)

# Init custom arl
custom_arls = {}

# ------------------------------------


def simplified(country: str) -> str:
    try:
        # Japan/にっぽん to Japan
        return country[:country.index('/')]
    except ValueError:
        # France
        return country


def get_rows():
    request = requests.get(url)
    raw = BeautifulSoup(request.text, features="html.parser")

    # 1 because the first (0) one is the Qobuz one
    tbody = raw.find_all('tbody')[1]
    rows = tbody.find_all('tr')

    return rows


def get_countries() -> list:
    rows = get_rows()

    countries = []
    for row in rows:
        country = row.find('img')['alt']
        country = simplified(country)
        if country not in countries:
            countries.append(country)

    return countries


def get_arl(country: str) -> str:
    country = simplified(country)
    rows = get_rows()
    if country == 'Default ARL':
        return os.getenv('DEEZER_ARL')
    else:
        for row in rows:
            c = row.find('img')['alt']
            c = simplified(c)
            if country == c:
                return row.find('code').text


def load_arl(
    user_id: int | None,
    arl: str | None,
    force: bool = False
) -> Deezer | None:
    global custom_arls
    global dz
    if not arl:
        return
    elif arl == ARL:
        return dz
    elif user_id in custom_arls and not force:
        return custom_arls[user_id]
    else:
        # New Deezer instance
        new_dz = Deezer()
        new_dz.login_via_arl(arl)
        custom_arls[user_id] = new_dz
        return new_dz
