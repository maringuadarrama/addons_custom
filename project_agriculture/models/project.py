from odoo import fields, models


class Project(models.Model):
    _inherit = "project.project"

    # Agronomic fields
    is_agroproject = fields.Boolean(compute="_compute_is_agroproject", store=True)
    agricultural_cycle = fields.Selection(
        [
            ("none", "None"),
            ("ss", "Spring - summer"),
            ("aw", "Autum - winter"),
            ("year", "Year"),
        ],
        "Agricultural cycle",
        default="none",
    )
    agriculture_asset_ids = fields.One2many(
        "project.agriculture.asset",
        "project_id",
        "Agriculture assets",
        copy=False,
    )
    land_ids = fields.One2many(
        "project.agriculture.land",
        "project_id",
        "Agriculture lands",
        copy=False,
    )
    surface_total = fields.Float("Surface", help="the sum of all land_ids surface")

    # Agro BI
    fianna_percentage = fields.Float(help="the percentage of hectares plantted with Fianna concept")
    fresh_percentage = fields.Float(help="The percentage of hectars plantted with non fianna concept")
    potato_stage1_percentage = fields.Float(help="The percentage of hectars that are in potato stage 1")
    potato_stage2_percentage = fields.Float(help="The percentage of hectars that are in potato stage 2")
    potato_stage3_percentage = fields.Float(help="The percentage of hectars that are in potato stage 3")
    potato_stage4_percentage = fields.Float(help="The percentage of hectars that are in potato stage 4")
    potato_stage5_percentage = fields.Float(help="The percentage of hectars that are in potato stage 5")
    potato_total_harvest_percentage = fields.Float(help="The percentage of hectars that have been harvested")
    potato_yield_total_expected = fields.Float(
        "Yield expected", help="The mean yield of the fields grown during season."
    )
    potato_yield_mean = fields.Float("Mean yield", help="The mean yield of the fields grown during season.")

    def _compute_is_agroproject(self):
        for project in self:
            project.is_agroproject = self.env.context.get("is_agroproject", False)
