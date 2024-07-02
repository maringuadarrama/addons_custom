from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_edi_import_customer_invoices = fields.Boolean(
        "Import Customer Invoices?", readonly=False, related="company_id.l10n_edi_import_customer_invoices"
    )
    l10n_edi_import_canceled_documents = fields.Boolean(
        "Import Canceled Documents?", readonly=False, related="company_id.l10n_edi_import_canceled_documents"
    )
