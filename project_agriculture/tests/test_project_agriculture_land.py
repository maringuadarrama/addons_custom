import base64
import csv
import io
import json
import zipfile

from shapely.geometry import mapping
from topojson import Topology

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("project_agriculutre_land", "post_install", "-at_install")
class TestProjectAgricultureLand(TransactionCase):
    def setUp(self):
        super().setUp()
        city_demo_id = self.env.ref("project_agriculture.city_demo").id
        self.land = self.env["project.agriculture.land"].create(
            {
                "name": "Land Demo 1",
                "city_id": city_demo_id,
                "the_geom": "MULTIPOLYGON (((-11339471.710185 2393255.333162, -11339546.089816 2393140.585501, "
                "-11339633.220221 2393090.649054, -11339658.19056 2393137.929312, "
                "-11339588.592478 2393177.772259, -11339522.182075 2393271.270324, -11339471.710185 2393255.333162)))",
                "geopoint_ids": [
                    Command.create({"name": "geopoint", "longitude": -11339579.93587, "latitude": 2393155.82172})
                ],
                "child_ids": [
                    Command.create(
                        {
                            "name": "Child Land Demo 1",
                            "city_id": city_demo_id,
                            "the_geom": "MULTIPOLYGON (((-11339514.368272 2393235.298866, "
                            "-11339549.097338 2393190.679578, -11339547.518748 2393176.18906, "
                            "-11339495.855675 2393228.268819, -11339514.368272 2393235.298866)))",
                        }
                    )
                ],
            }
        )
        self.ir_attachment = self.env["ir.attachment"]

    def test_01_get_child_lands(self):
        child_lands = self.land.get_child_lands()
        self.assertEqual(len(child_lands), 1)
        name = self.land.child_ids[0].name
        self.assertEqual(name, "Child Land Demo 1")

    def test_02_remove_related_records(self):
        self.land.remove_related_records("child_ids")
        self.assertEqual(len(self.land.child_ids), 0)
        self.land.remove_related_records("geopoint_ids")
        self.assertEqual(len(self.land.geopoint_ids), 0)

    def test_03_get_geojson(self):
        geojson = json.loads(self.land.get_geojson())
        the_geom_geojson = mapping(self.land.the_geom)
        self.assertEqual(geojson["type"], the_geom_geojson["type"])
        self.land.action_compute_geo_values()
        self.assertEqual(round(self.land.longitude, 4), 2393179.0168)
        self.assertEqual(round(self.land.latitude, 4), -11339562.9264)
        self.assertEqual(round(self.land.area, 4), 1.15)

    def test_04_has_geometry(self):
        self.land.the_geom = None
        with self.assertRaises(ValidationError):
            self.land.has_geometry()

    def test_05_download_geojson(self):
        results = self.land._download_geojson()
        attachment = self.ir_attachment.search(
            [("res_id", "=", self.land.id), ("res_model", "=", "project.agriculture.land")]
        )
        self.assertEqual(attachment.name, f"{self.land.name}.geojson")
        expected_url = f"/content/{attachment.id}?download=True"
        url = results["url"].split("/web", 1)[1]
        self.assertEqual(url, expected_url)

    def test_06_download_download_topojson(self):
        self.land._download_topojson()
        attachment = self.ir_attachment.search(
            [("res_id", "=", self.land.id), ("res_model", "=", "project.agriculture.land")]
        )
        self.assertEqual(attachment.name, f"{self.land.name}.topojson")
        topojson1 = Topology(self.land.the_geom)
        attachment_data = json.loads(base64.b64decode(attachment.datas))
        self.assertEqual(attachment_data["type"], topojson1.to_dict()["type"])

    def test_07_download_geopoints_csv(self):
        self.land._download_geopoints_csv()
        attachment = self.ir_attachment.search(
            [("res_id", "=", self.land.id), ("res_model", "=", "project.agriculture.land")]
        )
        self.assertEqual(attachment.name, f"{self.land.name}.csv")
        datas = base64.b64decode(attachment.datas)
        csv_data = io.StringIO(datas.decode("utf-8"))
        csv_reader = csv.reader(csv_data)
        expected_columns = 5
        self.assertEqual(len(next(csv_reader)), expected_columns)

    def test_08_download_kml(self):
        self.land._download_kml()
        attachment = self.ir_attachment.search(
            [("res_id", "=", self.land.id), ("res_model", "=", "project.agriculture.land")]
        )
        # Test if the attachment is created
        self.assertTrue(attachment.exists())
        # Test the attachment name
        self.assertEqual(attachment.name, f"{self.land.name}.kml")

    def test_09_download_wkt(self):
        self.land._download_wkt()
        attachment = self.ir_attachment.search(
            [("res_id", "=", self.land.id), ("res_model", "=", "project.agriculture.land")]
        )
        self.assertEqual(attachment.name, f"{self.land.name}.wkt")

    def test_10_download_shapefiles(self):
        self.land._download_shapefiles()
        attachment = self.ir_attachment.search(
            [("res_id", "=", self.land.id), ("res_model", "=", "project.agriculture.land")]
        )
        self.assertEqual(attachment.name, f"{self.land.name}.zip")
        datas = base64.b64decode(attachment.datas)
        expected_number_of_files = 4
        # Open the zip file
        with zipfile.ZipFile(io.BytesIO(datas), "r") as zip_ref:
            files = zip_ref.namelist()
            num_files = len(files)
            self.assertEqual(num_files, expected_number_of_files)
