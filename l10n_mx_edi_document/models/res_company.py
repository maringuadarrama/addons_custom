from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_mx_edi_fuel_code_sat_ids = fields.Many2many(
        "product.unspsc.code", string="SAT fuel codes", domain=[("applies_to", "=", "product")]
    )
