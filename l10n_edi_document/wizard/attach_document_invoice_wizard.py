from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class AttachDocumentInvoiceWizard(models.TransientModel):
    _name = "attach.document.invoice.wizard"
    _description = "Attach document to invoice"

    @api.model
    def default_get(self, fields_list):
        # OVERRIDE
        res = super().default_get(fields_list)
        move = self.env["account.move"].browse(self.env.context.get("active_id"))
        partner = move.partner_id.id
        res["partner_id"] = partner
        res["available_document_ids"] = [
            Command.set(
                self.env["documents.document"]
                .search([("in_finance_folder", "=", True), ("partner_id", "=", partner)])
                .ids
            )
        ]
        return res

    partner_id = fields.Many2one("res.partner", help="Partner related to the invoice.")
    available_document_ids = fields.Many2many(
        "documents.document",
        "attach_document_invoice_wizard_available_documents_rel",
        "document_id",
        "wizard_id",
        help="Documents available to be related to this invoice.",
    )
    document_ids = fields.Many2many(
        "documents.document",
        required=True,
        domain="[('id', 'in', available_document_ids)]",
        help="Document to relate on this invoice.",
    )

    def do_action(self):
        move = self.env["account.move"].browse(self.env.context["active_ids"])
        if move.edi_document_ids:
            raise UserError(_("This can only be used on invoices without EDI documents related."))

        if len(self.document_ids) > 1:
            raise UserError(_("To use this option, only could be used a document, please select the correct record."))

        if not self.document_ids:
            raise UserError(_("Please select a record."))

        res = self.l10n_edi_document_validation(move)
        if res.get("errors"):
            raise UserError("\n".join(res["errors"]))

        move._l10n_prepare_edi_document(self.document_ids.attachment_id)

        # Update attachment model
        self.document_ids.attachment_id.res_id = move.id
        self.document_ids.attachment_id.res_model = move._name

        return True

    @api.model
    def l10n_edi_document_validation(self, move):
        """Method to be overwritten from localization to validate document before attach
        :params: move
        :return: dict with two elements:
            record: invoice related
            validate: boolean indicating if validation was correct or not
        :rtype: dict
        """
        return {"validate": True}
