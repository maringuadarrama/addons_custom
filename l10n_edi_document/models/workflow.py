from os.path import splitext

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError


class WorkflowActionRuleAccount(models.Model):
    _inherit = ["documents.workflow.rule"]

    create_model = fields.Selection(selection_add=[("l10n_edi_document.edi.document", "EDI Document")])

    def create_record(self, documents=None):
        rv = super().create_record(documents=documents)
        if not self.create_model or not documents:
            return rv
        document_ids = []
        original_ids = documents.read(["res_id"])
        for document in documents.filtered(lambda doc: not doc.res_id or doc.res_model == "documents.document"):
            if splitext(document.name)[1].upper() != ".XML":
                continue
            attachment_id = document.attachment_id
            document_type, res_model = attachment_id.l10n_edi_document_type(document)
            if not document_type:
                self._move_document_to_incorrect_folder(document, original_ids)
                if isinstance(res_model, dict) and res_model.get("error"):
                    document.message_post(body=res_model.get("error"))
                continue
            result = self._get_document_record(document, res_model, document_type, attachment_id)
            record = result.get("record")
            errors = (record._get_edi_document_errors() if record else False) or result.get("error", False)
            if errors:
                document.message_post(body=", ".join(errors))
                if not result.get("prevent_move_folder"):
                    self._move_document_to_incorrect_folder(document, original_ids)
                # Reactive document
                if not document.active:
                    document.toggle_active()
                if record:
                    record.unlink()
                continue
            document_ids.append(record.id)
        if not document_ids:
            return rv
        action = {
            "type": "ir.actions.act_window",
            "res_model": record._name or res_model,
            "name": "EDI Documents",
            "view_id": False,
            "view_type": "list",
            "view_mode": "tree",
            "views": [(False, "list"), (False, "form")],
            "domain": [("id", "in", document_ids)],
            "context": self._context,
        }
        if len(documents) == 1 and record:
            view_id = record.get_formview_id()
            action.update(
                {
                    "view_type": "form",
                    "view_mode": "form",
                    "views": [(view_id, "form")],
                    "res_id": record.id,
                    "view_id": view_id,
                }
            )
        return action

    def _move_document_to_incorrect_folder(self, document, original_ids):
        """Move the document to incorrect folder"""
        incorrect_folder = self.env.ref("l10n_edi_document.documents_incorrect_edi_folder", False)
        rule_tc = self.env.ref("documents.documents_rule_finance_validate")
        document.tag_ids = False
        res_id = [doc["res_id"] for doc in original_ids if doc["id"] == document.id]
        document.sudo().write({"res_id": res_id[0] if res_id else False, "res_model": "documents.document"})
        rule_tc.apply_actions(document.ids)
        document.folder_id = incorrect_folder

    def _get_document_record(self, document, res_model, document_type, attachment):
        """Return the document generated from the document"""
        record_data = {"l10n_edi_created_with_dms": True}
        if res_model == "account.payment":
            record_data.update(self._prepare_payment_data(document_type, document))
        elif res_model == "account.move":
            record_data.update(self._prepare_invoice_data(document_type, document))
        attachment.mimetype = "application/xml"

        record_found = self.l10n_edi_documents_search_record(document, res_model, record_data)
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
        new_record = self.env[res_model].create(record_data)
        new_record.with_context(no_new_invoice=True).message_post(
            body=_("Created with DMS"), attachment_ids=[attachment.id]
        )
        self._attach_document_to_record(document, new_record)
        try:
            new_record = new_record.xml2record()
        except (UserError, ValidationError) as exe:
            return {"error": [str(exe)], "record": new_record}

        return {"success": True, "record": record_found or new_record}

    def _attach_document_to_record(self, document, record):
        attachment = document.attachment_id
        if attachment.res_model or attachment.res_id:
            attachment = attachment.copy()
            document.attachment_id = attachment.id
        attachment.write(
            {
                "res_model": record._name,
                "res_id": record.id,
            }
        )

    def _prepare_invoice_data(self, document_type, document):
        inv_type = {
            "customerI": "out_invoice",
            "customerE": "out_refund",
            "vendorI": "in_invoice",
            "vendorE": "in_refund",
        }.get(document_type)
        journal = self.env["account.move"].with_context(**{"default_move_type": inv_type})._search_default_journal()
        currency = journal.currency_id or journal.company_id.currency_id
        return {
            "move_type": inv_type,
            "currency_id": currency.id,
            "partner_id": document.partner_id.id,
        }

    def _prepare_payment_data(self, document_type, document):
        journal = self.env["account.journal"].search(
            [("type", "in", ("bank", "cash")), ("company_id", "=", document.company_id.id or self.env.company.id)],
            limit=1,
        )
        return {
            "payment_type": "inbound" if document_type == "customerP" else "outbound",
            "partner_type": "customer" if document_type == "customerP" else "supplier",
            "amount": 0,
            "journal_id": journal.id,
        }

    def l10n_edi_documents_search_record(self, document, res_model, record_data):
        """Implemented by l10n modules to check if a record already exists with the document data.
        :param document: Document record
        :param invoice_data: Dictionary with the invoice data
        :return: A single invoice record or False
        """
        return False
