from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _domain_company_partner_folder(self):
        company = self.env.company
        return ["|", ("company_id", "=", False), ("company_id", "=", company.id)]

    documents_partner_settings = fields.Boolean()
    partner_folder = fields.Many2one(
        "documents.folder",
        "Partners Workspace",
        domain=_domain_company_partner_folder,
        default=lambda self: self.env.ref("documents_partner.documents_partner_folder", raise_if_not_found=False),
    )
    partner_tags = fields.Many2many("documents.tag", "partner_tags_table")
