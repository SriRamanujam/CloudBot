"""
cryptocurrency.py

A plugin that uses the Cryptonator JSON API to get values for cryptocurrencies.

Created By:
    - Luke Rogers <https://github.com/lukeroge>
Updated by:
    - Sri Ramanujam <https://github.com/sriramanujam>

Special Thanks:
    - https://coinmarketcap-nexuist.rhcloud.com/
    - https://www.cryptonator.com/

License:
    GPL v3
"""
from urllib.parse import quote_plus
from datetime import datetime

import requests

from cloudbot import hook

API_URL = "https://api.cryptonator.com/api/ticker/{}-usd"


# aliases
@hook.command("bitcoin", "btc", autohelp=False)
def bitcoin():
    """ -- Returns current bitcoin value """
    # alias
    return crypto_command("btc")


@hook.command("litecoin", "ltc", autohelp=False)
def litecoin():
    """ -- Returns current litecoin value """
    # alias
    return crypto_command("ltc")


@hook.command("dogecoin", "doge", autohelp=False)
def dogecoin():
    """ -- Returns current dogecoin value """
    # alias
    return crypto_command("doge")


@hook.command("dash", "darkcoin", autohelp=False)
def dash():
    """ -- Returns current darkcoin/dash value """
    # alias
    return crypto_command("dash")


@hook.command("zcash", "zec", autohelp=False)
def zet():
    """ -- Returns current Zcash value """
    # alias
    return crypto_command("zec")


# main command
@hook.command("crypto", "cryptocurrency")
def crypto_command(text):
    """ <ticker> -- Returns current value of a cryptocurrency """
    try:
        encoded = quote_plus(text)
        request = requests.get(API_URL.format(encoded))
        request.raise_for_status()
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
        return "Could not get value: {}".format(e)

    data = request.json()

    if "error" in data and data['error'] != '':
        return "{}.".format(data['error'])

    updated_time = datetime.fromtimestamp(data['timestamp'])
    if (datetime.today() - updated_time).days > 2:
        # the API retains data for old ticker names that are no longer updated
        # in these cases we just return a "not found" message
        return "Currency not found."

    change = float(data['ticker']['change'])
    if change > 0:
        change_str = "\x033{}%\x0f".format(change)
    elif change < 0:
        change_str = "\x035{}%\x0f".format(change)
    else:
        change_str = "{}%".format(change)

    return "1 {} is worth {:,.7f} USD \x03\x02|\x02\x03 {} change".format(data['ticker']['base'].upper(),
                                                                            float(data['ticker']['price']),
                                                                            change_str)
