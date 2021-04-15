from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta, date
from pprint import pprint
from darksky import forecast
from opencage.geocoder import OpenCageGeocode
from datetime import datetime as dt
from Utilities import Util
import requests
import API_keys
import socket
import calendar

geocoder = OpenCageGeocode(API_keys.opencage_api_key)
u = Util()

app = Flask(__name__)
app.secret_key = "hello"
app.permanent_session_lifetime = timedelta(days=5)


@app.route("/", methods=['POST', 'GET'])
def main():
    return render_template("index.html")


@app.route("/forecast", methods=['POST', 'GET'])
def forecast():
    if request.method == 'POST':
        cur_date = date.today()
        cur_date_formatted = calendar.month_name[cur_date.month] + " " + str(cur_date.day)
        loc = request.form['city'] + ", " + request.form['state']
        geocoder_data = geocoder.geocode(loc)
        return render_template("forecast.html", location=loc, geocode=geocoder_data, date=cur_date_formatted)
    else:
        return render_template("index.html")
    # # Ask user for their location
    # locational_data = get_user_locational_data()
    #
    # # Assign values based on user's location
    # lng = locational_data[0]['geometry']['lng']
    # lat = locational_data[0]['geometry']['lat']
    # city = get_city_from_locational_data(locational_data)
    #
    # # Get darksky forecast and create an hourly dictionary
    # darksky_forecast = forecast(API_keys.darksky_api_key, lat, lng)
    # hourly_forecast = create_hourly_dict(darksky_forecast)
    #
    # # Analyze the hourly dictionary hour by hour
    # print(city + ", " + locational_data[0]['components']['state'])
    # analyze_hourly_results(hourly_forecast, darksky_forecast)


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
        hourly_dict[dt_object] = ds_forecast.hourly[x]

    return hourly_dict


def analyze_hourly_results(hourly_forecast, darksky_forecast):
    """
    Takes in the results of a darksky API call
    Analyzes the data and determines whether or not it is a good time for astrophotography over a 24 hour period

    :param hourly_forecast:
    :param darksky_forecast:
    :return:
    """
    # Get moon phase
    moon_phase = darksky_forecast.daily.data[0].moonPhase
    print("TONIGHT'S MOON PHASE: " + u.moon_phase(moon_phase))

    for key in hourly_forecast:
        print(key)
        print("CLOUD COVERAGE: " + str(hourly_forecast[key].cloudCover))
        print("WIND SPEED: " + str(hourly_forecast[key].windSpeed))
        print("WIND DIRECTION: " + u.wind_direction(hourly_forecast[key].windBearing))

        if hourly_forecast[key].cloudCover > 0.10 or hourly_forecast[key].windSpeed > 3.5:
            if hourly_forecast[key].cloudCover > 0.10 and hourly_forecast[key].windSpeed <= 3.5:
                print("The wind may be reasonable, but there are too many clouds outside for astrophotography\n")
            elif hourly_forecast[key].windSpeed > 3.5 and hourly_forecast[key].cloudCover <= 0.10:
                print("There may be almost no clouds, but it is too windy for astrophotography\n")
            else:
                print("The wind is too strong and there are too many clouds out!\n")
        else:
            print("It's a good night for astrophotography :)\n")


def get_city_from_locational_data(loc_data):
    """
    Takes in the results of a GEOCODE API call and returns the correct city name.
    Sometimes, the result is listed as a town, city, or suburb.

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

    print("1. IP address")
    print("2. City, State")
    print("3. Latitude / Longitude")
    repeat = True

    while repeat:
        loc_type = input("Please choose search method (number): ")

        if loc_type == "1":
            # IP Lookup
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            ip_loc_data = requests.get(
                "https://api.ipgeolocation.io/ipgeo?apiKey={0}&ip={1}".format(API_keys.ip_loc_api_key,
                                                                              ip_address)).json()
            print(ip_loc_data)
            return ip_loc_data['city'] + ", " + ip_loc_data['state_prov']

        elif loc_type == "2":
            # City, State
            city = input("Please enter the name of a city: ")
            state = input("Please enter the name of a state: ")
            location = city + ", " + state
            return geocoder_forward(location)

        elif loc_type == "3":
            # Latitude / Longitude lookup
            lat = input("Please enter the latitude: ")
            lng = input("Please enter the longitude: ")
            return geocoder_reverse(lat, lng)

        print("Please enter a number from 1 to 3")


def geocoder_forward(location):
    """
    Takes in a location in the STRING format "city, state"
    Returns the results of geocode api call based on their location (lat, lng)

    :param location: STRING (City, State)
    :return: GEOCODE API RESULTS
    """
    return geocoder.geocode(location)


def geocoder_reverse(lat, lng):
    """
    Takes in latitude and longitude
    Returns the results of geocode api call based on their location (city, state)

    :param lat: STRING latitude
    :param lng: STRING longitude
    :return: GEOCODE API RESULTS
    """
    return geocoder.reverse_geocode(lat, lng)


if __name__ == '__main__':
    app.run(debug=True)
