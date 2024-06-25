from odoo import fields, models


class ProjectAgricultureAsset(models.Model):
    _name = "project.agriculture.asset"

    name = fields.Char(index=True)
    species_id = fields.Many2one("project.agriculture.species")
    production_plan_id = fields.Many2one("project.agriculture.production.plan")
    project_id = fields.Many2one("project.project")
    partner_id = fields.Many2one("res.partner")
    land_id = fields.Many2one(
        "project.agriculture.land",
        "Agriculture land",
        copy=False,
    )
    date_propagative_material = fields.Date(
        "Date",
        index=True,
        copy=False,
    )
    date_start = fields.Date(
        "Start date",
        index=True,
        copy=False,
    )
    date_end_expected = fields.Date(
        "Expected date end",
        index=True,
        copy=False,
    )
    date_end_real = fields.Date(
        "Actual end date",
        index=True,
        copy=False,
    )
