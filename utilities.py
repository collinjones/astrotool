# utilities.py
# Contains useful utility methods
from datetime import date
import calendar


def wind_direction(bearing):
    """
    Takes in the wind bearing direction in degrees.
    Returns the direction of the wind.

    :param bearing: INT, bearing of the wind in degrees
    :return: res_key, STRING, direction of wind
    """

    # Dictionary of wind bearings and their cardinal direction counterparts
    bearing_dict = {
        "↑": 0,
        "↗": 45,
        "→": 90,
        "↘": 135,
        "↓": 180,
        "↙": 225,
        "←": 270,
        "↖": 315,
    }

    # Map (bearing - each value) and take the minimum value, then return the key
    if bearing < 337.5:
        return min(bearing_dict.items(), key=lambda x: abs(bearing - x[1]))[0]

    # In the case that the bearing is above 337.5, evaluate to north
    else:
        return "↑"


def moon_phase(phase):
    """
    Takes in a FLOAT moon phase between 0.0 to 1.0
    Returns the STRING moon phase in english

    :param phase: FLOAT moon phase between 0.0 and 1.0
    :return: STRING moon phase in english
    """
    phase_dict = {
        "New Moon": 0,
        "First Quarter Moon": 0.25,
        "Full Moon": 0.5,
        "Last Quarter Moon": 0.75,
    }
    res_key = min(phase_dict.items(), key=lambda x: abs(phase - x[1]))

    return res_key[0]


def get_current_date():
    """
    Returns a formatted date in the form (Monthname, Day)

    :return: (Monthname, Day)
    """
    return calendar.month_name[date.today().month] + " " + str(date.today().day)


def decdeg2dms(dd):
    is_positive = dd >= 0
    dd = abs(dd)
    minutes, seconds = divmod(dd * 3600, 60)
    degrees, minutes = divmod(minutes, 60)
    degrees = degrees if is_positive else -degrees
    return degrees, minutes, seconds


def kelvin_to_fahrenheit(temp):
    """
    Converts a temperature, represented in Kelvin, to Fahrenheit

    :param temp: Temperature in Kelvin
    :return:
    """
    return (((temp - 273.15) * 9) / 5) + 32

