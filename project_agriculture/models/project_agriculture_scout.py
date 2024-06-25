from odoo import fields, models


class Scout(models.Model):
    _name = "project.agriculture.scout"

    name = fields.Char(index=True, default_export_compatible=True)
    land_id = fields.Many2one("project.agriculture.land", readonly=True, required=True)
    description = fields.Text()
    longitude = fields.Float(digits=(16, 5), readonly=True, required=True)
    latitude = fields.Float(digits=(16, 5), readonly=True, required=True)
    scout_type = fields.Selection(
        [
            ("Property_boundary", "Property boundary"),
            ("Field", "Field"),
            ("Animal", "Animal"),
            ("Bed", "Bed"),
            ("Irrigation", "Irrigation"),
            ("Trial", "Trial"),
            ("Buffer", "Buffer"),
            ("Storage", "Storage"),
            ("Building", "Building"),
            ("Other", "Other"),
        ],
        default="Property_boundary",
        required=True,
    )
    geopoint = fields.GeoPoint()
