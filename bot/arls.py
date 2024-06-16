from bs4 import BeautifulSoup
import requests
import discord
import os

request = requests.get('https://rentry.org/firehawk52#deezer-arls')
raw = BeautifulSoup(request.text, features="html.parser")
url: str = 'https://rentry.org/firehawk52#deezer-arls'


def simplified(country: str) -> str:
    try:
        # Japan/にっぽん to Japan
        return country[:country.index('/')]
    except:
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
