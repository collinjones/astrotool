from pprint import pprint
from collections import OrderedDict

from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta, date, time
from opencage.geocoder import OpenCageGeocode
from datetime import datetime as dt
import calendar, requests, api_keys, socket, pylunar, almanac, utilities as u
import timezonefinder, pytz
from timezonefinder import TimezoneFinder
import requests

geocoder = OpenCageGeocode(api_keys.open_cage_apikey)
master_forecast = []

app = Flask(__name__)
app.secret_key = "hello"
app.permanent_session_lifetime = timedelta(days=5)

# Setup variables
default_loc = "Broomfield, Colorado"  # Default location
today = dt.today()  # Current date object
min_date = date(today.year, today.month, today.day - 1)
min_time = time(12, 00)

mid_date = date(today.year, today.month, today.day)
mid_time = time(today.hour - 1, 00)

max_date = date(today.year, today.month, today.day + 1)
max_time = time(today.hour - 1, 00)

min_dt = dt.combine(min_date, min_time)
mid_dt = dt.combine(mid_date, mid_time)
max_dt = dt.combine(max_date, max_time)


@app.route("/", methods=['POST', 'GET'])
def index():
    """
    main forecast function

    :return: render_template("index.html", **context)
    """
    return render_template("index.html")


@app.route("/forecast", methods=['POST', 'GET'])
def forecast():

    # Declare context. Context is the dictionary containing information to set up the forecast.
    context = None

    # Check if a new location was searched for
    if "location" in request.form:

        # Get the new city and state from the request form
        # Set the context with the new city and state and the "current" centering option
        session["city"] = request.form['city']
        session["state"] = request.form['state']
        context = set_up_forecast(session["city"], session["state"], "current", new_loc=True)

    # else if, check that the user has requested a different centering option.
    elif request.form["center"] == "center":

        # Set the context with the current city and state and the new centering option from the request form
        context = set_up_forecast(session["city"], session["state"], request.form["submit"])

    # Render the template with "forecast.html" and the context.
    return render_template("forecast.html", **context)


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


def get_user_locational_data(city, state):
    """
    Asks users for their location via IP, City / State, or latitude / longitude
    Returns the geocode api results based on their location

    :return: GEOCODE API RESULTS
    """
    return geocoder.geocode(city + ", " + state), \
           city + ", " + state


@app.route("/center", methods=['POST', 'GET'])
def set_up_forecast(city, state, centering, new_loc=False):
    """
    Sets up the forecast table
    Returns the context for the html
    :return:
    """
    global current_hour, master_forecast
    global formatted_current

    # Determine if city/state or lat/lng, return loc data and location
    if request.form:
        geocoder_data, loc = get_user_locational_data(city, state)
    else:
        loc = default_loc
        geocoder_data = geocoder.geocode(default_loc)

    lat = geocoder_data[0]['geometry']['lat']
    lng = geocoder_data[0]['geometry']['lng']

    # Localize the time to where the data is being requested
    tz_obj = TimezoneFinder()
    my_date = dt.now(pytz.timezone(tz_obj.timezone_at(lng=lng, lat=lat)))
    localized_hour = my_date.hour

    if new_loc:
        master_forecast = request_data(lat, lng)

    hourly_forcast = parse_weather_data(centering)

    # Get a list of wind directions and ids
    wind_direction_ids = []
    wind_directions = []
    for key in hourly_forcast:
        wind_directions.append(u.wind_direction(hourly_forcast[key]['wind_deg']))
        wind_direction_ids.append("direction" + str(key))

    # Get moon rise / set times
    lat_dms = u.decdeg2dms(geocoder_data[0]['geometry']['lat'])
    lng_dms = u.decdeg2dms(geocoder_data[0]['geometry']['lng'])
    moon_obj = pylunar.MoonInfo(lat_dms, lng_dms)
    lunar_set_rise = pylunar.MoonInfo.rise_set_times(moon_obj, "UTC-07:00")

    # Return the context for flask html variables as a dictionary
    return {
        'geocode': geocoder_data,
        'darksky': hourly_forcast,
        'wind_directions': wind_directions,
        'wind_direction_ids': wind_direction_ids,
        'date': u.get_current_date(),
        'location': loc,
        'phase': moon_obj.phase_name().replace("_", " "),
        'lunar_times': lunar_set_rise,
        'current_hour': localized_hour
    }


def parse_weather_data(request_type):
    """
    Takes in lat, lng, and request type and
        return a darksky api json dictionary.

    :param lat:
    :param lng:
    :param request_type:
    :return:
    """

    if request_type == 'current':
        return start_forecast_current_hour()

    elif request_type == 'midnight':
        return center_forecast_on_midnight()

    elif request_type == 'midday':
        return center_forecast_on_midday()


def start_forecast_current_hour():
    """
    Returns a dictionary out of hourly forecast data

    :param ds_forecast: DARKSKY API RESULTS
    :return: DICTIONARY of hourly forecast data
    """

    # Create empty dictionary
    formatted_forecast = {}
    pprint(master_forecast)
    # Create a 24 hour dictionary starting from the current hour using the time as the keys
    pprint(len(master_forecast))
    for i in range(len(master_forecast) - 23, len(master_forecast)):
        formatted_forecast[str(i)] = master_forecast[i]

    return formatted_forecast


def center_forecast_on_midnight():
    """
    Center the forecast on midnight. (12 - 11)

    :param lat:
    :param lng:
    :return:
    """
    formatted_forecast = {}

    # Request made before noon
    if current_hour <= 11:
        for i in range(0, 23):
            formatted_forecast[str(i)] = master_forecast[i]
    # Request made after noon
    else:
        for i in range(24, 47):
            formatted_forecast[str(i)] = master_forecast[i]

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
    for i in range(len(earlier_weather['hourly'])):
        formatted_forecast[str(i)] = earlier_weather['hourly'][i]

    return formatted_forecast


def request_data(lat, lng):
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
    min_to_max_weather_data = {}

    # For historical, we want to go from 12pm of previous day to current hour - 1
    # For current we want to go from current hour to 23 hours ahead.
    historical_response = requests.get(
        f"https://history.openweathermap.org/data/2.5/history/city?lat={lat}&lon={lng}&type=hour&start={int(min_dt.timestamp())}&end={int(mid_dt.timestamp())}&appid={api_keys.openweather_apikey}")
    currently_response = requests.get(
        f"https://pro.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lng}&units=imperial&appid={api_keys.openweather_apikey}")

    pprint(f"https://history.openweathermap.org/data/2.5/history/city?lat={lat}&lon={lng}&type=hour&start={int(min_dt.timestamp())}&end={int(mid_dt.timestamp())}&appid={api_keys.openweather_apikey}")
    pprint(f"https://pro.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lng}&units=imperial&appid={api_keys.openweather_apikey}")
    historical_json = historical_response.json()
    currently_json = currently_response.json()

    # From 12pm of the previous day to 1 - current hour
    for i in range(historical_json['cnt']):
        min_to_max_weather_data[i] = historical_json['list'][i]

    for i in range(0, 23):
        min_to_max_weather_data[i+historical_json['cnt']] = currently_json['hourly'][i]

    # THIS IS THE MASTER FILE. THIS REDUCES THE AMOUNT OF TIMES THE API IS CALLED TO ONCE PER LOCATION.
    return min_to_max_weather_data


if __name__ == '__main__':
    app.run(debug=True)
