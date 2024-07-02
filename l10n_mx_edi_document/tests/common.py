import base64
import os
from os.path import join

from odoo.tests.common import TransactionCase
from odoo.tools import misc


class L10nMxEDocumentsTransactionCase(TransactionCase):
    def setUp(self):
        super().setUp()

        self.invoice_xml = misc.file_open(join("l10n_mx_edi_document", "tests", "invoice.xml")).read().encode("UTF-8")
        self.finance_folder = self.env.ref("documents.documents_finance_folder")
        self.rule = self.env.ref("l10n_edi_document.edi_document_rule")

        self.env["l10n_mx_edi.certificate"].search([]).unlink()
        self.certificate = self.env["l10n_mx_edi.certificate"].create(
            {
                "content": base64.encodebytes(
                    misc.file_open(
                        os.path.join("l10n_mx_edi", "demo", "pac_credentials", "certificate.cer"), "rb"
                    ).read()
                ),
                "key": base64.encodebytes(
                    misc.file_open(
                        os.path.join("l10n_mx_edi", "demo", "pac_credentials", "certificate.key"), "rb"
                    ).read()
                ),
                "password": "12345678a",
            }
        )
        self.certificate._check_credentials()
        self.env.user.company_id = self.env.ref("l10n_mx.demo_company_mx")

    def _prepare_document(self, datas):
        attachment = self.env["ir.attachment"].create(
            {
                "name": "invoice.xml",
                "datas": base64.b64encode(datas),
                "description": "Mexican invoice",
            }
        )
        return self.env["documents.document"].create(
            {"name": attachment.name, "folder_id": self.finance_folder.id, "attachment_id": attachment.id}
        )
