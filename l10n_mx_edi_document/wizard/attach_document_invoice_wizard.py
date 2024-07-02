from odoo import _, api, models
from odoo.exceptions import UserError


class AttachDocumentInvoiceWizard(models.TransientModel):
    _inherit = "attach.document.invoice.wizard"

    @api.model
    def l10n_edi_document_validation(self, move):
        result = super().l10n_edi_document_validation(move)
        if move.country_code != "MX":
            return result
        attachment = self.document_ids.attachment_id
        cfdi = attachment.l10n_mx_edi_is_cfdi33()
        if cfdi is None:
            raise UserError(_("Incorrect CFDI in the document"))
        cfdi_data = self.env["l10n_mx_edi.document"]._decode_cfdi_attachment(attachment.raw)
        xml_vat_emitter = cfdi_data.get("supplier_rfc", "").upper()
        xml_vat_receiver = cfdi_data.get("customer_rfc", "").upper()
        xml_total = float(cfdi_data.get("amount_total", 0))
        xml_currency = cfdi.get("Moneda", "")
        errors = []
        if move.partner_id.vat != xml_vat_emitter:
            errors.append(
                _(
                    "The VAT on the CFDI (%s) is not the same that in the invoice partner (%s).",
                    xml_vat_emitter,
                    move.partner_id.vat,
                )
            )
        if move.company_id.vat != xml_vat_receiver:
            errors.append(
                _(
                    "The VAT on the CFDI (%s) is not the same that in the invoice company (%s).",
                    xml_vat_receiver,
                    move.company_id.vat,
                )
            )
        if abs(move.amount_total - xml_total) > 1:
            errors.append(
                _(
                    "The amount total of the invoice (%s) is not the same that the XML file (%s).",
                    move.amount_total,
                    xml_total,
                )
            )
        if move.currency_id.name != xml_currency:
            errors.append(
                _(
                    "The currency on the CFDI (%s) is not the same that in the invoice (%s).",
                    xml_currency,
                    move.currency_id.name,
                )
            )
        if move.search(
            [
                ("l10n_mx_edi_cfdi_uuid", "=", cfdi_data.get("uuid")),
                ("move_type", "=", move.move_type),
                ("id", "!=", move.id),
            ],
            limit=1,
        ):
            errors.append(_("An invoice already exists with the same fiscal folio as the selected document."))
        if errors:
            return {"errors": errors}
        return result

    def do_action(self):
        """Inherit to update SAT status"""
        result = super().do_action()
        move = self.env["account.move"].browse(self.env.context["active_ids"])
        if move.country_code != "MX":
            return result
        sat_param = self.env["ir.config_parameter"].sudo().get_param("l10n_mx_edi_document.omit_sat_validation", False)
        if not sat_param:
            move.l10n_mx_edi_cfdi_try_sat()
        return result
