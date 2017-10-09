"""
google.py

Originally for RoboCop 2, a replacement after Google's deprecation of Google Web Search API
Module requires a Google Custom Search API key and a Custom Search Engine ID in order to function.

Created By:
    - Foxlet <http://furcode.tk/>

Modified by:
    - Sri Ramanujam <http://github.com/sriramanujam>

License:
    GNU General Public License (Version 3)
"""



import requests

from cloudbot import hook
from cloudbot.util import formatting, filesize

API_CS = 'https://www.googleapis.com/customsearch/v1'


@hook.on_start()
def load_api(bot):
    global dev_key
    global cx

    dev_key = bot.config.get("api_keys", {}).get("google_dev_key", None)
    cx = bot.config.get("api_keys", {}).get("google_cse_id", None)

@hook.command('g', 'google')
def gse(text):
    """<query> -- Returns first Google search result for <query>."""
    if not dev_key:
        return "This command requires a Google Developers Console API key."
    if not cx:
        return "This command requires a custom Google Search Engine ID."

    parsed = requests.get(API_CS, params={"cx": cx, "q": text, "key": dev_key}).json()

    try:
        result = parsed['items'][0]
    except KeyError:
        return "No results found."

    title = formatting.truncate_str(result['title'], 60)
    content = result['snippet']

    if not content:
        content = "No description available."
    else:
        content = formatting.truncate_str(content.replace('\n', ''), 240)

    return u'\x02Google search result\x02 for \x02{}\x02 \x02\x0312|\x03\x02 {} · {} \x02\x0312|\x03\x02 {}'.format(
            text, title, content, result['link'])


@hook.command('gis', 'googleimage')
def gse_gis(text):
    """<query> -- Returns first Google Images result for <query>."""
    if not dev_key:
        return "This command requires a Google Developers Console API key."
    if not cx:
        return "This command requires a custom Google Search Engine ID."

    parsed = requests.get(API_CS, params={"cx": cx, "q": text, "searchType": "image", "key": dev_key}).json()

    try:
        result = parsed['items'][0]
    except KeyError:
        return "No results found."

    return u'\x02Google image result\x02 for \x02{}\x02 \x02\x0312|\x03\x02 {}'.format(text, result['link'])

