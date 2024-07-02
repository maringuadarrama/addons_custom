from os.path import join

from odoo.tests import Form, tagged
from odoo.tools import misc

from .common import L10nMxEDocumentsTransactionCase


@tagged("mx_wizard_invoice", "post_install", "-at_install")
class TestAttachInvoiceDocument(L10nMxEDocumentsTransactionCase):
    def test_import_document_on_invoice(self):
        self.invoice_xml = (
            misc.file_open(join("l10n_mx_edi_document", "tests", "vendor_bill.xml")).read().encode("UTF-8")
        )
        document = self._prepare_document(self.invoice_xml)
        invoice = self.rule.create_record(document).get("res_id")
        invoice = self.env["account.move"].browse(invoice)

        bill = invoice.copy()
        invoice.l10n_mx_edi_document_ids.unlink()
        invoice.unlink()
        document = self._prepare_document(self.invoice_xml)

        bill.partner_id.vat = "XAXX010101000"

        ctx = {"active_model": invoice._name, "active_id": bill.id, "active_ids": bill.ids}
        wizard_form = Form(self.env["attach.document.invoice.wizard"].with_context(**ctx))
        wizard_form.document_ids = document
        wizard = wizard_form.save()
        wizard.do_action()

        self.assertTrue(bill.l10n_mx_edi_document_ids, "EDI document was not attached to the invoice.")
