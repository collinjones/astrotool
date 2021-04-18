from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta, date
from darksky import forecast
from opencage.geocoder import OpenCageGeocode
from datetime import datetime as dt
import calendar, requests, api_keys, socket, pylunar, almanac, utilities as u
import timezonefinder, pytz

geocoder = OpenCageGeocode(api_keys.open_cage_apikey)

app = Flask(__name__)
app.secret_key = "hello"
app.permanent_session_lifetime = timedelta(days=5)

default_loc = "Broomfield, Colorado"


@app.route("/", methods=['POST', 'GET'])
def astro_forecast():
    """
    main forecast function

    :return: render_template("index.html", **context)
    """
    context = set_up_forecast()
    return render_template("forecast.html", **context)


def create_hourly_dict(ds_forecast, geocoder_data):
    """
    Returns a dictionary out of hourly forecast data

    :param ds_forecast: DARKSKY API RESULTS
    :return: DICTIONARY of hourly forecast data
    """
    # Create empty dictionary
    hourly_dict = {}

    tf = timezonefinder.TimezoneFinder()
    timezone_str = tf.certain_timezone_at(lat=geocoder_data[0]['geometry']['lat'],
                                          lng=geocoder_data[0]['geometry']['lng'])
    if timezone_str is None:
        print("Could not find time zone")
    else:
        timezone = pytz.timezone(timezone_str)
        datet = dt.utcnow()

    # Create a 24 hour dictionary starting from the current hour using the time as the keys
    for x in range(0, 24):
        dt_object = dt.fromtimestamp(ds_forecast.hourly[x].time)
        hourly_dict[str(dt_object)] = ds_forecast.hourly[x]

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

    # Get darksky data
    darksky_data = forecast(key=api_keys.darksky_apikey, latitude=geocoder_data[0]['geometry']['lat'],
                            longitude=geocoder_data[0]['geometry']['lng'], time=)

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


if __name__ == '__main__':
    app.run(debug=True)
