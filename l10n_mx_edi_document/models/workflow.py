from odoo import _, models
from odoo.exceptions import UserError, ValidationError


class WorkflowActionRule(models.Model):
    _inherit = "documents.workflow.rule"

    def _get_document_record(self, document, res_model, document_type, attachment):
        if res_model != "account.move":
            return super()._get_document_record(document, res_model, document_type, attachment)
        account = document.customer_account_id if "customer" in document_type else document.vendor_account_id
        if not account and not document.analytic_account_id:
            return super()._get_document_record(document, res_model, document_type, attachment)

        attachment.mimetype = "application/xml"
        record_data = self._prepare_invoice_data(document_type, document)
        record_found = self.env["account.move"].l10n_mx_edi_documents_search_invoice(document, record_data)
        if record_found:
            self._attach_document_to_record(document, record_found)
            return {"success": True, "record": record_found}

        # Check if vendor bill requires a PO to be processed
        requires_po = self.env.ref("l10n_edi_document.documents_edi_requires_po_tag")
        if (
            res_model == "account.move"
            and record_data["move_type"] == "in_invoice"
            and requires_po in document.tag_ids
        ):
            return {
                "error": [_("Document requires Purchase Order to process.")],
                "record": False,
                "prevent_move_folder": True,
            }
        # Create new record
        record_data["l10n_edi_created_with_dms"] = True
        new_record = self.env[res_model].create(record_data)
        new_record.with_context(no_new_invoice=True).message_post(
            body=_("Created with DMS"), attachment_ids=[attachment.id]
        )
        self._attach_document_to_record(document, new_record)
        try:
            new_record = new_record.xml2record(
                default_account=account.id, analytic_account=document.analytic_account_id.id
            )
        except (UserError, ValidationError) as exe:
            return {"error": exe, "record": new_record}

        return {
            "success": True,
            "record": new_record,
        }

    def _prepare_invoice_data(self, document_type, document):
        values = super()._prepare_invoice_data(document_type, document)
        company = document.company_id or self.env.company
        if company.country_code != "MX":
            return values

        # Update the invoice type in Emitter == Receiver
        # TODO - If is necessary add a system parameter to this case
        cfdi = document.attachment_id.l10n_mx_edi_is_cfdi33()
        if cfdi is not None and cfdi.Emisor.get("Rfc") == cfdi.Receptor.get("Rfc"):
            values["move_type"] = {"out_invoice": "in_invoice", "out_refund": "in_refund"}.get(values["move_type"])
        if values["move_type"] in ("out_invoice", "out_refund") and document.customer_journal_id:
            values["journal_id"] = document.customer_journal_id.id
        if values["move_type"] in ("in_invoice", "in_refund") and document.vendor_journal_id:
            values["journal_id"] = document.vendor_journal_id.id
        if document.invoice_date:
            values["invoice_date"] = document.invoice_date
        return values

    def l10n_edi_documents_search_record(self, document, res_model, record_data):
        if res_model == "account.move":
            return self.env["account.move"].l10n_mx_edi_documents_search_invoice(document, record_data)
        if res_model == "account.payment":
            return self.env["account.payment"].l10n_mx_edi_documents_search_payment(document)
        return super().l10n_edi_documents_search_record(document, res_model, record_data)
