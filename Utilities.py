# Utilities.py
# Contains useful utility methods

class Util:

    def wind_direction(self, bearing):
        """
        Takes in the wind bearing direction in degrees.
        Returns the direction of the wind.

        :param bearing: INT, bearing of the wind in degrees
        :return: res_key, STRING, direction of wind
        """

        # Dictionary of wind bearings and their cardinal direction counterparts
        bearing_dict = {
            "North": 0,
            "North East": 45,
            "East": 90,
            "South East": 135,
            "South": 180,
            "South West": 225,
            "West": 270,
            "North West": 315,
        }

        # Map (bearing - each value) and take the minimum value, then return the key
        if bearing < 337.5:
            return min(bearing_dict.items(), key=lambda x: abs(bearing - x[1]))[0]

        # In the case that the bearing is above 337.5, evaluate to north
        else:
            return "North"

    def moon_phase(self, phase):
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
