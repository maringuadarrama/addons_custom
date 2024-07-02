import base64
from os.path import join

from odoo.tests.common import tagged
from odoo.tools import misc

from .common import L10nMxEDocumentsTransactionCase


@tagged("test_documents")
class TestDocument(L10nMxEDocumentsTransactionCase):
    def test_01_get_xml_data(self):
        invoice_xml = (
            misc.file_open(join("l10n_mx_edi_document", "tests", "invoice_240122.xml")).read().encode("UTF-8")
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "test_invoice.xml",
                "datas": base64.b64encode(invoice_xml),
                "description": "Mexican invoice",
            }
        )
        invoice_document = self.env["documents.document"].create(
            {"name": attachment.name, "folder_id": self.finance_folder.id, "attachment_id": attachment.id}
        )
        pdf_content = invoice_document.get_xml_data()
        pdf_expected_content = {
            "currency": "MXN",
            "cetificate": "B",
            "export": None,
            "date": "2022-01-24T19:06:09",
            "folio": None,
            "payment_form": "03",
            "payment_method": "PUE",
            "seal": "",
            "serie": None,
            "subtotal": "6275.86",
            "total": "7280.00",
            "expedition_place": "99100",
            "seal_number": "00001000000504465028",
            "voucher_type": "I",
            "concepts": [
                {
                    "quantity": "1",
                    "product_service_key": "91111603",
                    "unity_key": "E48",
                    "description": "SERVICIO DE ALIMENTACION DEL 3 AL 09 DE ENERO DEL 2022",
                    "import": "6275.86",
                    "identification_number": None,
                    "imp_object": None,
                    "unity": None,
                    "unit_price": "6275.86",
                }
            ],
            "emitter_vat": "EKU9003173C9",
            "emitter_name": "YourCompany",
            "emitter_fiscal_regime": "621",
            "receptor_vat": "XAXX010101000",
            "receptor_name": "Azure Interior",
            "receptor_fiscal_regime": None,
            "receptor_fiscal_address": None,
            "cfdi_usage": "G03",
            "fiscal_regime": "621",
            "certificate_sat_number": "00001000000504465028",
            "expedition": "99100",
            "sello_sat": """dZdQzOEIwunhV1ovwfkAgZK2OXv+w8+eA/VoU2Mskl5mm7vH+P0V67V0+dbdLEp0DClk1UjcPFiWuJt+
tmwza24uFYVXgv6ejYMld8Ln0Kc7gznEqR1RyaKdEI7uZer8sb5HkDK0I0wFKd+9d9u+Tc0pG+wi1ijg5Mq7/
65Va4cUp1jDNISdMmFdwvTp6JC1TABRf5n8CNm564qU1FFhavzgYd7zrsltnCzie//GKeOByVIsWFgjV8hXZ7
sEBx0i6dTQVwJr3iNb56PvCF1Pv0mostzhiboUWHYdkqcXYMRl7D+lxhReIu+DZFvWT9A4p92ethD7RsS9UJ2OOZSFmw==""",
            "cadena": """||1.1|AAA120F5-4B83-4206-B8C2-BFA24EBE56CD|2022-01-24T19:11:52|SAT970701NN3|
JEOVSk1qRJ91M0pJhtFwdVOv77gcVJdBBI0cs6SJ4NX6vL4k7gJfRju1BsNu/RZhWAP+8vEb8arUNFT25pnhcP
vsjO4OmxAWB+5RMdnUBqC8sl3JgE00kqMKlYQfZlAlTMPa5/jCdYLoOd7/cj1VkxryAs5yuEAWSO8ghSc4KU3vz7
wssar9OTU6j8qvms54WKG81+OPBUGltoInFMb1VjXjneORdLlUmx+bx40wO5yyJ5o/6oPmhG2zJ+RZKFPY6P/a1
LmBYXJL13n7kMUDUpZEpMr8drQruCyWqiaDGc1OHjhE/VS0aT/j8EndACy/sfXWCPfBHSRSamhUjxunBw==
|00001000000504465028||""",
            "total_transferred_taxes": "1004.14",
            "total_witheld_taxes": None,
            "emission_date_str": "2022-01-24 19:06:09",
            "certificate_provider_rfc": "SAT970701NN3",
        }
        pdf_expected_content["sello_sat"] = pdf_expected_content["sello_sat"].replace("\n", "")
        pdf_expected_content["cadena"] = pdf_expected_content["cadena"].replace("\n", "")
        self.assertEqual(
            pdf_content,
            pdf_expected_content,
            "ERROR! Expecting %s but get %s instead" % (pdf_expected_content, pdf_content),
        )
