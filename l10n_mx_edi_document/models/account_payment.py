# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from lxml import etree

from odoo import _, api, fields, models
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    l10n_edi_created_with_dms = fields.Boolean(
        "Created with DMS?", copy=False, help="Is market if the document was created with DMS."
    )

    def l10n_mx_edi_documents_search_payment(self, document):
        cfdi = document.attachment_id.l10n_mx_edi_is_cfdi33()
        if cfdi is None:
            return False

        amount = 0
        invoices = self.env["account.move"]
        for element in self.l10n_mx_edi_get_payment_etree(cfdi):
            invoices |= invoices.search([("l10n_mx_edi_cfdi_uuid", "=", element.get("IdDocumento").upper().strip())])
            amount = amount or float(element.getparent().get("Monto"))

        payment_match = self.l10n_mx_edi_payment_match(
            self.env["l10n_mx_edi.document"]._decode_cfdi_attachment(etree.tostring(cfdi)).get("uuid"),
            amount,
            invoices,
        )
        if payment_match:
            self._attach_document_to_existing_payment(document, payment_match)
            return payment_match
        return False

    def _attach_document_to_existing_payment(self, document, record):
        # TODO: Review Odoo's new l10n_mx_edi.document model since account.edi.document is no longer used.
        record.message_post(body=_("The CFDI attached to was assigned with DMS."))
        document.attachment_id.res_id = record.id

    # Payment Functions

    def xml2record(self):
        """Use the last attachment in the payment (xml) and fill the payment
        data"""
        atts = self.env["ir.attachment"].search(
            [
                ("res_model", "=", self._name),
                ("res_id", "in", self.ids),
            ]
        )
        avoid_create = self.env["ir.config_parameter"].sudo().get_param("mexico_document_avoid_create_payment")
        without_record_folder = self.env.ref("l10n_edi_document.l10n_edi_document_documents_without_records", False)
        rule_tc = self.env.ref("documents.documents_rule_finance_validate")
        for attachment in atts:
            cfdi = attachment.l10n_mx_edi_is_cfdi33()
            if cfdi is None:
                continue
            amount = 0
            currency = self.env["res.currency"]
            invoices = self.env["account.move"]
            for elem in self.l10n_mx_edi_get_payment_etree(cfdi):
                parent = elem.getparent()
                if not amount:
                    amount += float(parent.get("Monto"))
                payment_method = self.env["l10n_mx_edi.payment.method"].search(
                    [("code", "=", parent.get("FormaDePagoP"))], limit=1
                )
                currency = currency.search([("name", "=", parent.get("MonedaP"))], limit=1)
                invoices |= invoices.search([("l10n_mx_edi_cfdi_uuid", "=", elem.get("IdDocumento").upper().strip())])
            document_type, _res_model = attachment.l10n_edi_document_type()
            payment_data = {
                "amount": amount,
                "l10n_mx_edi_payment_method_id": payment_method.id,
                "date": cfdi.get("Fecha").split("T")[0],
                "l10n_mx_edi_post_time": cfdi.get("Fecha").replace("T", " "),
                "currency_id": currency.id,
                "uuid": self.env["l10n_mx_edi.document"]._decode_cfdi_attachment(etree.tostring(cfdi)).get("uuid"),
                "payment_type": "inbound" if document_type == "customerP" else "outbound",
            }
            if avoid_create:
                attachment.res_model = False
                attachment.res_id = False
                documents = self.env["documents.document"].search([("attachment_id", "in", attachment.ids)])
                rule_tc.apply_actions(documents.ids)
                documents.folder_id = without_record_folder
                self.unlink()
                continue
            self.l10n_mx_edi_set_cfdi_partner(
                cfdi, currency, "inbound" if document_type == "customerP" else "outbound"
            )
            del payment_data["uuid"]
            self.write(payment_data)
            self.action_post()
            move = self.move_id.line_ids.filtered(
                lambda line: line.account_id.account_type in ("asset_receivable", "liability_payable")
            )
            for inv in invoices:
                lines = move
                lines |= inv.line_ids.filtered(
                    lambda line: line.account_id in lines.mapped("account_id") and not line.reconciled
                )
                lines.reconcile()
            attachment.copy({"res_model": "account.move", "res_id": self.move_id.id, "mimetype": "application/xml"})
        return self.exists()

    def l10n_mx_edi_payment_match(self, payment_uuid, amount, invoices):
        """Search a payment with the same data that payment_data and merge with
        it, to avoid 2 payments with the same data."""
        # TODO: This function is not working properly, it is not finding matching payments.
        payment_ids = self.env["account.payment"]
        inv_pay_rec_lines = invoices.mapped("line_ids").filtered(
            lambda line: line.account_type in ("asset_receivable", "liability_payable")
        )
        for field in ("debit", "credit"):
            for partial in inv_pay_rec_lines[f"matched_{field}_ids"]:
                counterpart_move = partial[f"{field}_move_id"].move_id
                if counterpart_move.payment_id or counterpart_move.statement_line_id:
                    payment_ids |= counterpart_move.payment_id
        for payment in payment_ids:
            uuid = not payment.l10n_mx_edi_cfdi_uuid or payment_uuid == payment.l10n_mx_edi_cfdi_uuid
            if not float_compare(amount, payment.amount, precision_digits=0) and uuid:
                return payment
        return False

    def l10n_mx_edi_set_cfdi_partner(self, cfdi, currency, payment_type):
        # TODO - make method generic
        self.ensure_one()
        partner = self.env["res.partner"]
        domain = []
        partner_cfdi = {}
        if payment_type == "inbound":
            partner_cfdi = cfdi.Receptor
        elif payment_type == "outbound":
            partner_cfdi = cfdi.Emisor
        vat = partner_cfdi.get("Rfc")
        if vat in ("XEXX010101000", "XAXX010101000"):
            domain.append(("name", "ilike", partner_cfdi.get("Nombre")))
        else:
            domain.append(("vat", "=", vat))
        domain.append(("is_company", "=", True))
        cfdi_partner = partner.search(domain, limit=1)
        currency_field = "property_purchase_currency_id" in partner._fields
        if currency_field:
            domain.append(("property_purchase_currency_id", "=", currency.id))
        if currency_field and not cfdi_partner:
            domain.pop()
            cfdi_partner = partner.search(domain, limit=1)
        if not cfdi_partner:
            domain.pop()
            cfdi_partner = partner.search(domain, limit=1)
        if not cfdi_partner:
            domain.pop()
            cfdi_partner = partner.search(domain, limit=1)
        if not cfdi_partner:
            cfdi_partner = partner.create(
                {
                    "name": partner_cfdi.get("Nombre"),
                    "vat": partner_cfdi.get("Rfc"),
                    "country_id": False,  # TODO
                }
            )
            cfdi_partner.message_post(body=_("This record was generated from DMS"))
        self.partner_id = cfdi_partner

    @api.model
    def l10n_mx_edi_get_payment_etree(self, cfdi):
        """Get the Complement node from the cfdi."""
        # TODO: Remove this method
        if not hasattr(cfdi, "Complemento"):
            return None
        attribute = "//pago10:DoctoRelacionado"
        namespace = {"pago10": "http://www.sat.gob.mx/Pagos"}
        node = cfdi.Complemento.xpath(attribute, namespaces=namespace)
        if not node:
            attribute = "//pago20:DoctoRelacionado"
            namespace = {"pago20": "http://www.sat.gob.mx/Pagos20"}
            node = cfdi.Complemento.xpath(attribute, namespaces=namespace)
        return node

    def _get_edi_document_errors(self):
        errors = []
        if self.country_code != "MX":
            return errors
        if not self.company_id.l10n_mx_edi_pac_test_env and self.l10n_mx_edi_cfdi_sat_state != "valid":
            errors.append(
                "The SAT status of this document is not valid in the SAT. (Is %s)" % self.l10n_mx_edi_cfdi_sat_state
            )
        return errors
