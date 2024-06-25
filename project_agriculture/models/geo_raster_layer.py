from odoo import fields, models


class GeoRasterLayer(models.Model):
    _inherit = "geoengine.raster.layer"
    raster_type = fields.Selection(selection_add=[("map_box", "MapBox")], ondelete={"map_box": "set default"})
