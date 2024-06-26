from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.constrains("state", "l10n_mx_edi_document_ids")
    def _check_uuid_duplicated(self):
        for move in self:
            if move.l10n_mx_edi_cfdi_uuid:
                dupli = self.search(
                    [
                        ("id", "!=", move.id),
                        ("l10n_mx_edi_cfdi_uuid", "=", move.l10n_mx_edi_cfdi_uuid),
                        ("company_id", "=", move.company_id.id),
                    ]
                )
                if dupli:
                    msg = _("UUID duplicated %s for following invoices:\n", move.l10n_mx_edi_cfdi_uuid)
                    for rec in dupli:
                        msg += "-(%s) %s\n" % (rec.id, rec.name)
                        raise ValidationError(msg)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_mx_edi_is_ecc = fields.Boolean(help="Indicates that comes from a Fuel Account Statement complement")
