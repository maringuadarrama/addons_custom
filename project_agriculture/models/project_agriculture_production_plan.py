from odoo import fields, models


class ProjectAgricultureProductionPlan(models.Model):
    _name = "project.agriculture.production.plan"

    name = fields.Char()
    species_id = fields.Many2one("project.agriculture.species")
    duration_delta = fields.Integer()


class ProjectAgricultureProductionPlanActivity(models.Model):
    _name = "project.agriculture.production.plan.activity"

    date = fields.Date(string="Date UTC")
