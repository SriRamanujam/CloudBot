import requests

from sqlalchemy import Table, Column, PrimaryKeyConstraint, String

from cloudbot import hook
from cloudbot.util import web, database


class APIError(Exception):
    pass

# Define some constants
google_base = 'https://maps.googleapis.com/maps/api/'
geocode_api = google_base + 'geocode/json'

forecast_io_api = "https://api.forecast.io/forecast/{}/{}?units=us"

table = Table(
    "weather",
    database.metadata,
    Column('nick', String(255)),
    Column('location', String(255)),
    PrimaryKeyConstraint('nick')
)

# Change this to a ccTLD code (eg. uk, nz) to make results more targeted towards that specific country.
# <https://developers.google.com/maps/documentation/geocoding/#RegionCodes>
bias = None

w_cache = []

def check_status(status):
    """
    A little helper function that checks an API error code and returns a nice message.
    Returns None if no errors found
    """
    if status == 'REQUEST_DENIED':
        return 'The geocode API is off in the Google Developers Console.'
    elif status == 'ZERO_RESULTS':
        return 'No results found.'
    elif status == 'OVER_QUERY_LIMIT':
        return 'The geocode API quota has run out.'
    elif status == 'UNKNOWN_ERROR':
        return 'Unknown Error.'
    elif status == 'INVALID_REQUEST':
        return 'Invalid Request.'
    elif status == 'OK':
        return None


def find_location(location):
    """
    Takes a location as a string, and returns a dict of data
    :param location: string
    :return: dict, string
    """
    params = {"address": location, "key": dev_key}
    if bias:
        params['region'] = bias

    json = requests.get(geocode_api, params=params).json()

    error = check_status(json['status'])
    if error:
        raise APIError(error)

    return json['results'][0]['geometry']['location'], json['results'][0]['formatted_address']


def _parse_weather_output(weather_data, location):
    w_dict = {}

    w_dict['location'] = location
    w_dict['summary'] = weather_data['currently']['summary']
    w_dict['humidity'] = weather_data['currently']['humidity'] * 100
    w_dict['precip_chance'] = weather_data['currently']['precipProbability'] * 100
    w_dict['daily_summary'] = weather_data['daily']['summary']

    ## Build a string that has both measurement systems.
    w_dict['temp_f'] = round(weather_data['currently']['temperature'], 2)
    w_dict['temp_c'] = round((weather_data['currently']['temperature'] - 32) * 5/9, 2)
    w_dict['feelslike_f'] = round(weather_data['currently']['apparentTemperature'], 2)
    w_dict['feelslike_c'] = round((weather_data['currently']['apparentTemperature'] - 32) * 5/9, 2)
    w_dict['windspeed_mph'] = round(weather_data['currently']['windSpeed'], 2)
    w_dict['windspeed_ms'] = round(weather_data['currently']['windSpeed'] * .44704, 2)

    return "Current weather in \x02{location}\x02 \x02\x033|\x03\x02 {summary}, {temp_f}°F ({temp_c}°C) feels like {feelslike_f}°F ({feelslike_c}°C), {humidity}% humidity, wind speed {windspeed_mph} mph ({windspeed_ms} m/s), {precip_chance}% chance of precipitation. Today's forecast: {daily_summary}".format(**w_dict)


def load_weather_db(db):
    global w_cache
    w_cache = []
    for row in db.execute(table.select()):
        w_cache.append((row['nick'], row['location']))


@hook.on_start
def load_cache(bot, db):
    """ Loads API keys """
    global dev_key, forecast_io_key
    dev_key = bot.config.get("api_keys", {}).get("google_dev_key", None)
    forecast_io_key = bot.config.get("api_keys", {}).get("forecast_io", None)
    load_weather_db(db)


def get_saved_weather(nick):
    global w_cache
    w_loc = [row[1] for row in w_cache if nick.lower() == row[0]]
    return w_loc


@hook.command("weather", "w", autohelp=False)
def weather(text, reply, bot, db, nick, notice):
    """weather <location> --save. If you pass --save, the location will be saved to the database. You can get your weather for your saved location by passing .weather without any parameters.
    """
    if not forecast_io_key:
        return "This command requires a forecast.io API key."
    if not dev_key:
        return "This command requires a Google Developers Console API key."

    should_save = text.endswith(' --save')

    if not text:
        # try to find nick in database
        location = get_saved_weather(nick)
        if not location:
            notice(weather.__doc__)
            return
    else:
        location = text.split(' --')[0]

    # use find_location to get location data from the user input
    try:
        location_data, formatted_address = find_location(location)
    except APIError as e:
        return e

    formatted_location = "{lat},{lng}".format(**location_data)

    url = forecast_io_api.format(forecast_io_key, formatted_location)
    response = requests.get(url).json()

    reply(_parse_weather_output(response, formatted_address))

    if should_save:
        db.execute('insert into weather(nick, location) values (:nick, :location) '
                'on conflict(nick) do update set location = EXCLUDED.location',
                {'nick': nick.lower(), 'location': formatted_address})
        db.commit()
        load_weather_db(db)
        notice('Location {} saved'.format(formatted_address))

