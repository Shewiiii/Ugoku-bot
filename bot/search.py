from deezer import API
import requests
import re


api = API(
    headers={
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64)"
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/79.0.3945.130 Safari/537.36"
            )
    },
    session=requests.Session()
)
# string from https://www.geeksforgeeks.org/python-check-url-string/
link_grabber = (r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2"
                r",4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+("
                r"?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\""
                r".,<>?«»“”‘’]))")


def get_song_url(query: str) -> str | None:
    search = api.search_track(query)
    if not search['data']:
        return None
    return search['data'][0]['link']


def is_url(string: str, sites: list) -> bool:
    search = re.findall(link_grabber, string)
    if len(search) == 0:
        return False
    for site in sites:
        if site in search[0][0]:
            return True
    return False
