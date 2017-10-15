import requests

from cloudbot import hook
from cloudbot.util import web


class APIError(Exception):
    pass

# Define some constants
google_base = 'https://maps.googleapis.com/maps/api/'
geocode_api = google_base + 'geocode/json'

forecast_io_api = "https://api.forecast.io/forecast/{}/{}?units={}"

# Change this to a ccTLD code (eg. uk, nz) to make results more targeted towards that specific country.
# <https://developers.google.com/maps/documentation/geocoding/#RegionCodes>
bias = None


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


@hook.on_start
def on_start(bot):
    """ Loads API keys """
    global dev_key, forecast_io_key
    dev_key = bot.config.get("api_keys", {}).get("google_dev_key", None)
    forecast_io_key = bot.config.get("api_keys", {}).get("forecast_io", None)


@hook.command("weather", "w", autohelp=False)
def weather(text, reply):
    """weather <location>:<units>. Units can be one of [us, si, ca, uk, both]. Defaults to us"""
    if not forecast_io_key:
        return "This command requires a forecast.io API key."
    if not dev_key:
        return "This command requires a Google Developers Console API key."

    if not text:
        return "Saved weather coming soon! Hold on to your butts."
    else:
        parts = text.split(':')
        location, *measure_type = parts

    if measure_type and measure_type[0] not in ['us', 'si', 'ca', 'uk', 'both']:
        return "Invalid units. Please pick from one of [us, si, ca, uk, both]."

    # use find_location to get location data from the user input
    try:
        location_data, formatted_address = find_location(location)
    except APIError as e:
        return e

    formatted_location = "{lat},{lng}".format(**location_data)

    url = forecast_io_api.format(forecast_io_key, formatted_location,
            measure_type[0] if measure_type else 'us')
    response = requests.get(url).json()

    reply(_parse_weather_output(response, formatted_address))

