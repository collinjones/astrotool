from pprint import pprint

from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta, date
from darksky import forecast
from opencage.geocoder import OpenCageGeocode
from datetime import datetime as dt
import calendar, requests, api_keys, socket, pylunar, almanac, utilities as u
import timezonefinder, pytz
import requests

geocoder = OpenCageGeocode(api_keys.open_cage_apikey)

app = Flask(__name__)
app.secret_key = "hello"
app.permanent_session_lifetime = timedelta(days=5)

# Setup variables
default_loc = "Broomfield, Colorado"  # Default location
today = dt.today()  # Current date
current_hour = today.hour
ts = int(dt.now().timestamp())  # Time stamp of current day


@app.route("/", methods=['POST', 'GET'])
def astro_forecast():
    """
    main forecast function

    :return: render_template("index.html", **context)
    """
    context = set_up_forecast()
    return render_template("forecast.html", **context)


def create_hourly_dict(ds_forecast):
    """
    Returns a dictionary out of hourly forecast data

    :param ds_forecast: DARKSKY API RESULTS
    :return: DICTIONARY of hourly forecast data
    """
    # Create empty dictionary
    hourly_dict = {}

    # Create a 24 hour dictionary starting from the current hour using the time as the keys
    for x in range(0, 24):
        dt_object = dt.fromtimestamp(ds_forecast.hourly[x].time)
        hourly_dict[str(dt_object)] = ds_forecast.hourly[x]

    return hourly_dict


def get_city_from_locational_data(loc_data):
    """
    Takes in the results of a GEOCODE API call and returns the correct city name.
    Sometimes, the result is listed as a town, city, or suburb. This logic will always return something correctly.

    :param loc_data: results of a GEOCODE API call
    :return: STRING name of city, town, or suburb
    """

    try:
        if 'city' in loc_data[0]['components']:
            return loc_data[0]['components']['city']
        elif 'suburb' in loc_data[0]['components']:
            return loc_data[0]['components']['suburb']
        else:
            return loc_data[0]['components']['town']

    except ValueError:
        return "No match"


def get_user_locational_data():
    """
    Asks users for their location via IP, City / State, or latitude / longitude
    Returns the geocode api results based on their location

    :return: GEOCODE API RESULTS
    """
    if request.form['state'] and request.form['city']:
        return geocoder.geocode(request.form['city'] + ", " + request.form['state']), \
               request.form['city'] + ", " + request.form['state']

    if request.form['lat'] and request.form['lng']:
        geo_data = geocoder.reverse_geocode(request.form['lat'], request.form['lng'])
        return geo_data, get_city_from_locational_data(geo_data) + ", " + geo_data[0]['components']['state']


def set_up_forecast():
    """
    Sets up the forecast table
    Returns the context for the html
    :return:
    """
    # Determine if city/state or lat/lng, return loc data and location
    if request.form:
        geocoder_data, loc = get_user_locational_data()
    else:
        loc = default_loc
        geocoder_data = geocoder.geocode(default_loc)

    # tz = pytz.timezone(geocoder_data[0]['annotations']['timezone']['name'])
    # tz_now = dt.now(tz)

    lat = geocoder_data[0]['geometry']['lat']
    lng = geocoder_data[0]['geometry']['lng']

    # Get darksky data
    # darksky_data = forecast(key=api_keys.darksky_apikey, latitude=geocoder_data[0]['geometry']['lat'],
    #                         longitude=geocoder_data[0]['geometry']['lng'])
    darksky_data = get_weather_data(lat, lng, 'midnight')

    print(darksky_data.hourly[0].time)

    # Get darksky hourly dictionary
    hourly_forecast = create_hourly_dict(darksky_data)

    # Get moon phase (english)
    moon_phase = u.moon_phase(darksky_data['daily']['data'][0]['moonPhase'])

    # Get a list of wind directions and ids (for html)
    wind_direction_ids = []
    wind_directions = []
    hours = []
    for key in hourly_forecast:
        wind_directions.append(u.wind_direction(hourly_forecast[key].windBearing))
        wind_direction_ids.append("direction" + key[11:13])
        hours.append(key[11:13])

    # Get moon rise / set times
    lat_dms = u.decdeg2dms(geocoder_data[0]['geometry']['lat'])
    lng_dms = u.decdeg2dms(geocoder_data[0]['geometry']['lng'])
    moon_obj = pylunar.MoonInfo(lat_dms, lng_dms)
    lunar_set_rise = pylunar.MoonInfo.rise_set_times(moon_obj, "UTC-07:00")

    # Return the context for flask html variables as a dictionary
    return {
        'geocode': geocoder_data,
        'darksky': hourly_forecast,
        'wind_directions': wind_directions,
        'wind_direction_ids': wind_direction_ids,
        'date': u.get_current_date(),
        'location': loc,
        'phase': moon_obj.phase_name().replace("_", " "),
        'lunar_times': lunar_set_rise,
        'hours': hours
    }


def get_weather_data(lat, lng, request_type='current'):
    """
    Takes in lat, lng, and request type and
        return a darksky api json dictionary.

    :param lat:
    :param lng:
    :param request_type:
    :return:
    """

    response = None

    if request_type == 'current':
        response = requests.get(
            f"https://api.darksky.net/forecast/{api_keys.darksky_apikey}/{lat},{lng}?exclude=currently,minutely,daily,flags&units=us")

    elif request_type == 'midnight':
        # Create a datetime object set at midnight (default settings)
        response = requests.get(f"https://api.darksky.net/forecast/{api_keys.darksky_apikey}/{lat},{lng},{ts}?exclude=currently,minutely,daily,flags&units=us")
        return format_midnight_forcast(response)

    elif request_type == 'midday':
        return format_midday_forecast(lat, lng)


def format_midnight_forcast(response):
    """
    Takes in a DarkSky API response
    Returns a formatted dictionary

    :param response:
    :return:
    """
    # Get the DarkSky TimeMachine response and formatted json dictionary
    historical_json = response.json()['hourly']['data']
    for i in range(0, 24):
         = historical_json[i+12]




def format_midday_forecast(lat, lng):
    """
    Takes in historical and current darksky data
    returns the data in a dictionary, formatted so that the first key is midday, last key is 23 hours after that.

    :param lng:
    :param lat:
    :return:
    """
    # current_response = requests.get(f"https://api.darksky.net/forecast/{api_keys.darksky_apikey}/"
    #                                 f"{lat},{lng}?exclude=currently,minutely,daily,flags&units=us")
    # current_json = current_response.json()['hourly']['data']
    formatted_forecast = {}

    # Get the DarkSky TimeMachine response and formatted json dictionary
    midnight_response = requests.get(f"https://api.darksky.net/forecast/{api_keys.darksky_apikey}/"
                                     f"{lat},{lng},{ts}?exclude=currently,minutely,daily,flags&units=us")
    historical_json = midnight_response.json()['hourly']['data']

    for i in range(0, 24):
        dt_object = dt.fromtimestamp(historical_json[i]['time'])
        formatted_forecast[str(dt_object)] = historical_json[i]

    return formatted_forecast

    # else:
    #
    #     # Get the time in hours (int) that it would take to hit 12:00
    #     midday_offset = 12 - current_hour
    #
    #     # From midday of the current day to midday of the next day,
    #     #   create the new keys with the respective data for each hour.
    #     # Each key represents an hour.
    #     for i in range(midday_offset, 24 + midday_offset):
    #
    #         # Get the timestamp and convert it to a human readable date
    #         ts_current = current_json[i]['time']
    #         dt_obj = dt.fromtimestamp(ts_current)
    #
    #         # Assign the keys and data to the dictionary, starting at midday
    #         formatted_forecast[dt_obj.hour] = current_json[i]
    #
    # return formatted_forecast


if __name__ == '__main__':
    app.run(debug=True)
