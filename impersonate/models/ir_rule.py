from odoo import api, models

from .res_users import no_impostor


class IrRule(models.Model):
    _inherit = "ir.rule"

    @no_impostor
    @api.model_create_multi
    def create(self, vals_list):
        return super().create(vals_list)

    @no_impostor
    def write(self, values):
        return super().write(values)

    @no_impostor
    def unlink(self):
        return super().unlink()
