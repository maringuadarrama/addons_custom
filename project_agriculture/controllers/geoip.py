from odoo import http


class GeoIPController(http.Controller):
    @http.route("/get_geoip", type="json", auth="user")
    def geoip(self):
        """Returns the longitude and latitude values of the user's IP address.
        :return: A list containing the longitude and latitude values,
        or an empty list if the values are not available.
        :rtype: list
        """
        longitude = http.request.geoip.get("longitude")
        latitude = http.request.geoip.get("latitude")
        if longitude and latitude:
            return [longitude, latitude]
        return []
