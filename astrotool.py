import time
from pprint import pprint
from collections import OrderedDict
from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta, date
from darksky import forecast
from opencage.geocoder import OpenCageGeocode
from datetime import datetime as dt
import calendar, requests, api_keys, socket, pylunar, almanac, utilities as u
import timezonefinder, pytz
from timezonefinder import TimezoneFinder
import requests
import ciso8601
from pytz import timezone

geocoder = OpenCageGeocode(api_keys.open_cage_apikey)

app = Flask(__name__)
app.secret_key = "hello"
app.permanent_session_lifetime = timedelta(days=5)

# Setup variables
default_loc = "Broomfield, Colorado"  # Default location
today = dt.today()  # Current date object
current_hour = today.hour


@app.route("/", methods=['POST', 'GET'])
def astro_forecast():
    """
    main forecast function

    :return: render_template("index.html", **context)
    """
    context = set_up_forecast()
    return render_template("forecast.html", **context)


def start_forecast_current_hour(ds_forecast):
    """
    Returns a dictionary out of hourly forecast data

    :param ds_forecast: DARKSKY API RESULTS
    :return: DICTIONARY of hourly forecast data
    """

    # Create empty dictionary
    hourly_dict = {}

    # Create a 24 hour dictionary starting from the current hour using the time as the keys
    for i in range(0, 24):
        hourly_dict[str(i)] = ds_forecast['hourly'][i]

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
    global current_hour
    global formatted_current

    # Determine if city/state or lat/lng, return loc data and location
    if request.form:
        geocoder_data, loc = get_user_locational_data()
    else:
        loc = default_loc
        geocoder_data = geocoder.geocode(default_loc)

    lat = geocoder_data[0]['geometry']['lat']
    lng = geocoder_data[0]['geometry']['lng']

    # Localize the time to where the data is being requested
    tz_obj = TimezoneFinder()
    my_date = dt.now(pytz.timezone(tz_obj.timezone_at(lng=lng, lat=lat)))
    localized_hour = my_date.hour

    # Return the hourly forecast
    hourly_forecast = get_weather_data(lat, lng, 'midnight')

    # Get a list of wind directions and ids
    wind_direction_ids = []
    wind_directions = []
    for key in hourly_forecast:
        wind_directions.append(u.wind_direction(hourly_forecast[key]['wind_deg']))
        wind_direction_ids.append("direction" + str(key))

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
        'current_hour': localized_hour
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

    if request_type == 'current':
        response = requests.get(f"http://pro.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lng}&units=imperial&dt=1618850845&appid={api_keys.openweather_apikey}")
        return start_forecast_current_hour(response.json())

    elif request_type == 'midnight':
        return center_forecast_on_midnight(lat, lng)

    elif request_type == 'midday':
        return center_forecast_on_midday(lat, lng)


def center_forecast_on_midnight(lat, lng):
    """
    Center the forecast on midnight. (12 - 11)

    :param lat:
    :param lng:
    :return:
    """
    formatted_forecast = OrderedDict()

    yesterday_json = request_data("yesterday", lat, lng)
    today_historical_json = request_data("earlier", lat, lng)
    currently_json = request_data("now", lat, lng)

    # Request made before noon
    if current_hour < 12:
        # Get the data from noon to midnight of the previous day
        for i in range(12, 24):
            formatted_forecast[str(i)] = yesterday_json['hourly'][i]
        for i in range(0, 12):
            formatted_forecast[str(i)] = today_historical_json['hourly'][i]
        # TODO - finish the center on midnight request when the hour is before noon
    else:
        # Midday of the current day to the current hour of the current day
        for i in range(12, current_hour):
            formatted_forecast[str(i)] = today_historical_json['hourly'][i]
        # Current hour of current day to midday of the next day
        for i in range(0, 25 - (current_hour - 12)):

            # The logic below is for keeping the keys relative to a 24 hour time system.

            # If the current hour of the iterator is less than 24, make the key be the index plus the current hour
            if i+current_hour < 24:
                formatted_forecast[str(i+current_hour)] = currently_json['hourly'][i]

            # If the current hour of the iterator is above 24, subtract 25 (to get 0) and keep iterating
            if i+current_hour > 24:
                formatted_forecast[str(i+current_hour-25)] = currently_json['hourly'][i]

    return formatted_forecast


def center_forecast_on_midday(lat, lng):
    """
    Center the forecast on midday (00 - 23)
    """

    # Create empty dict
    formatted_forecast = {}

    # Get the Openweather API response and format it to JSON
    earlier_weather = request_data("earlier", lat, lng)

    # From 0 to 24
    for i in range(0, 24):
        # Add a 0 before i if i is less than 10
        if i < 10:
            formatted_forecast["0" + str(i)] = earlier_weather['hourly'][i]
        else:
            formatted_forecast[str(i)] = earlier_weather['hourly'][i]

    return formatted_forecast


def request_data(type, lat, lng):
    """
    A function for requesting different types of data.
        "now": data from now to 48 hours ahead
        "earlier": 24 hours of data starting at the first hour of the current day
        "yesterday": 24 hours of data starting at the first hour of the day before the current day

    :param type: type of data being requested
    :param lat: latitude
    :param lng: longitude
    :return: json object of weather data
    """

    if type == "now":
        currently_response = requests.get(f"https://pro.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lng}&units=imperial&appid={api_keys.openweather_apikey}")
        return currently_response.json()
    elif type == "earlier":
        today_historical_response = requests.get(f"https://pro.openweathermap.org/data/2.5/onecall/timemachine?lat={lat}&lon={lng}&units=imperial&dt={int(today.timestamp())}&appid={api_keys.openweather_apikey}")
        return today_historical_response.json()
    elif type == "yesterday":
        # Get yesterday's date
        yesterday = today - timedelta(1)
        yesterday_midnight = dt(yesterday.year, yesterday.month, yesterday.day, hour=0)
        yesterday_timestamp = int(yesterday_midnight.timestamp())
        yesterday_response = requests.get(f"https://pro.openweathermap.org/data/2.5/onecall/timemachine?lat={lat}&lon={lng}&units=imperial&dt={yesterday_timestamp}&appid={api_keys.openweather_apikey}")
        return yesterday_response.json()


if __name__ == '__main__':
    app.run(debug=True)
