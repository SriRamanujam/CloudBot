"""
recipe.py

Ask the internet what you should make for dinner.

Created By:
    - Luke Rogers <https://github.com/lukeroge>
Heavily modified by:
    - Sri Ramanujam <https://github.com/sriramanujam>

License:
    GPL v3
"""

import requests
import bs4

from cloudbot import hook
from cloudbot.util import web

WTFSIMFD_URL = "http://whatthefuckshouldimakefordinner.com"
VEG_SUFFIX = "/veg.php"

# set this to true to censor this plugin!
CENSOR = True

class ParseError(Exception):
    pass

# inspired by http://whatthefuckshouldimakefordinner.com/ <3
@hook.command("dinner", "wtfsimfd", autohelp=False)
def dinner(text):
    """<veg> - TELLS YOU WHAT THE F**K YOU SHOULD MAKE FOR DINNER"""
    try:
        request = requests.get(WTFSIMFD_URL + (VEG_SUFFIX if text == 'veg' else ''))
        request.raise_for_status()
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
        return "I CAN'T GET A DAMN RECIPE: {}".format(e).upper()

    url = request.url

    try:
        soup = bs4.BeautifulSoup(request.text)
        divs = soup.find_all('dl')
        intro = divs[0].text.strip()
        recipe = divs[1].text.strip()
        url = divs[1].a['href']
        text = (intro + ' ' + recipe).upper()
    except ParseError as e:
        return "I CAN'T READ THE F**KING RECIPE: {}".format(e).upper()

    if CENSOR:
        text = text.replace("FUCK", "F**K")

    return "{} - {}".format(text, web.try_shorten(url))
