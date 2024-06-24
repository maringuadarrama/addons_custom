from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    documents_partner_settings = fields.Boolean(
        "Partners", related="company_id.documents_partner_settings", readonly=False
    )
    partner_folder = fields.Many2one(
        "documents.folder", "Partner default workspace", related="company_id.partner_folder", readonly=False
    )
    partner_tags = fields.Many2many(
        "documents.tag", "partner_tags_table", string="Partner Tags", related="company_id.partner_tags", readonly=False
    )

    @api.onchange("partner_folder")
    def on_partner_folder_change(self):
        if self.partner_folder != self.partner_tags.mapped("folder_id"):
            self.partner_tags = False
