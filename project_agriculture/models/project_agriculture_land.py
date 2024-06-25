import base64
import json
import os
import tempfile
import zipfile
from io import BytesIO

import geopandas as gpd
import topojson
from lxml import etree
from pykml.factory import KML_ElementMaker as KML
from shapely.geometry import shape

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class LandTag(models.Model):
    _name = "project.agriculture.land.tag"

    name = fields.Char(index=True, default_export_compatible=True)


class Land(models.Model):
    _name = "project.agriculture.land"
    _parent_name = "parent_id"
    _parent_store = True

    ALLOWED_FILE_EXTENSIONS = {
        "GeoJSON": "geojson",
        "TopoJSON": "topojson",
        "CSV": "csv",
        "KML": "kml",
        "WKT": "wkt",
    }

    project_id = fields.Many2one("project.project")
    name = fields.Char(index=True, default_export_compatible=True)
    parent_id = fields.Many2one("project.agriculture.land", "Parent Land", index=True, readonly=True)
    child_ids = fields.One2many("project.agriculture.land", "parent_id", "Land", domain=[("active", "=", True)])
    geopoint_ids = fields.One2many("project.agriculture.scout", "land_id", "Geo Points")
    child_ids_count = fields.Integer("Child Lands", compute="_compute_child_ids_count", store=True)
    parent_path = fields.Char(index=True, unaccent=False)
    priority = fields.Integer(default=100)
    tag_ids = fields.Many2many("project.agriculture.land.tag", column1="land_id", column2="tag_id", string="Tags")
    ref = fields.Char("Reference", index=True)
    barcode = fields.Char(help="Use a barcode to identify this land.", copy=False)
    active = fields.Boolean(
        default=True, help="By unchecking the active field, you may hide a land without deleting it."
    )
    default_map_layer = fields.Selection(
        [
            ("satellite", "Satellite"),
            ("street", "Street"),
            ("outdoors", "Outdoors"),
            ("osm", "OSM"),
        ],
        default="satellite",
        help="Select the default map view",
    )

    # Spatial
    the_geom = fields.GeoMultiPolygon("Geo Shape")
    polygon_type = fields.Selection(
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
        readonly=True,
    )
    area = fields.Float(digits="Area")
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
    geopoint = fields.GeoPoint()

    # Agronomy
    ph = fields.Float("pH", help="Values between 0 being the most acid and 14 being the most alcaline")
    organic_matter = fields.Float("Organic matter (%)", help="Values not greater than 100%")
    ec = fields.Float(
        "Electrical conductivity (mmhos/cm)",
        help="""
0.0 - 0.15    Very low          Plants may be starved of nutrients.\n
0.15- 0.50    Low               If soil lacks organic matter.Satisfactory if soil is high in organic matter\n
0.51- 1.25    Medium            Okay range for established plants.\n
1.26- 1.75    High              Okay for most established plants. Too high for seedlings or cuttings.\n
1.76-2.00     Very high         Plants usually stunted or chlorotic.\n
> 2.00        Excessively high  Plants severely dwarfed; seedlings and rooted cuttings frequently killed.
        """,
    )
    soil_type = fields.Selection(
        [
            ("clay", "Clay"),
            ("chalky", "Chalky"),
            ("silty", "Silty"),
            ("sandy", "Sandy"),
            ("loamy", "Loamy"),
        ],
    )
    is_irrigated = fields.Boolean()
    # crop_id = fields.Many2one("project.agriculture.species")

    # Political
    partner_id = fields.Many2one("res.partner", "Partner", index=True)
    city_id = fields.Many2one("res.city", required=True)
    state_id = fields.Many2one(
        "res.country.state", "State", ondelete="restrict", domain='[("country_id", "=?", country_id)]'
    )
    country_id = fields.Many2one("res.country", "Country", ondelete="restrict")
    company_id = fields.Many2one("res.company", "Company", index=True)

    def action_compute_geo_values(self):
        for rec in self:
            area = rec._get_area()
            latitude, longitude = rec._get_lat_long()
            rec.write(
                {
                    "area": area,
                    "latitude": latitude,
                    "longitude": longitude,
                }
            )

    @api.depends("child_ids")
    def _compute_child_ids_count(self):
        for record in self:
            record.child_ids_count = len(record.child_ids)

    def _get_area(self):
        self.ensure_one()
        if not self.the_geom:
            return 0.0
        query = """
            SELECT
                ST_Area(the_geom)
            FROM
                project_agriculture_land
            WHERE
                id=%(rec_id)s;
        """
        self.env.cr.execute(query, {"rec_id": self.id})
        res = self.env.cr.fetchone()[0]
        if not res:
            return 0.0
        return res / 10000

    def _get_lat_long(self):
        self.ensure_one()
        if not self.the_geom:
            return 0.0, 0.0
        query = """
            SELECT
                ST_AsGeoJSON(ST_Centroid(the_geom))
            FROM
                project_agriculture_land
            WHERE
                id=%(rec_id)s;
        """
        self.env.cr.execute(query, {"rec_id": self.id})
        res = self.env.cr.fetchone()[0]
        if not res:
            return 0.0, 0.0
        new_res = json.loads(res)
        coordinates = new_res.get("coordinates")
        if not coordinates:
            return 0.0, 0.0
        return coordinates

    def get_child_lands(self):
        """Retrieves the child lands of the current land record.
        Returns:
            list: A list of tuples, where each tuple contains the ID, name, polygon type,
                and GeoJSON of a child land. If the current land record does not have any
                child lands, the function returns an empty list.
        """
        if not self.child_ids:
            return []
        query = """
            WITH Childs AS (
                SELECT
                    child.id,
                    child.name,
                    child.polygon_type,
                    ST_AsGeoJSON(child.the_geom) AS geojson
                FROM
                    project_agriculture_land AS parent
                JOIN
                    project_agriculture_land AS child ON parent.id = child.parent_id
                WHERE
                    parent.id = %(rec_id)s
            )
            SELECT
                id,
                name,
                polygon_type,
                geojson
            FROM
                Childs;
        """
        self.env.cr.execute(query, {"rec_id": self.id})
        res = self.env.cr.fetchall()
        return res

    def remove_related_records(self, attribute, ids=None):
        """Removes related records from a given attribute of the model.
        This method is specifically used for removing 'child_ids' and 'geopoint_ids'
        from the model. It uses the unlink method to remove the related records.
        Parameters:
        attribute (str): The attribute from which related records should be removed.
            This should be either 'child_ids' or 'geopoint_ids'.
        ids (list, optional): A list of ids for the records to be removed. If this
            parameter is not provided, all related records will be removed.
        """
        for record in self:
            related_records = getattr(record, attribute)
            if ids:
                related_records = related_records.filtered(lambda r: r.id in ids)
            related_records.unlink()

    def _download_geojson(self):
        """Downloads the GeoJSON representation of the land's geometry and creates an attachment.
        Raises:
            ValidationError: If no geometry is found for this land.
        Returns:
            The created attachment.
        """
        self.has_geometry()
        geojson = self.get_geojson()
        return self.create_attachment(geojson, self.ALLOWED_FILE_EXTENSIONS["GeoJSON"])

    def _download_topojson(self):
        """Downloads the TopoJSON representation of the land's geometry.

        Raises:
            ValidationError: If no geometry is found for this land.

        Returns:
            The created attachment.
        """
        self.has_geometry()
        geojson = self.get_geojson()
        topo = topojson.Topology(geojson)
        return self.create_attachment(topo.to_json(), self.ALLOWED_FILE_EXTENSIONS["TopoJSON"])

    def _download_geopoints_csv(self):
        """Downloads a CSV file containing the geopoints associated with this land.

        Raises:
            ValidationError: If no geopoints are found for this land.

        Returns:
            attachment: The created attachment containing the CSV data.
        """
        self.has_geometry()
        if not self.geopoint_ids:
            raise ValidationError(_("No geopoints found for this land."))
        headers = ["name", "description", "longitude", "latitude", "scout_type"]
        data = "\n".join(
            [",".join(headers)]
            + [",".join([str(getattr(geopoint, header)) for header in headers]) for geopoint in self.geopoint_ids]
        )
        return self.create_attachment(data, self.ALLOWED_FILE_EXTENSIONS["CSV"])

    def _download_kml(self):
        """Downloads a KML file for the land's geometry.

        Raises:
            ValidationError: If no geometry is found for this land.

        Returns:
            Attachment: The created attachment for the KML file.
        """
        self.has_geometry()
        geojson = json.loads(self.get_geojson())
        kml_root = KML.kml()
        doc = KML.Document()
        coords = "\n".join(f"{lat},{lon}" for lat, lon in geojson["coordinates"][0][0])
        kml_polygon = KML.Placemark(KML.Polygon(KML.outerBoundaryIs(KML.LinearRing(KML.coordinates(coords)))))
        doc.append(kml_polygon)
        kml_root.append(doc)
        kml_data = etree.tostring(kml_root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("utf-8")
        return self.create_attachment(kml_data, self.ALLOWED_FILE_EXTENSIONS["KML"])

    def _download_wkt(self):
        """Downloads the WKT representation of the geometry of this land as an attachment.

        Raises:
            ValidationError: If no geometry is found for this land.

        Returns:
            The created attachment.
        """
        self.has_geometry()
        return self.create_attachment(self.the_geom.wkt, self.ALLOWED_FILE_EXTENSIONS["WKT"])

    def _download_shapefiles(self):
        """Downloads the shapefiles for the land's geometry and returns them as a zip attachment.

        Raises:
            ValidationError: If no geometry is found for this land.

        Returns:
            Attachment: The zip attachment containing the shapefiles.
        """
        self.has_geometry()
        geojson = json.loads(self.get_geojson())
        geometry = shape(geojson)
        gdf = gpd.GeoDataFrame([{"geometry": geometry}])
        with tempfile.TemporaryDirectory() as tmpdirname:
            shapefile_path = os.path.join(tmpdirname, f"{self.name}.shp")
            gdf.to_file(shapefile_path, driver="ESRI Shapefile")
            bytes_buffer = BytesIO()
            with zipfile.ZipFile(bytes_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for filename in os.listdir(tmpdirname):
                    zf.write(os.path.join(tmpdirname, filename), arcname=filename)
        zip_values = bytes_buffer.getvalue()
        return self.create_attachment(zip_values, "zip", is_data_encoded=True)

    def get_geojson(self):
        """Executes a SQL query to get the GeoJSON of the current land record.

        Returns:
            str: The GeoJSON of the current land record.
        """
        query = """
        SELECT
            ST_AsGeoJSON(ST_Transform(the_geom, 4326))
        FROM
            project_agriculture_land
        WHERE
            id=%(rec_id)s;
        """
        self.env.cr.execute(query, {"rec_id": self.id})
        res = self.env.cr.fetchone()[0]
        return res

    def create_attachment(self, data, file_extension, **kargs):
        """Creates an attachment with the given data and file extension.
        The supported file extensions are: 'geojson', 'topojson', 'csv', 'kml', 'wkt', 'shapefile'.
        Args:
            data (str): The data to be stored in the attachment.
            file_extension (str): The file extension of the attachment.
        Returns:
            dict: A dictionary containing the type of action ('ir.actions.act_url'),
                the URL for the download action, and the target of the action.
        """
        if not kargs.get("is_data_encoded"):
            data = data.encode()
        values = {
            "name": f"{self.name}.{file_extension}",
            "res_model": "project.agriculture.land",
            "res_id": self.id,
            "type": "binary",
            "public": False,
            "datas": base64.b64encode(data),
        }
        attachment_id = self.env["ir.attachment"].sudo().create(values)
        download_url = f"/web/content/{attachment_id.id}?download=True"
        base_url = self.env["ir.config_parameter"].get_param("web.base.url")
        return {
            "type": "ir.actions.act_url",
            "url": f"{base_url}{download_url}",
            "target": "new",
        }

    def has_geometry(self):
        """Check if the land has a geometry."""
        if not self.the_geom:
            raise ValidationError(_("No geometry found for this land."))

    @api.model
    def get_all_child_lands(self):
        query = """
            SELECT
                id,
                name,
                polygon_type,
                ST_AsGeoJSON(the_geom) AS geojson
            FROM
                project_agriculture_land
            WHERE
                parent_id IS NOT NULL;
        """
        self.env.cr.execute(query, {"rec_id": self.id})
        res = self.env.cr.fetchall()
        return res
