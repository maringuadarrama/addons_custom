from odoo import fields, models


class WeatherStation(models.Model):
    _name = "project.agriculture.weather.station"

    name = fields.Char(index=True, default_export_compatible=True)
    geopoint = fields.GeoPoint("Coordinate")


class WeatherLog(models.Model):
    _name = "project.agriculture.weather.log"

    date = fields.Date(string="Date UTC")
    local_date = fields.Date(string="Mexico Date")
    air_temperature = fields.Float("°C?")
    precipitation = fields.Float("Precipitation (mm)")
    relative_humidity = fields.Float("Precipitation (%)")
    atmospheric_preassure = fields.Float("Precipitation")
    solar_radiation = fields.Float("Precipitation")
    # wind_direction =
    wind_speed = fields.Float("Precipitation")
