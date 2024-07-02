from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_edi_import_customer_invoices = fields.Boolean(
        "Import Customer Invoices?",
        help="If the company is starting in Odoo, and must import the open customer "
        "invoices, mark this option to allow select the default journal and account to be used in Documents.",
    )
    l10n_edi_import_canceled_documents = fields.Boolean(
        "Import Canceled Documents?",
        help="If true, will to allow import canceled documents on the country portal, but will be generated and "
        "cancelled in Odoo.",
    )
