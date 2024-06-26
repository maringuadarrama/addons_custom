import base64
import hashlib
import logging
from datetime import datetime, timedelta

import requests
from lxml import etree, objectify
from OpenSSL import crypto

from odoo import _, models, tools
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round

TYPE_CFDI22_TO_CFDI33 = {
    "ingreso": "I",
    "egreso": "E",
    "traslado": "T",
    "nomina": "N",
    "pago": "P",
}
MXWS_ERROR_TYPE = [
    ("0", "Token invalido."),
    ("1", "Aceptada"),
    ("2", "En proceso"),
    ("3", "Terminada"),
    ("4", "Error"),
    ("5", "Rechazada"),
    ("6", "Vencida"),
]


_logger = logging.getLogger(__name__)


class L10nMxEdiDocument(models.Model):
    _inherit = "l10n_mx_edi.document"

    def _xml2capitalize(self, xml):
        """Receive 1 lxml etree object and change all attrib to Capitalize."""

        def recursive_lxml(element):
            for attrib, value in element.attrib.items():
                new_attrib = "%s%s" % (attrib[0].upper(), attrib[1:])
                element.attrib.update({new_attrib: value})
            for child in element.getchildren():
                child = recursive_lxml(child)
            return element

        return recursive_lxml(xml)

    def _convert_cfdi32_to_cfdi33(self, cfdi_etree):
        """Convert a xml from cfdi32 to cfdi33
        :param xml: The xml 32 in lxml.objectify object
        :return: A xml 33 in lxml.objectify object
        """
        if cfdi_etree.get("Version") in ("3.3", "4.0"):
            return cfdi_etree
        cfdi_etree = self._xml2capitalize(cfdi_etree)
        cfdi_etree.attrib.update(
            {
                "TipoDeComprobante": TYPE_CFDI22_TO_CFDI33[cfdi_etree.attrib["tipoDeComprobante"]],
                "MetodoPago": "PPD",
            }
        )
        return cfdi_etree

    def get_et_complemento(
        self,
        cfdi_etree,
        attribute="tfd:TimbreFiscalDigital[1]",
        namespaces=None,
    ):
        """Helper to extract relevant data from CFDI 3.3 nodes.
        By default this method will retrieve tfd, Adjust parameters for other nodes
        :param cfdi_etree:  The cfdi etree object.
        :param attribute:   tfd.
        :param namespaces:  tfd.
        :return:            A python dictionary.
        """
        if not namespaces:
            namespaces = {"tfd": "http://www.sat.gob.mx/TimbreFiscalDigital"}
        if not hasattr(cfdi_etree, "Complemento"):
            return {}
        node = cfdi_etree.Complemento.xpath(attribute, namespaces=namespaces)
        return node[0] if node else {}

    def get_et_import_type(self, cfdi_etree):
        import_type = "issued" if self.env.company.vat == cfdi_etree.Emisor.get("Rfc", "") else "received"
        cfdi_type = cfdi_etree.get("TipoDeComprobante", False)
        move_type = None
        if import_type == "received":
            received_move_type = {"I": "in_invoice", "E": "in_refund", "N": "entry", "P": "entry"}
            move_type = received_move_type.get(cfdi_type, "in_invoice")
        elif import_type == "issued":
            issued_move_type = {"I": "out_invoice", "E": "out_refund", "N": "entry", "P": "entry"}
            move_type = issued_move_type.get(cfdi_type, "out_invoice")
        return import_type, move_type

    def l10n_mx_edi_get_fuel_codes(self):
        """Return the codes that can be used in FUEL"""
        return [str(r) for r in range(15101500, 15101513)]

    def get_taxes_to_omit(self):
        """Some taxes are not found in the system, but is correct, because those
        taxes should be added in the invoice like expenses.
        To make dynamic this a system parameter can be added with the name:
        \"l10n_mx_taxes_for_expense\", then set the tax name. If many taxes split
        the names by \",\" """
        taxes = self.env["ir.config_parameter"].sudo().get_param("l10n_mx_taxes_for_expense", False)
        if taxes:
            return taxes.split(",")
        return ["ISH", "TUA", "ISAN"]

    def collect_taxes(self, line_tax_element):
        """Get tax data of the Impuesto node of the xml and return
        dictionary with taxes datas
        :param taxes_xml: Impuesto node of xml
        :type taxes_xml: etree
        :return: A list with the taxes data dict
        :rtype: list
        """
        taxes = []
        tax_codes = {"001": "ISR", "002": "IVA", "003": "IEPS"}
        for rec in line_tax_element:
            tax_xml = rec.get("Impuesto", "")
            tax_xml = tax_codes.get(tax_xml, tax_xml)
            amount_xml = float(rec.get("Importe", "0.0"))
            rate_xml = float_round(float(rec.get("TasaOCuota", "0.0")) * 100, 4)
            if "Retenciones" in rec.getparent().tag:
                amount_xml = amount_xml * -1
                rate_xml = rate_xml * -1
            taxes.append(
                {
                    "tax": tax_xml,
                    "factor": rec.get("TipoFactor", False),
                    "rate": rate_xml,
                    "amount": amount_xml,
                }
            )
        return taxes

    def search_taxes(self, taxes, type_tax_use="purchase"):
        """Return the Odoo taxes based on the dict with taxes data"""
        tax_list = []
        for tax in taxes:
            tax_group_id = self.env["account.tax.group"].search(
                [("country_id", "=", self.env.ref("base.mx").id), ("name", "ilike", tax["tax"])]
            )
            tax_name = "%s %s" % (tax["tax"], tax["rate"])
            tax_factor = tax["factor"] if tax["factor"] else "Tasa"
            domain = [
                ("active", "=", True),
                ("tax_group_id", "in", tax_group_id.ids),
                ("type_tax_use", "=", type_tax_use),
                ("name", "ilike", tax_name),
                ("l10n_mx_tax_type", "=", tax_factor),
                ("company_id", "=", self.env.company.id),
            ]
            if -10.67 <= tax["rate"] <= -10.66:
                domain.append(("amount", "<=", -10.66))
                domain.append(("amount", ">=", -10.67))
            else:
                domain.append(("amount", "=", tax["rate"]))
            tax_exist = self.env["account.tax"].search(domain, limit=1, order="id asc")
            if not tax_exist:
                # self.message_post(body=_("The tax %s cannot be found") % name)
                continue
            # tax_account = tax_exist.invoice_repartition_line_ids.filtered(lambda rec: rec.repartition_type == "tax")
            # if not tax_account:
            #    self.message_post(body=_("Please configure the tax account in the tax %s") % name)
            #    continue
            tax_list.append(tax_exist.id)
        return tax_list

    def prepare_line_taxes(self, line):
        if not hasattr(line, "Impuestos"):
            return []
        taxes = []
        if hasattr(line.Impuestos, "Traslados"):
            taxes = self.collect_taxes(line.Impuestos.Traslados.Traslado)
        if hasattr(line.Impuestos, "Retenciones"):
            taxes += self.collect_taxes(line.Impuestos.Retenciones.Retencion)
        return taxes

    def get_et_taxes(self, cfdi_etree):
        """:param cfdi_etree:  The cfdi etree object.
        :return:            A python dictionary.
        """
        if not hasattr(cfdi_etree, "Impuestos"):
            return {}

        import_type, _move_type = self.get_et_import_type(cfdi_etree)
        type_tax_use = "sale" if import_type == "issued" else "purchase"
        tax_obj = self.env["account.tax"]
        taxes_dict = {
            "wrong_taxes": [],
            "withno_account": [],
            "taxes_ids": {},
            "total_amount": 0.0,
            "total_amount_retained": 0.0,
        }

        if cfdi_etree.get("Version") == "3.2":
            if hasattr(cfdi_etree.Impuestos, "Traslados"):
                for tax in cfdi_etree.Impuestos.Traslados.Traslado:
                    taxes_dict["total_amount"] += float(tax.get("importe", 0.0))
                    tax_name = tax.get("impuesto")
                    tax_rate = float(tax.get("tasa"))
                    tax_group_id = self.env["account.tax.group"].search([("name", "ilike", tax_name)])
                    tax_domain = [
                        ("type_tax_use", "=", type_tax_use),
                        ("company_id", "=", self.env.company.id),
                        ("tax_group_id", "in", tax_group_id.ids),
                        ("amount_type", "=", "percent"),
                        ("amount", "=", tax_rate),
                    ]
                    tax_exist = tax_obj.search(tax_domain, limit=1)
                    if not tax_exist:
                        taxes_dict["wrong_taxes"].append("%s(%s%%)" % (tax_name, tax_rate))
                        continue

                    repartition_id = self.env["account.tax.repartition.line"].search(
                        [("tax_id", "=", tax.id), ("repartition_type", "=", "tax"), ("account_id", "!=", False)],
                        limit=1,
                    )
                    account_id = repartition_id.account_id.id if repartition_id else False
                    if not account_id:
                        taxes_dict["withno_account"].append(tax_name)

                    taxes_dict["taxes_ids"]["old"] = [(0, 0, {"tax_id": tax.id, "name": tax_name})]

            if hasattr(cfdi_etree.Impuestos, "Retenciones"):
                for rec in cfdi_etree.Impuestos.Retenciones.Retencion:
                    taxes_dict["total_amount_retained"] += float(rec.get("importe", 0.0))

        if cfdi_etree.get("Version") in ("3.3", "4.0"):
            taxes_dict["total_amount"] += float(cfdi_etree.Impuestos.get("TotalImpuestosTrasladados", "0.0"))
            taxes_dict["total_amount_retained"] += float(cfdi_etree.Impuestos.get("TotalImpuestosRetenidos", 0.0))

        for index, line in enumerate(cfdi_etree.Conceptos.Concepto):
            if not hasattr(line, "Impuestos"):
                continue
            taxes_dict["taxes_ids"][index] = []
            collected_taxes = self.prepare_line_taxes(line)
            for tax in collected_taxes:
                tax_name = "%s %s" % (tax["tax"], tax["rate"])
                domain = [
                    ("active", "=", True),
                    ("type_tax_use", "=", type_tax_use),
                    ("name", "ilike", tax_name),
                    ("l10n_mx_tax_type", "=", tax["factor"]),
                ]
                if type_tax_use == "purchase" and -10.67 <= tax["rate"] <= -10.66:
                    domain.append(("amount", "<=", -10.66))
                    domain.append(("amount", ">=", -10.67))
                else:
                    domain.append(("amount", "=", tax["rate"]))
                tax_exist = tax_obj.search(domain, limit=1, order="id asc")
                if not tax_exist:
                    taxes_dict["wrong_taxes"].append(tax_name)
                    continue

                tax_account = tax_exist.invoice_repartition_line_ids.filtered(
                    lambda rec: rec.repartition_type == "tax"
                )
                if not tax_account:
                    taxes_dict["withno_account"].append(tax_name)
                    continue

                tax["id"] = tax_exist.id
                tax["name"] = tax_name
                taxes_dict["taxes_ids"][index].append(tax)

        return taxes_dict

    def get_et_local_taxes(self, cfdi_etree):
        """:param cfdi_etree:  The cfdi etree object.
        :return:            A python dictionary.
        """
        local_taxes = self.get_et_complemento(
            cfdi_etree, "implocal:ImpuestosLocales", {"implocal": "http://www.sat.gob.mx/implocal"}
        )
        if not local_taxes:
            return local_taxes

        import_type, _move_type = self.get_et_import_type(cfdi_etree)
        type_tax_use = "sale" if import_type == "issued" else "purchase"
        tax_obj = self.env["account.tax"]
        taxes_to_omit = self.get_taxes_to_omit()
        taxes_dict = {
            "wrong_taxes": [],
            "withno_account": [],
            "taxes_ids": [],
            "total_amount": 0.0,
            "total_amount_retained": 0.0,
        }

        if hasattr(local_taxes, "RetencionesLocales"):
            for tax in local_taxes.RetencionesLocales:
                tax_name = tax.get("ImpLocRetenido")
                tax_rate = float(tax.get("TasadeRetencion")) * -100
                tax_dict = {"name": tax_name, "amount": float(tax.get("Importe")) * -1, "for_expenses": True}
                if tax_name in taxes_to_omit:
                    taxes_dict["taxes_ids"].append(tax_dict)
                    continue

                tax_exist = tax_obj.search(
                    [("type_tax_use", "=", type_tax_use), ("name", "ilike", tax_name), ("amount", "=", tax_rate)],
                    limit=1,
                )
                if not tax_exist:
                    taxes_dict["wrong_taxes"].append(tax_name)
                    continue

                account_id = tax_exist.invoice_repartition_line_ids.filtered(lambda rec: rec.repartition_type == "tax")
                if not account_id.id:
                    taxes_dict["withno_account"].append(tax_name)
                    continue

                tax_dict["tax_id"] = tax_exist.id
                tax_dict["account_id"] = account_id.id
                tax_dict["for_expenses"] = False

                taxes_dict["taxes_ids"].append(tax_dict)
                taxes_dict["total_amount"] = taxes_dict["total_amount"] + float(local_taxes.get("Importe"))

        if hasattr(local_taxes, "TrasladosLocales"):
            for tax in local_taxes.TrasladosLocales:
                tax_name = tax.get("ImpLocTrasladado")
                tax_rate = float(tax.get("TasadeTraslado")) * 100
                tax_dict = {"name": tax_name, "amount": float(tax.get("Importe")), "for_expenses": True}
                if tax_name in taxes_to_omit:
                    taxes_dict["taxes_ids"].append(tax_dict)
                    continue

                tax_exist = tax_obj.search(
                    [("type_tax_use", "=", type_tax_use), ("name", "ilike", tax_name), ("amount", "=", tax_rate)],
                    limit=1,
                )
                if not tax_exist:
                    taxes_dict["wrong_taxes"].append(tax_name)
                    continue

                account_id = tax_exist.invoice_repartition_line_ids.filtered(lambda rec: rec.repartition_type == "tax")
                if not account_id:
                    taxes_dict["withno_account"].append(tax_name)
                    continue

                tax_dict["tax_id"] = tax_exist.id
                tax_dict["account_id"] = account_id.id
                tax_dict["for_expenses"] = False

                taxes_dict["taxes_ids"].append(tax_dict)
                taxes_dict["total_amount"] = taxes_dict["total_amount"] + float(tax.get("Importe"))

        return taxes_dict

    def get_et_serie_folio(self, cfdi_etree):
        """:return:        Serie + Folio
        :rtype:         str
        """
        xml_serie = cfdi_etree.get("Serie", False)
        xml_folio = cfdi_etree.get("Folio", False)
        xml_sefo = ""
        if xml_serie or xml_folio:
            xml_sefo = "%s%s" % (cfdi_etree.get("Serie", ""), cfdi_etree.get("Folio", ""))
        return xml_sefo

    def get_et_datetime(self, cfdi_etree):
        """:return:        CFDI date
        :rtype:         datetime
        """
        date = cfdi_etree.get("Fecha", cfdi_etree.get("FechaTimbrado", ""))
        return datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")

    def get_et_currency(self, cfdi_etree):
        """:return:        Currency in ISO? code
        :rtype:         str
        """
        currency = cfdi_etree.get("Moneda", "MXN")
        mxn = [
            "mxp",
            "mxn",
            "mn",
            "peso",
            "pesos",
            "peso mexicano",
            "pesos mexicanos",
            "nacional",
            "nal",
            "m.n.",
            "$",
            "2013",
        ]
        usd = ["dolar", "dólar", "dólares", "dolares"]
        currency = "MXN" if currency.lower() in mxn else currency
        currency = "USD" if currency.lower() in usd else currency
        return currency

    def get_related_uuids_dict(self, cfdi_etree):
        """:return:        {"type": TipoRelacion code, "uuids": []}
        :rtype:         dict
        """
        if not hasattr(cfdi_etree, "CfdiRelacionados"):
            return False

        res = {"type": cfdi_etree.CfdiRelacionados.get("TipoRelacion", "01"), "uuids": []}
        for related_uuid in cfdi_etree.CfdiRelacionados.CfdiRelacionado:
            res["uuids"].append(related_uuid.get("UUID").upper())
        return res

    def check_objectify_xml(self, xml64):
        """Helper to decode and lxml objectify an xml b64 file.
        :param xml64:       An xml b64 file.
        :return:            etree object or False
        :rtype:             etree object or False
        """
        is_cfdi, is_cfdi_signed, cfdi_etree = False, False, False
        try:
            if isinstance(xml64, bytes):
                xml64 = xml64.decode()
            xml_str = base64.b64decode(xml64)
            objectify.fromstring(xml_str)
        except etree.XMLSyntaxError as e:
            _logger.warning(str(e))
            return is_cfdi, is_cfdi_signed, cfdi_etree

        xml_str = (
            xml_str.replace(b"xmlns:schemaLocation", b"xsi:schemaLocation")
            .replace(b"data:text/xml;base64,", b"")
            .replace(b"o;?", b"")
            .replace(b"\xef\xbf\xbd", b"")
        )
        cfdi_etree = objectify.fromstring(xml_str)
        tags = [
            "{http://www.sat.gob.mx/cfd/3}Comprobante",
            "{http://www.sat.gob.mx/cfd/4}Comprobante",
        ]
        is_cfdi = cfdi_etree.tag in tags
        if is_cfdi:
            cfdi_etree = self._convert_cfdi32_to_cfdi33(cfdi_etree)
            is_cfdi_signed = bool(self.get_et_complemento(cfdi_etree).get("UUID"))
        return is_cfdi, is_cfdi_signed, cfdi_etree

    def _prepare_cfdi_dict(self, xml64, mode="simple"):
        """Helper to extract relevant data from the CFDI
        and turn it into dictionary.
        :param xml:     The xml b64 file.
        :return:        A python dictionary.
        :rtype:         dict
        """
        _is_cfdi, _is_cfdi_signed, cfdi_etree = self.check_objectify_xml(xml64)
        tfd_node = self.get_et_complemento(cfdi_etree)
        import_type, move_type = self.get_et_import_type(cfdi_etree)
        cfdi_type = cfdi_etree.get("TipoDeComprobante", False)
        cfdi_dict = {
            "import_type": import_type,
            "cfdi_type": cfdi_type,
            "move_type": move_type,
            "issuer_vat": cfdi_etree.Emisor.get("Rfc", ""),
            "issuer_name": cfdi_etree.Emisor.get("Nombre", ""),
            "fiscal_regime": cfdi_etree.Emisor.get("RegimenFiscal", ""),
            "receiver_vat": cfdi_etree.Receptor.get("Rfc", ""),
            "receiver_name": cfdi_etree.Receptor.get("Nombre", ""),
            "usage": cfdi_etree.Receptor.get("UsoCFDI", False),
            "version": cfdi_etree.get("Version", ""),
            "date": self.get_et_datetime(cfdi_etree),
            "sefo": self.get_et_serie_folio(cfdi_etree),
            "currency": self.get_et_currency(cfdi_etree),
            "amount_total": float(cfdi_etree.get("Total", 0)),
            "amount_subtotal": float(cfdi_etree.get("SubTotal", 0)),
            "global_discount": float(cfdi_etree.get("Descuento", 0)),
            "payment_form": cfdi_etree.get("FormaDePago", cfdi_etree.get("FormaPago")),
            "payment_method": cfdi_etree.get("MetodoPago"),
            "payment_term": cfdi_etree.get("CondicionesDePago", False),
            "bank_account": cfdi_etree.get("NumCtaPago"),
            "sello": cfdi_etree.get("sello", cfdi_etree.get("Sello", "No identificado")),
            "certificate_number": cfdi_etree.get("noCertificado", cfdi_etree.get("NoCertificado")),
            "expedition": cfdi_etree.get("LugarExpedicion"),
            "related_uuids_dict": self.get_related_uuids_dict(cfdi_etree),
            "lines": cfdi_etree.Conceptos.Concepto,
            "taxes": self.get_et_taxes(cfdi_etree),
            "local_taxes": self.get_et_local_taxes(cfdi_etree),
            # TFD
            "stamp_date": self.get_et_datetime(tfd_node) if tfd_node else "",
            "certificate_sat_number": tfd_node.get("NoCertificadoSAT") if tfd_node else "not signed",
            "uuid": tfd_node.get("UUID", "").upper().strip() if tfd_node else "not signed",
            "sello_sat": tfd_node.get("SelloSAT") if tfd_node else "not signed",
            "cfdi_etree": cfdi_etree,
        }

        if mode == "complete":
            complements = [
                ("payslip", "nomina:Nomina", {"nomina": "http://www.sat.gob.mx/nomina"}),
                ("payslip", "nomina12:Nomina", {"nomina12": "http://www.sat.gob.mx/nomina12"}),
                (
                    "fuel_statement",
                    "ecc12:EstadoDeCuentaCombustible",
                    {"ecc12": "http://www.sat.gob.mx/EstadoDeCuentaCombustible12"},
                ),
            ]
            for complement in complements:
                node = self.get_et_complemento(cfdi_etree, attribute=complement[1], namespaces=complement[2])
                if node:
                    cfdi_dict.update({complement[0]: node})
                    break

        return cfdi_dict

    def _create_cfdi_attachment(self, cfdi_filename, description, move, data):
        attachment_obj = self.env["ir.attachment"]
        values = {
            "name": cfdi_filename,
            "res_id": move.id,
            "res_model": move._name,
            "type": "binary",
            "datas": data,
            "mimetype": "application/xml",
            "description": description,
        }
        attachment = attachment_obj.search(
            [
                ("name", "=", cfdi_filename),
                ("res_model", "=", move._name),
                ("res_id", "=", move.id),
                ("type", "=", "binary"),
            ]
        )
        if attachment:
            attachment.write(values)
            return attachment[0]
        return attachment_obj.create(values)

    def _create_move_cfdi_attachment(self, invoice, data):
        cfdit = {
            "in_invoice": "Bill",
            "in_refund": "Bill-Refund",
            "out_invoice": "Invoice",
            "out_refund": "Invoice-Refund",
        }
        cfdi_filename = (
            "%s-%s-MX-%s.xml" % (invoice.journal_id.code, invoice.payment_reference, cfdit.get(invoice.move_type))
        ).replace("/", "")
        description = _(
            "Mexican %s CFDI generated for the %s document.",
            cfdit.get(invoice.move_type),
            invoice.name,
        )

        return self._create_cfdi_attachment(cfdi_filename, description, invoice, data)

    def search_partner_ecc12(self, line_ecc12_element):
        partner_obj = self.env["res.partner"]
        domain_partner = [("vat", "=", line_ecc12_element.get("Rfc"))]
        partner_exist = partner_obj.search(domain_partner, limit=1, order="id asc")
        if not partner_exist:
            partner_exist = partner_obj.sudo().create(
                {
                    "name": line_ecc12_element.get("ClaveEstacion"),
                    "vat": line_ecc12_element.get("Rfc"),
                    "company_type": "company",
                    "country_id": self.env.ref("base.mx").id,
                }
            )
            msg = _(
                "This partner was created when importing a CFDI file. Please verify that Partner datas are correct."
            )
            partner_exist.message_post(body=msg)
        return partner_exist

    def search_partner(self, cfdi_etree):
        partner_obj = self.env["res.partner"]
        import_type, _move_type = self.get_et_import_type(cfdi_etree)
        domain_partner = []
        if import_type == "received":
            name = cfdi_etree.Emisor.get("Nombre", "")
            vat = cfdi_etree.Emisor.get("Rfc", "")
            domain_partner.append(("vat", "=", vat))
        elif import_type == "issued":
            name = cfdi_etree.Receptor.get("Nombre", "")
            vat = cfdi_etree.Receptor.get("Rfc", "")
            domain_partner.append(("vat", "=", vat))
        partner = partner_obj.search(domain_partner, limit=1, order="id asc")
        if not partner:
            vals = {"company_type": "company", "country_id": self.env.ref("base.mx").id, "name": name, "vat": vat}
            partner = partner_obj.sudo().create(vals)
            msg = _(
                "This partner was created when importing a CFDI file. Please verify that Partner datas are correct."
            )
            partner.message_post(body=msg)
        return partner

    def prepare_move_lines_ecc12(self, cfdi_etree):
        ecc12 = self.get_et_complemento(
            cfdi_etree,
            "//ecc12:EstadoDeCuentaCombustible",
            {"ecc12": "http://www.sat.gob.mx/EstadoDeCuentaCombustible12"},
        )
        if not ecc12:
            return False

        product = self.env["ir.config_parameter"].sudo().get_param("l10n_mx_product_ecc12", False)
        if product:
            product = self.env["product.product"].browse(int(product))
            account = (product.property_account_expense_id or product.categ_id.property_account_expense_categ_id).id
        else:
            fuel_codes = self.env["product.unspsc.code"].search(
                [("applies_to", "=", "product"), ("code", "in", (self.l10n_mx_edi_get_fuel_codes()))]
            )
            product = self.env["product.product"].search([("unspsc_code_id", "in", fuel_codes.ids)], limit=1)
            account = (product.property_account_expense_id or product.categ_id.property_account_expense_categ_id).id

        move_line_ids = []
        # analytic_distribution = self.env["account.analytic.distribution.model"]._get_distribution({
        #    "product_id": product_exist.id if product_exist else False,
        #    "product_categ_id": product_exist.categ_id.id if product_exist else False,
        #    "partner_id": partner.id,
        #    "partner_category_id": partner.category_id.ids,
        #    "account_prefix": account_id.code,
        #    "company_id": company.id,
        # })
        tax_rate_exempt = self.env["account.tax"].search(
            [
                ("name", "=ilike", "IVA" + "%" + "exento"),
                ("l10n_mx_tax_type", "=", "Exento"),
                ("amount_type", "=", "percent"),
                ("amount", "=", 0),
                ("type_tax_use", "=", "purchase"),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )

        for rec in ecc12.Conceptos.ConceptoEstadoDeCuentaCombustible:
            taxes = self.collect_taxes(rec.Traslados.Traslado) if hasattr(rec, "Traslados") else []
            tax = taxes[0] if taxes else {}
            price = round(tax.get("amount") / (tax.get("rate") / 100), 2)
            taxes = self.search_taxes(taxes)
            partner = self.search_partner_ecc12(rec)
            move_line_ids.append(
                (
                    0,
                    0,
                    {
                        "name": _(
                            "Station: %s - Operation: %s - Identifier: %s",
                            rec.get("ClaveEstacion"),
                            rec.get("FolioOperacion"),
                            rec.get("Identificador"),
                        ),
                        "product_id": product.id,
                        "product_uom_id": product.uom_id.id,
                        "account_id": account,
                        # "analytic_distribution": ,
                        "quantity": float(rec.get("Cantidad", "0.0")),
                        "price_unit": price / float(rec.get("Cantidad", "0.0")),
                        "tax_ids": taxes,
                        "l10n_mx_edi_is_ecc": True,
                        "partner_id": partner.id,
                    },
                )
            )
            move_line_ids.append(
                (
                    0,
                    0,
                    {
                        "name": _("Fuel - IEPS"),
                        "account_id": account,
                        # "analytic_distribution": ,
                        "quantity": 1.0,
                        "price_unit": float(rec.get("Importe", 0)) - price,
                        "tax_ids": tax_rate_exempt.ids,
                        "l10n_mx_edi_is_ecc": True,
                        "partner_id": partner.id,
                    },
                )
            )
        return move_line_ids

    def prepare_move_lines(self, cfdi_etree, import_type, journal):
        ecc12_lines = self.prepare_move_lines_ecc12(cfdi_etree)
        if ecc12_lines:
            return ecc12_lines

        prod_obj = self.env["product.product"]
        prod_sup_obj = self.env["product.supplierinfo"]
        sat_code_obj = self.env["product.unspsc.code"]
        uom_obj = self.env["uom.uom"]

        move_line_ids = []

        product_create = self._context.get("product_create", False)
        account_id = self._context.get("account_id", False)
        # _logger.info(account_id)

        for line in cfdi_etree.Conceptos.Concepto:
            line_amount = float(line.get("Importe", "0.0"))
            line_discount = 0.0
            if line.get("Descuento"):
                line_discount = (float(line.get("Descuento")) / line_amount) * 100
            if not line.get("Descuento") and cfdi_etree.get("Descuento", 0.0):
                line_discount = float(cfdi_etree.get("Descuento", 0.0)) * 100 / float(cfdi_etree.get("SubTotal", 0.0))
            line_price = float(line.get("ValorUnitario"))
            line_quantity = float(line.get("Cantidad"))

            uom = line.get("Unidad", "")
            sat_uom_exist = False
            xml_uom_sat_code = line.get("ClaveUnidad", False)
            if xml_uom_sat_code:
                sat_uom_exist = sat_code_obj.search(
                    [("code", "=", xml_uom_sat_code), ("applies_to", "=", "uom")], limit=1
                )
            uom_domain = (
                [("name", "=ilike", uom)] if not sat_uom_exist else [("unspsc_code_id", "=", sat_uom_exist.id)]
            )
            uom_exist = uom_obj.with_context(lang="es_MX").search(uom_domain, limit=1)
            uom = uom_exist if uom_exist else self.env.ref("uom.product_uom_unit")

            line_name = line.get("Descripcion", "")
            if line_name.splitlines():
                line_name = line_name.splitlines()[0]
            product_exist = prod_sup_obj.search([("product_name", "=ilike", line_name)], limit=1)
            if product_exist:
                product_exist = product_exist.product_tmpl_id
            else:
                product_exist = prod_obj.search([("description_purchase", "=ilike", line_name)], limit=1)
                if not product_exist:
                    product_exist = prod_obj.search([("name", "=ilike", line_name)], limit=1)
                    if not product_exist and product_create:
                        product_exist = prod_obj.create(
                            {
                                "name": line_name,
                                "description_purchase": line_name,
                                "list_price": line_price,
                                "type": "product",
                                "detailed_type": "product",
                                "uom_id": uom.id,
                                "uom_po_id": uom.id,
                                "l10n_mx_edi_code_sat_id": sat_uom_exist.id if sat_uom_exist else False,
                            }
                        )

            if import_type == "received" and not account_id and product_exist:
                account_id = (
                    product_exist.property_account_expense_id.id
                    or product_exist.categ_id.property_account_expense_categ_id.id
                )
                # _logger.info(account_id)
            elif import_type == "issued" and not account_id and product_exist:
                account_id = (
                    product_exist.property_account_income_id.id
                    or product_exist.categ_id.property_account_income_categ_id.id
                )
            if not account_id:
                account_id = journal.default_account_id.id
                # _logger.info(account_id)
            if not account_id:
                msg = _(
                    "Some products are not found in the database, and the account that "
                    "is used as default is not configured in the journal, please set "
                    "default account in the journal %s to create the move.",
                    journal.name,
                )
                raise ValidationError(msg)

            # analytic_distribution = self.env["account.analytic.distribution.model"]._get_distribution({
            #    "product_id": product_exist.id if product_exist else False,
            #    "product_categ_id": product_exist.categ_id.id if product_exist else False,
            #    "partner_id": partner.id,
            #    "partner_category_id": partner.category_id.ids,
            #    "account_prefix": account_id.code,
            #    "company_id": company.id,
            # })
            line_taxes = self.prepare_line_taxes(line)
            move_line_ids.append(
                (
                    0,
                    0,
                    {
                        "product_id": product_exist.id if product_exist else False,
                        "name": line_name,
                        "account_id": account_id,
                        # "analytic_distribution": analytic_distribution else False,
                        "quantity": line_quantity,
                        "product_uom_id": product_exist.uom_id.id if product_exist else uom.id,
                        "price_unit": line_price,
                        "discount": line_discount,
                        "tax_ids": self.search_taxes(line_taxes),
                    },
                )
            )

            # Case for fuel move line
            xml_sat_code_product = line.get("ClaveProdServ", False)
            if xml_sat_code_product in self.l10n_mx_edi_get_fuel_codes():
                tax = self.collect_taxes(line.Impuestos.Traslados.Traslado)
                fuel_line_price = tax[0].get("amount") / (tax[0].get("rate") / 100)
                move_line_ids.append(
                    (
                        0,
                        0,
                        {
                            "name": _("Fuel - IEPS"),
                            "account_id": account_id,
                            # "analytic_distribution": analytic_distribution else False,
                            "quantity": 1,
                            "price_unit": float(line.get("Importe")) - fuel_line_price,
                        },
                    )
                )

        local_taxes = self.get_et_local_taxes(cfdi_etree)
        if local_taxes:
            for _tax in local_taxes.get("taxes_ids"):
                if _tax["for_expenses"]:
                    move_line_ids.append(
                        (
                            0,
                            0,
                            {
                                "name": _tax["name"],
                                "account_id": account_id,
                                # "analytic_distribution": analytic_distribution or False,
                                "quantity": 1,
                                "price_unit": _tax["amount"],
                            },
                        )
                    )

        return move_line_ids

    def prepare_move(self, cfdi_etree):
        move_obj = self.env["account.move"]
        company = self.env.company
        import_type, move_type = self.get_et_import_type(cfdi_etree)
        journal_types = ["general"]
        if move_type in move_obj.get_sale_types():
            journal_types = ["sale"]
        elif move_type in move_obj.get_purchase_types():
            journal_types = ["purchase"]
        domain = [("company_id", "=", company.id), ("type", "in", journal_types)]
        journal = self.env["account.journal"].search(domain, limit=1, order="id asc")
        # _logger.info(journal)
        currency_exist = self.env["res.currency"].search([("name", "=", self.get_et_currency(cfdi_etree))], limit=1)
        payment_form = self.env["l10n_mx_edi.payment.method"].search(
            [("code", "=", cfdi_etree.get("FormaDePago", cfdi_etree.get("FormaPago")))], limit=1
        )
        payment_term = False
        if cfdi_etree.get("CondicionesDePago", False):
            payment_term = self.env["account.payment.term"].search(
                [("name", "=ilike", cfdi_etree.get("CondicionesDePago", False))], limit=1
            )
        l10n_mx_edi_origin = False
        related_uuids = self.get_related_uuids_dict(cfdi_etree)
        if cfdi_etree.get("TipoDeComprobante", False) == "E" and related_uuids:
            l10n_mx_edi_origin = move_obj._l10n_mx_edi_write_cfdi_origin(related_uuids["type"], related_uuids["uuids"])
            # related_moves = move_obj.search([
            #    ("commercial_partner_id", "=", partner.id), ("move_type", "=", "in_invoice")])
            # related_moves = related_moves.filtered(
            #    lambda inv: inv.l10n_mx_edi_cfdi_uuid in related_uuids["uuids"])
            # TODO update core fields: reversed_entry_id, reversal_move_id
            # related_moves.write({
            #    "refund_invoice_ids": [(4, invoice_id.id, 0)]
            # })
        partner = self.search_partner(cfdi_etree)
        move_line_ids = self.prepare_move_lines(cfdi_etree, import_type, journal)

        vals = {
            "move_type": move_type,
            "journal_id": journal.id,
            "currency_id": currency_exist.id,
            "invoice_date": self.get_et_datetime(cfdi_etree),
            "invoice_payment_term_id": payment_term.id if payment_term else 1,
            "partner_id": partner.id,
            "name": self.get_et_serie_folio(cfdi_etree) if import_type == "issued" else "/",
            "payment_reference": self.get_et_serie_folio(cfdi_etree)
            if import_type == "received" and self.get_et_serie_folio(cfdi_etree)
            else False,
            "posted_before": bool(import_type == "issued"),
            "l10n_mx_edi_payment_method_id": payment_form.id
            if payment_form
            else self.env.ref("l10n_mx_edi.payment_method_otros"),
            "l10n_mx_edi_payment_policy": cfdi_etree.get("MetodoPago"),
            "l10n_mx_edi_usage": cfdi_etree.Receptor.get("UsoCFDI", "S01"),
            "l10n_mx_edi_post_time": self.get_et_datetime(cfdi_etree),
            "l10n_mx_edi_cfdi_origin": l10n_mx_edi_origin,
            "invoice_line_ids": move_line_ids,
            "x_check_tax": float(cfdi_etree.Impuestos.get("TotalImpuestosTrasladados", "0.0"))
            if hasattr(cfdi_etree, "Impuestos")
            else 0.0,
            "x_check_total": float(cfdi_etree.get("Total", 0.0)),
        }
        return vals

    def prepare_cfdi_dupli_domain(self, cfdi_etree):
        import_type, move_type = self.get_et_import_type(cfdi_etree)
        domain = [
            ("invoice_date", "=", self.get_et_datetime(cfdi_etree)),
            # TODO l10n_mx_edi does wrong this part
            # ("l10n_mx_edi_post_time", "=", cfdi_dict["datetime"])
            ("move_type", "=", move_type),
        ]
        if import_type == "received":
            domain += [("payment_reference", "=", self.get_et_serie_folio(cfdi_etree))]
        elif import_type == "issued":
            domain += [("name", "=", self.get_et_serie_folio(cfdi_etree))]
        partner = self.search_partner(cfdi_etree)
        domain.append(("commercial_partner_id", "=", partner.id))
        domain.append(("l10n_mx_edi_cfdi_uuid", "=", self.get_et_complemento(cfdi_etree).get("UUID").upper()))
        return domain

    def check_cfdi_dupli(self, cfdi_etree):
        errors = []
        domain = self.prepare_cfdi_dupli_domain(cfdi_etree)
        fuzzy_domain = domain[:-1]
        fuzzy_move_exist = self.env["account.move"].search(fuzzy_domain)
        exact_move_exist = self.env["account.move"].search(domain)
        if not exact_move_exist and len(fuzzy_move_exist) == 1 and not fuzzy_move_exist.l10n_mx_edi_cfdi_uuid:
            exact_move_exist = fuzzy_move_exist
        elif not exact_move_exist and len(fuzzy_move_exist) > 1 or exact_move_exist:
            errors.append("Duplicated reference")
        return {"errors": errors, "move_exist": exact_move_exist}

    def xml2record(self, cfdi_etree):
        validation = self.check_cfdi_dupli(cfdi_etree)
        if validation["errors"]:
            raise ValidationError(_("Something went wrong: %s", validation["errors"]))
        if not validation["move_exist"]:
            vals = self.prepare_move(cfdi_etree)
            validation["move_exist"] = (
                self.env["account.move"].with_context(default_move_type=vals["move_type"]).create(vals)
            )
        return validation["move_exist"]

    def get_headers(self, soap_action, token=False, condition=True):
        headers = {
            "SOAPAction": soap_action,
            "Content-type": 'text/xml; charset="utf-8"',
            "Accept": "text/xml",
        }
        if condition:
            extend = {"Cache-Control": "no-cache", "Authorization": f'WRAP access_token="{token}"' if token else ""}
            headers.update(extend)
        return headers

    def check_comm(self, url, data, headers, result_xpath, external_nsmap):
        try:
            communication = requests.post(
                url,
                data,
                headers=headers,
                verify=True,
                timeout=20,
            )
            response = etree.fromstring(communication.text)
        except etree.XMLSyntaxError as e:
            _logger.error(str(e))
            raise ValidationError(str(e))
        except Exception as e:
            _logger.error(str(e))
            raise ValidationError(str(e))
        if communication.status_code != requests.codes.ok:
            error = response.find(".//faultstring").text
            raise ValidationError(error)
        return response.find(result_xpath, external_nsmap)

    def prepare_soap_data(
        self,
        certificate: crypto.X509,
        private_key: crypto.PKey,
        arguments: dict,
        envelop: str,
        xpath: str,
        token=False,
    ):
        internal_nsmap = {
            "": "http://www.w3.org/2000/09/xmldsig#",
            "s": "http://schemas.xmlsoap.org/soap/envelope/",
            "u": "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd",
            "o": "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd",
            "des": "http://DescargaMasivaTerceros.sat.gob.mx",
        }
        parser = etree.XMLParser(remove_blank_text=True)
        element_root = etree.fromstring(envelop, parser)
        element = element_root.find(xpath, internal_nsmap)
        signature = (
            '<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">'
            "<SignedInfo>"
            '<CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
            '<SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>'
            '<Reference URI="#_0">'
            "<Transforms>"
            '<Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
            "</Transforms>"
            '<DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>'
            "<DigestValue></DigestValue>"
            "</Reference>"
            "</SignedInfo>"
            "<SignatureValue></SignatureValue>"
            "</Signature>"
        )
        element_signature = etree.fromstring(signature, parser)

        element_to_digest = element_root.find(".//u:Timestamp", internal_nsmap)
        if not etree.iselement(element_to_digest):
            element_to_digest = element.getparent()
            for key in arguments:
                if key == "RfcReceptores":
                    for i, rfc_receptor in enumerate(arguments[key]):
                        if not i:
                            element_receptor = element_root.find(".//des:RfcReceptor", internal_nsmap)
                            element_receptor.text = rfc_receptor
                    continue
                if arguments[key] is not None:
                    element.set(key, arguments[key])

        digest_value = element_signature.find(".//DigestValue", internal_nsmap)
        digest_value.text = base64.b64encode(
            hashlib.sha1(etree.tostring(element_to_digest, method="c14n", exclusive=1)).digest()
        )
        element_to_sign = element_signature.find(".//SignedInfo", internal_nsmap)
        element_to_sign = etree.tostring(element_to_sign, method="c14n", exclusive=1)
        element_signed = element_signature.find(".//SignatureValue", internal_nsmap)
        element_signed.text = (
            base64.b64encode(crypto.sign(private_key, element_to_sign, "sha1")).decode("UTF-8").replace("\n", "")
        )

        if not token:
            key_info = (
                '<KeyInfo xmlns:o="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">'
                "<o:SecurityTokenReference>"
                '<o:Reference URI="#{uuid}" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>'  # noqa
                "</o:SecurityTokenReference>"
                "</KeyInfo>".format(**arguments)
            )
        else:
            key_info = (
                "<KeyInfo>"
                "<X509Data>"
                "<X509IssuerSerial>"
                "<X509IssuerName></X509IssuerName>"
                "<X509SerialNumber></X509SerialNumber>"
                "</X509IssuerSerial>"
                "<X509Certificate></X509Certificate>"
                "</X509Data>"
                "</KeyInfo>"
            )
        element_key_info = etree.fromstring(key_info, parser)
        if not token:
            element_certificate = element_root.find(".//o:BinarySecurityToken", internal_nsmap)
            element_certificate.text = base64.b64encode(crypto.dump_certificate(crypto.FILETYPE_ASN1, certificate))
        else:
            element_certificate = element_key_info.find(".//X509Certificate")
            element_certificate.text = base64.b64encode(crypto.dump_certificate(crypto.FILETYPE_ASN1, certificate))
            cer_issuer = certificate.get_issuer().get_components()
            cer_issuer = ",".join(
                ["{key}={value}".format(key=key.decode(), value=value.decode()) for key, value in cer_issuer]
            )
            element_issuer_name = element_key_info.find(".//X509IssuerName")
            element_issuer_name.text = cer_issuer
            element_serial_number = element_key_info.find(".//X509SerialNumber")
            element_serial_number.text = str(certificate.get_serial_number())

        element_signature.append(element_key_info)
        element.append(element_signature)

        return etree.tostring(element_root, method="c14n", exclusive=1)

    def l10n_mx_ws_get_cfdi_status(self, emmiter_vat, receiver_vat, total, uuid):
        expression = "?re=%s&amp;rr=%s&amp;tt=%s&amp;id=%s" % (
            tools.html_escape(emmiter_vat or ""),
            tools.html_escape(receiver_vat or ""),
            total or 0.0,
            uuid or "",
        )
        data = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<s:Envelope "
            'xmlns:ns0="http://tempuri.org/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
            "<s:Header/>"
            "<s:Body>"
            "<ns0:Consulta>"
            "<ns0:expresionImpresa>${expression}</ns0:expresionImpresa>"
            "</ns0:Consulta>"
            "</s:Body>"
            "</s:Envelope>".format(expression=expression)
        )
        url = "https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc?wsdl"
        soap_action = "http://tempuri.org/IConsultaCFDIService/Consulta"
        headers = self.get_headers(soap_action, condition=False)
        result_xpath = "s:Body/ConsultaResponse/ConsultaResult"
        external_nsmap = {
            "": "http://tempuri.org/",
            "a": "http://schemas.datacontract.org/2004/07/Sat.Cfdi.Negocio.ConsultaCfdi.Servicio",
            "i": "http://www.w3.org/2001/XMLSchema-instance",
            "s": "http://schemas.xmlsoap.org/soap/envelope/",
        }
        communication = self.check_comm(url, data, headers, result_xpath, external_nsmap)
        ret_dict = {
            "status": communication.find("a:Estado", external_nsmap).text,
            "is_cancellable": communication.find("a:EsCancelable", external_nsmap).text,
            "cancel_status": communication.find("a:EstatusCancelacion", external_nsmap).text,
            "efos_validation": communication.find("a:ValidacionEFOS", external_nsmap).text,
        }
        return ret_dict

    def l10n_mx_ws_generate_token(self, certificate, private_key, uuid):
        date_created = datetime.utcnow()
        date_expires = date_created + timedelta(seconds=300)
        date_created = date_created.isoformat()
        date_expires = date_expires.isoformat()
        duration = {
            "created": date_created,
            "expires": date_expires,
            "uuid": f"uuid-{uuid}-4",
        }
        envelop = (
            "<s:Envelope "
            'xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            'xmlns:u="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" '
            'xmlns:o="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">'
            "<s:Header>"
            '<o:Security s:mustUnderstand="1">'
            '<u:Timestamp u:Id="_0">'
            "<u:Created>{created}</u:Created>"
            "<u:Expires>{expires}</u:Expires>"
            "</u:Timestamp>"
            '<o:BinarySecurityToken u:Id="{uuid}" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary"></o:BinarySecurityToken>'  # noqa
            "</o:Security>"
            "</s:Header>"
            "<s:Body>"
            '<Autentica xmlns="http://DescargaMasivaTerceros.gob.mx"/>'
            "</s:Body>"
            "</s:Envelope>".format(**duration)
        )
        xpath = "s:Header/o:Security"
        data = self.prepare_soap_data(certificate, private_key, {"uuid": f"uuid-{uuid}-4"}, envelop, xpath, False)
        url = "https://cfdidescargamasivasolicitud.clouda.sat.gob.mx/Autenticacion/Autenticacion.svc"
        soap_action = "http://DescargaMasivaTerceros.gob.mx/IAutenticacion/Autentica"
        headers = self.get_headers(soap_action)
        result_xpath = "s:Body/AutenticaResponse/AutenticaResult"
        external_nsmap = {
            "": "http://DescargaMasivaTerceros.gob.mx",
            "s": "http://schemas.xmlsoap.org/soap/envelope/",
            "u": "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd",
            "o": "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd",
        }
        communication = self.check_comm(url, data, headers, result_xpath, external_nsmap)
        ret_dict = {
            "expires": date_expires,
            "token": communication.text,
        }
        return ret_dict

    def sanitize_args(self, args):
        args_allowed = (
            "uuid",
            "emitter_vat",
            "receiver_vats",
            "request_type",
            "date_from",
            "date_to",
            "cfdi_type",
            "cfdi_state",
            "thirthparty_vat",
            "complement",
        )
        sanitized_arg = {}
        for key, value in args.items():
            if key in args_allowed:
                sanitized_arg[key] = value
        return sanitized_arg

    def l10n_mx_ws_request_download(self, certificate, private_key, token, args):
        if not isinstance(args, dict):
            raise ValidationError(_("Validation error"))
        holder_vat = "".join(certificate.get_subject().x500UniqueIdentifier.split(" ")[0])
        sanitized = self.sanitize_args(args)
        arguments = {
            "UUID": sanitized["uuid"] if "uuid" in sanitized else None,
            "RfcSolicitante": holder_vat,
            "RfcEmisor": sanitized["emitter_vat"] if "emitter_vat" in sanitized and "uuid" not in sanitized else None,
            "RfcReceptores": sanitized["receiver_vats"]
            if "receiver_vats" in sanitized and "uuid" not in sanitized
            else [holder_vat],
            "FechaInicial": sanitized["date_from"].isoformat() if "date_from" in sanitized else None,
            "FechaFinal": sanitized["date_to"].isoformat() if "date_to" in sanitized else None,
            "TipoSolicitud": sanitized["request_type"] if "request_type" in sanitized else "CFDI",
            "TipoComprobante": sanitized["cfdi_type"]
            if "cfdi_type" in sanitized and "uuid" not in sanitized
            else None,
            "EstadoComprobante": sanitized["cfdi_state"]
            if "cfdi_state" in sanitized and "uuid" not in sanitized
            else None,
            "RfcACuentaTerceros": sanitized["thirthparty_vat"]
            if "thirthparty_vat" in sanitized and "uuid" not in sanitized
            else None,
            "Complemento": sanitized["complement"] if "complement" in sanitized and "uuid" not in sanitized else None,
        }
        envelop = (
            "<s:Envelope "
            'xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            'xmlns:des="http://DescargaMasivaTerceros.sat.gob.mx">'
            "<s:Header/>"
            "<s:Body>"
            "<des:SolicitaDescarga>"
            "<des:solicitud>"
            "<des:RfcReceptores>"
            "<des:RfcReceptor/>"
            "</des:RfcReceptores>"
            "</des:solicitud>"
            "</des:SolicitaDescarga>"
            "</s:Body>"
            "</s:Envelope>"
        )
        xpath = "s:Body/des:SolicitaDescarga/des:solicitud"
        data = self.prepare_soap_data(certificate, private_key, arguments, envelop, xpath, token)
        url = "https://cfdidescargamasivasolicitud.clouda.sat.gob.mx/SolicitaDescargaService.svc"
        soap_action = "http://DescargaMasivaTerceros.sat.gob.mx/ISolicitaDescargaService/SolicitaDescarga"
        headers = self.get_headers(soap_action, token)
        result_xpath = "s:Body/SolicitaDescargaResponse/SolicitaDescargaResult"
        external_nsmap = {
            "": "http://DescargaMasivaTerceros.sat.gob.mx",
            "s": "http://schemas.xmlsoap.org/soap/envelope/",
            "u": "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd",
            "o": "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd",
            "h": "http://DescargaMasivaTerceros.sat.gob.mx",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsd": "http://www.w3.org/2001/XMLSchema",
        }
        communication = self.check_comm(url, data, headers, result_xpath, external_nsmap)
        ret_dict = {
            "id_solicitud": communication.get("IdSolicitud"),
            "cod_estatus": communication.get("CodEstatus"),
            "mensaje": communication.get("Mensaje"),
        }
        return ret_dict

    def l10n_mx_ws_verify_package(self, certificate, private_key, token, id_solicitud):
        arguments = {
            "RfcSolicitante": certificate.get_subject().x500UniqueIdentifier.split(" ")[0],
            "IdSolicitud": id_solicitud,
        }
        envelop = (
            "<s:Envelope "
            'xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            'xmlns:des="http://DescargaMasivaTerceros.sat.gob.mx">'
            "<s:Header/>"
            "<s:Body>"
            "<des:VerificaSolicitudDescarga>"
            '<des:solicitud IdSolicitud="" RfcSolicitante=""/>'
            "</des:VerificaSolicitudDescarga>"
            "</s:Body>"
            "</s:Envelope>"
        )
        xpath = "s:Body/des:VerificaSolicitudDescarga/des:solicitud"
        data = self.prepare_soap_data(certificate, private_key, arguments, envelop, xpath, token)
        url = "https://cfdidescargamasivasolicitud.clouda.sat.gob.mx/VerificaSolicitudDescargaService.svc"
        soap_action = (
            "http://DescargaMasivaTerceros.sat.gob.mx/IVerificaSolicitudDescargaService/VerificaSolicitudDescarga"
        )
        headers = self.get_headers(soap_action, token)
        external_nsmap = {
            "": "http://DescargaMasivaTerceros.sat.gob.mx",
            "s": "http://schemas.xmlsoap.org/soap/envelope/",
            "u": "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd",
            "o": "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd",
            "h": "http://DescargaMasivaTerceros.sat.gob.mx",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsd": "http://www.w3.org/2001/XMLSchema",
        }
        result_xpath = "s:Body/VerificaSolicitudDescargaResponse/VerificaSolicitudDescargaResult"
        communication = self.check_comm(url, data, headers, result_xpath, external_nsmap)
        ret_dict = {
            "cod_estatus": communication.get("CodEstatus"),
            "estado_solicitud": communication.get("EstadoSolicitud"),
            "codigo_estado_solicitud": communication.get("CodigoEstadoSolicitud"),
            "numero_cfdis": communication.get("NumeroCFDIs"),
            "mensaje": communication.get("Mensaje"),
            "paquetes": [],
        }
        for id_paquete in communication.iter("{{{}}}IdsPaquetes".format(external_nsmap[""])):
            ret_dict["paquetes"].append(id_paquete.text)
        return ret_dict

    def l10n_mx_ws_download_package(self, certificate, private_key, token, id_paquete):
        arguments = {
            "RfcSolicitante": certificate.get_subject().x500UniqueIdentifier.split(" ")[0],
            "IdPaquete": id_paquete,
        }
        envelop = (
            "<s:Envelope "
            'xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            'xmlns:des="http://DescargaMasivaTerceros.sat.gob.mx">'
            "<s:Header/>"
            "<s:Body>"
            "<des:PeticionDescargaMasivaTercerosEntrada>"
            '<des:peticionDescarga IdPaquete="" RfcSolicitante=""/>'
            "</des:PeticionDescargaMasivaTercerosEntrada>"
            "</s:Body>"
            "</s:Envelope>"
        )
        xpath = "s:Body/des:PeticionDescargaMasivaTercerosEntrada/des:peticionDescarga"
        data = self.prepare_soap_data(certificate, private_key, arguments, envelop, xpath, token)
        url = "https://cfdidescargamasiva.clouda.sat.gob.mx/DescargaMasivaService.svc"
        soap_action = "http://DescargaMasivaTerceros.sat.gob.mx/IDescargaMasivaTercerosService/Descargar"
        headers = self.get_headers(soap_action, token)
        external_nsmap = {
            "": "http://DescargaMasivaTerceros.sat.gob.mx",
            "s": "http://schemas.xmlsoap.org/soap/envelope/",
            "u": "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd",
            "o": "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd",
            "h": "http://DescargaMasivaTerceros.sat.gob.mx",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsd": "http://www.w3.org/2001/XMLSchema",
        }
        result_xpath = "s:Body/RespuestaDescargaMasivaTercerosSalida/Paquete"
        communication = self.check_comm(url, data, headers, result_xpath, external_nsmap)
        respuesta = (
            communication.getparent().getparent().getparent().find("s:Header/h:respuesta", namespaces=external_nsmap)
        )
        ret_dict = {
            "cod_estatus": respuesta.get("CodEstatus"),
            "mensaje": respuesta.get("Mensaje"),
            "paquete_b64": communication.text,
        }
        return ret_dict
