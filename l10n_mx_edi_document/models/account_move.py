# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from lxml import etree

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round


class AccountInvoice(models.Model):
    _inherit = "account.move"

    def l10n_mx_edi_documents_search_invoice(self, document, invoice_data):
        cfdi = document.attachment_id.l10n_mx_edi_is_cfdi33()
        if cfdi is None:
            return False
        result = self._search_invoice(cfdi, invoice_data["move_type"], document.partner_id)
        if result:
            result._l10n_mx_edi_update_data(document.attachment_id)
            return result
        return False

    def xml2record(self, default_account=False, analytic_account=False):
        """Use the last attachment in the invoice (xml) and fill the invoice data"""
        result = super().xml2record()
        if self.country_code != "MX" or result._context.get("xml2record"):
            return result
        atts = self.env["ir.attachment"].search(
            [
                ("res_model", "=", self._name),
                ("res_id", "in", self.ids),
            ]
        )
        default_account = default_account or self.journal_id.default_account_id.id
        invoice = self
        for attachment in atts:
            cfdi = attachment.l10n_mx_edi_is_cfdi33()
            if cfdi is None:
                continue
            currency = self.env["res.currency"].search([("name", "=", cfdi.get("Moneda"))], limit=1)
            if not currency:
                raise UserError(
                    _(
                        "The currency %s is not available in the system, please ensure that it is active.",
                        cfdi.get("Moneda"),
                    )
                )
            if not self.partner_id:
                self.l10n_mx_edi_set_cfdi_partner(cfdi, currency)
            self._onchange_partner_id()
            cfdi_related = ""
            if hasattr(cfdi, "CfdiRelacionados"):
                cfdi_related = "%s|%s" % (
                    cfdi.CfdiRelacionados.get("TipoRelacion"),
                    ",".join([rel.get("UUID") for rel in cfdi.CfdiRelacionados.CfdiRelacionado]),
                )
            invoice_data = {
                "ref": "%s%s" % (cfdi.get("Serie", ""), cfdi.get("Folio", "")),
                "currency_id": currency.id,
                "l10n_mx_edi_post_time": cfdi.get("Fecha").replace("T", " "),
                "l10n_mx_edi_cfdi_origin": cfdi_related,
            }
            if not self.invoice_date:
                invoice_data["invoice_date"] = cfdi.get("Fecha").split("T")[0]
                invoice_data["date"] = cfdi.get("Fecha").split("T")[0]
            self.write(invoice_data)

            # If fiscal_position is set in the partner, map the default account to the lines
            default_account = (
                self.fiscal_position_id.map_account(self.env["account.account"].browse(default_account)).id
                if self.fiscal_position_id
                else default_account
            )

            self._l10n_mx_edi_create_lines(cfdi, default_account)

            for tax in self._get_local_taxes(cfdi):
                self.write(
                    {
                        "invoice_line_ids": [
                            (
                                0,
                                0,
                                {
                                    "account_id": default_account,
                                    "name": tax[-1]["name"],
                                    "quantity": 1,
                                    "price_unit": tax[-1]["amount"],
                                    "tax_ids": False,
                                },
                            )
                        ]
                    }
                )

            self._l10n_mx_edi_update_data(attachment)
            if self.state == "posted" and cfdi_related.split("|")[0] in ("01", "03"):
                move = self.line_ids.filtered(
                    lambda line: line.account_id.account_type in ("liability_payable", "asset_receivable")
                )
                for uuid in self.l10n_mx_edi_cfdi_origin.split("|")[1].split(","):
                    inv = self.search([("l10n_mx_edi_cfdi_uuid", "=", uuid.upper().strip())])
                    if not inv:
                        continue
                    inv.js_assign_outstanding_line(move.ids)
        return invoice

    def _l10n_mx_edi_create_lines(self, cfdi, default_account):
        if self._l10n_mx_edi_create_lines_ecc12(cfdi, default_account):
            return True

        fiscal_position = self.fiscal_position_id
        prod_supplier = self.env["product.supplierinfo"]
        prod = self.env["product.product"]
        for rec in cfdi.Conceptos.Concepto:
            name = rec.get("Descripcion", "")
            no_id = rec.get("NoIdentificacion", name)
            uom = rec.get("Unidad", "")
            uom_code = rec.get("ClaveUnidad", "")
            qty = rec.get("Cantidad", "")
            price = rec.get("ValorUnitario", "")
            amount = float(rec.get("Importe", "0.0"))
            supplierinfo = prod_supplier.search(
                [
                    ("partner_id", "=", self.partner_id.id),
                    "|",
                    ("product_name", "=ilike", name),
                    ("product_code", "=ilike", no_id),
                ],
                limit=1,
            )
            product = supplierinfo.product_tmpl_id.product_variant_id
            product = product or prod.search(
                ["|", ("default_code", "=ilike", no_id), ("name", "=ilike", name)], limit=1
            )
            product_uom_id = product.uom_id if self.is_sale_document(include_receipts=True) else product.uom_po_id
            uom_id = self._l10n_mx_edi_get_uom(uom, uom_code) or product_uom_id

            # If product UoM != CFDI UoM, avoid set the product found to avoid an error.
            if uom_id and product_uom_id.category_id != uom_id.category_id:
                product = prod

            accounts = product.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
            account_id = (
                accounts["income"].id if self.is_sale_document(include_receipts=True) else accounts["expense"].id
            ) or default_account

            discount = 0.0
            if rec.get("Descuento") and amount:
                discount = (float(rec.get("Descuento", "0.0")) / amount) * 100

            if rec.get("ClaveProdServ", "") in self._get_fuel_codes():
                taxes = (
                    self.collect_taxes(rec.Impuestos.Traslados.Traslado) if hasattr(rec.Impuestos, "Traslados") else []
                )
                tax = taxes[0] if taxes else {}
                qty = 1.0
                price = tax.get("amount") / (tax.get("rate") / 100)
                self.write(
                    {
                        "invoice_line_ids": [
                            (
                                0,
                                0,
                                {
                                    "account_id": account_id,
                                    "name": _("FUEL - IEPS"),
                                    "quantity": qty,
                                    "product_uom_id": uom_id.id,
                                    "price_unit": float(rec.get("Importe", 0)) - price,
                                    "tax_ids": False,
                                    # "analytic_account_id": analytic_account,
                                },
                            )
                        ]
                    }
                )
            self.write(
                {
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": product.id,
                                "account_id": account_id,
                                "name": name,
                                "quantity": float(qty),
                                # "analytic_account_id": analytic_account,
                                "product_uom_id": uom_id.id,
                                "tax_ids": self.get_line_taxes(rec),
                                "price_unit": float(price),
                                "discount": discount,
                            },
                        )
                    ]
                }
            )
        return True

    def _l10n_mx_edi_create_lines_ecc12(self, cfdi, account):
        ecc12 = self._get_fuel_complement(cfdi)
        if ecc12 is None:
            return False
        product = self.env["ir.config_parameter"].sudo().get_param("l10n_mx_product_ecc12", "")
        try:
            product = self.env["product.product"].browse(int(product))
            account = (product.property_account_expense_id or product.categ_id.property_account_expense_categ_id).id
        except Exception:
            product = self.env["product.product"]
        values_list = []
        for rec in ecc12.Conceptos.ConceptoEstadoDeCuentaCombustible:
            values_list += self._l10n_mx_edi_get_line_ecc12_values(rec, product, account)
        self.write({"invoice_line_ids": values_list})
        return True

    def _l10n_mx_edi_get_line_ecc12_values(self, rec, product, account):
        """Method for obtaining the values for the creation of invoice lines of fuel concepts"""
        taxes = self.collect_taxes(rec.Traslados.Traslado) if hasattr(rec, "Traslados") else []
        # Split IEPS if is assigned in the XML
        ieps = [tax for tax in taxes if tax.get("tax") == "IEPS"]
        taxes = [tax for tax in taxes if tax.get("tax") != "IEPS"]
        tax = taxes[0] if taxes else {}
        price = round(tax.get("amount") / (tax.get("rate") / 100), 2)
        taxes = self._l10n_mx_edi_get_taxes(taxes)
        partner = self._l10n_mx_edi_partner_ecc12(rec)
        return [
            Command.create(
                {
                    "account_id": account,
                    "name": _("FUEL - IEPS"),
                    "quantity": 1.0,
                    "product_uom_id": product.uom_id.id,
                    "price_unit": (float(rec.get("Importe", 0)) - price)
                    + float(ieps[0].get("amount", 0) if ieps else 0),
                    "tax_ids": False,
                    "l10n_mx_edi_is_ecc": True,
                    "partner_id": partner.id,
                },
            ),
            Command.create(
                {
                    "product_id": product.id,
                    "account_id": account,
                    "name": _("Station: %s - Operation: %s", rec.get("ClaveEstacion"), rec.get("FolioOperacion")),
                    "quantity": 1.0,
                    "product_uom_id": product.uom_id.id,
                    "tax_ids": taxes,
                    "price_unit": float(price),
                    "l10n_mx_edi_is_ecc": True,
                    "partner_id": partner.id,
                },
            ),
        ]

    def _l10n_mx_edi_partner_ecc12(self, data):
        partner = self.env["res.partner"]
        domain = [("vat", "=", data.get("Rfc"))]
        domain.append(("is_company", "=", True))
        cfdi_partner = partner.search(domain, limit=1)
        if not cfdi_partner:
            domain.pop()
            cfdi_partner = partner.search(domain, limit=1)
        if not cfdi_partner:
            cfdi_partner = partner.create(
                {
                    "name": data.get("ClaveEstacion"),
                    "vat": data.get("Rfc"),
                    "country_id": self.env.ref("base.mx").id,
                }
            )
            cfdi_partner.message_post(body=_("This record was generated from DMS"))
        return cfdi_partner

    def _l10n_mx_edi_get_uom(self, uom, uom_code):
        domain_uom = [("name", "=ilike", uom)]
        code_sat = self.env["product.unspsc.code"].search([("code", "=", uom_code)], limit=1)
        domain_uom = [("unspsc_code_id", "=", code_sat.id)]
        return self.env["uom.uom"].with_context(lang="es_MX").search(domain_uom, limit=1)

    def _l10n_mx_edi_update_data(self, attachment):
        if self.l10n_mx_edi_cfdi_state == "sent":
            return
        self._l10n_prepare_edi_document(attachment)
        sat_param = self.env["ir.config_parameter"].sudo().get_param("l10n_mx_edi_document.omit_sat_validation", False)
        if not sat_param:
            self.l10n_mx_edi_cfdi_try_sat()
        if not sat_param and self.l10n_mx_edi_cfdi_sat_state == "cancelled":
            try:
                self.button_cancel()
            except (UserError, ValidationError) as exe:
                self.message_post(body=_("Error on invoice cancellation: %s", str(exe)))
            self.l10n_mx_edi_cfdi_state = "cancel"
            self.l10n_mx_edi_document_ids.state = "invoice_cancel"
            return
        if self.move_type in ("in_refund", "in_invoice"):
            return
        # The invoice will be removed, then avoid validate it.
        if (
            not sat_param
            and not self.company_id.l10n_mx_edi_pac_test_env
            and self.l10n_mx_edi_cfdi_sat_state != "valid"
        ):
            return
        try:
            self.action_post()
        except (UserError, ValidationError) as exe:
            self.message_post(body=_("Error on invoice validation: %s", str(exe)))
        return

    def _l10n_prepare_edi_document(self, attachment):
        if self.country_code != "MX":
            return super()._l10n_prepare_edi_document(attachment)
        # TODO: Review Odoo's new l10n_mx_edi.document model since account.edi.document is no longer used.
        if self.l10n_mx_edi_document_ids:
            return self.env["l10n_mx_edi.document"]
        return self.env["l10n_mx_edi.document"].create(
            {
                "move_id": self.id,
                "invoice_ids": [Command.set(self.ids)],
                "state": "invoice_sent" if self.is_sale_document() else "invoice_received",
                "sat_state": "not_defined",
                "attachment_id": attachment.id,
                "datetime": fields.Datetime.now(),
            }
        )

    def l10n_mx_edi_get_partner(self, cfdi, move_type, currency=False):
        partner = self.env["res.partner"]
        partner_cfdi = {}
        if move_type in ("out_invoice", "out_refund"):
            partner_cfdi = cfdi.Receptor
        elif move_type in ("in_invoice", "in_refund"):
            partner_cfdi = cfdi.Emisor
        # Make domain and search the partner
        name = partner_cfdi.get("Nombre")
        vat = partner_cfdi.get("Rfc")
        domain = [
            ("name", "ilike", name) if vat in ("XEXX010101000", "XAXX010101000") else ("vat", "=", vat),
            ("is_company", "=", True),
        ]
        currency_field = currency and ("property_purchase_currency_id" in partner._fields)
        if currency_field:
            domain.append(("property_purchase_currency_id", "=", currency.id))
        cfdi_partner = partner.search(domain, limit=1)
        if cfdi_partner:
            return cfdi_partner
        # No partner found, expand search
        if currency_field:
            domain.pop()
            cfdi_partner = partner.search(domain, limit=1)
            if cfdi_partner:
                return cfdi_partner
        domain.pop()
        cfdi_partner = partner.search(domain, limit=1)
        if cfdi_partner:
            return cfdi_partner
        # No partner found, create new one
        if not self.env["ir.config_parameter"].sudo().get_param("mx_documents_omit_partner_generation", ""):
            cfdi_partner = partner.create(
                {
                    "name": name,
                    "vat": vat,
                    "country_id": self.env.ref("base.mx").id,
                }
            )
            cfdi_partner.message_post(body=_("This record was generated from DMS"))
        return cfdi_partner

    def l10n_mx_edi_set_cfdi_partner(self, cfdi, currency):
        self.ensure_one()
        cfdi_partner = self.l10n_mx_edi_get_partner(cfdi, self.move_type, currency)
        if cfdi_partner:
            self.partner_id = cfdi_partner

    def get_line_taxes(self, line):
        if not hasattr(line, "Impuestos"):
            return []
        taxes = []
        taxes_xml = line.Impuestos
        if hasattr(taxes_xml, "Traslados"):
            taxes = self.collect_taxes(taxes_xml.Traslados.Traslado)
        if hasattr(taxes_xml, "Retenciones"):
            taxes += self.collect_taxes(taxes_xml.Retenciones.Retencion)
        return self._l10n_mx_edi_get_taxes(taxes)

    def _l10n_mx_edi_get_taxes(self, taxes):
        """Return the Odoo taxes based on the dict with taxes data"""
        taxes_list = []
        for tax in taxes:
            tax_group_id = (
                self.env["account.tax.group"].with_context(lang="es_MX").search([("name", "ilike", tax["tax"])])
            )
            domain = [
                # TODO: Investigate why this domain condition results in no tax being found.
                ("tax_group_id", "in", tax_group_id.ids),
                ("type_tax_use", "=", "purchase" if "in_" in self.move_type else "sale"),
                ("company_id", "=", self.company_id.id),
            ]
            if -10.67 <= tax["rate"] <= -10.66:
                domain.append(("amount", "<=", -10.66))
                domain.append(("amount", ">=", -10.67))
            else:
                domain.append(("amount", "=", tax["rate"]))
            name = "%s(%s%%)" % (tax["tax"], tax["rate"])

            tax_get = self.env["account.tax"].search(domain, limit=1)
            if not tax_get:
                self.message_post(body=_("The tax %s cannot be found", name))
                continue
            tax_account = tax_get.invoice_repartition_line_ids.filtered(lambda rec: rec.repartition_type == "tax")
            if not tax_account:
                self.message_post(body=_("Please configure the tax account in the tax %s", name))
                continue
            taxes_list.append((4, tax_get.id))
        return taxes_list

    def _get_local_taxes(self, xml):
        if not hasattr(xml, "Complemento"):
            return {}
        local_taxes = xml.Complemento.xpath(
            "implocal:ImpuestosLocales", namespaces={"implocal": "http://www.sat.gob.mx/implocal"}
        )
        taxes = []
        if not local_taxes:
            return taxes
        local_taxes = local_taxes[0]
        if hasattr(local_taxes, "RetencionesLocales"):
            for local_ret in local_taxes.RetencionesLocales:
                taxes.append(
                    (
                        0,
                        0,
                        {
                            "name": local_ret.get("ImpLocRetenido"),
                            "amount": float(local_ret.get("Importe")) * -1,
                        },
                    )
                )
        if hasattr(local_taxes, "TrasladosLocales"):
            for local_tras in local_taxes.TrasladosLocales:
                taxes.append(
                    (
                        0,
                        0,
                        {
                            "name": local_tras.get("ImpLocTrasladado"),
                            "amount": float(local_tras.get("Importe")),
                        },
                    )
                )

        return taxes

    def collect_taxes(self, taxes_xml):
        """Get tax data of the Impuesto node of the xml and return
        dictionary with taxes datas
        :param taxes_xml: Impuesto node of xml
        :type taxes_xml: etree
        :return: A list with the taxes data
        :rtype: list
        """
        result = super().collect_taxes(taxes_xml)
        if self.country_code != "MX":
            return result
        taxes = []
        tax_codes = {"001": "ISR", "002": "IVA", "003": "IEPS"}
        for rec in taxes_xml:
            tax_xml = rec.get("Impuesto", "")
            tax_xml = tax_codes.get(tax_xml, tax_xml)
            amount_xml = float(rec.get("Importe", "0.0"))
            rate_xml = float_round(float(rec.get("TasaOCuota", "0.0")) * 100, 4)
            if "Retenciones" in rec.getparent().tag:
                amount_xml = amount_xml * -1
                rate_xml = rate_xml * -1

            taxes.append({"rate": rate_xml, "tax": tax_xml, "amount": amount_xml})
        return taxes

    def _search_invoice(self, cfdi, move_type, partner_id=False):
        uuid = self.env["l10n_mx_edi.document"]._decode_cfdi_attachment(etree.tostring(cfdi)).get("uuid")
        # The first search is for UUID
        invoice = self.search(
            [
                ("l10n_mx_edi_cfdi_uuid", "=", uuid),
                ("move_type", "=", move_type),
            ],
            limit=1,
        )
        if uuid and invoice:
            return invoice

        folio = cfdi.get("Folio", "")
        serie = cfdi.get("Serie", "")
        serie_folio = "%s%%%s" % (serie, folio) if serie or folio else ""
        domain = [("move_type", "=", move_type)]

        amount = float(cfdi.get("Total", 0.0))
        domain.append(("amount_total", ">=", amount - 1))
        domain.append(("amount_total", "<=", amount + 1))

        if partner_id:
            domain.extend(["|", ("partner_id", "child_of", partner_id.id), ("partner_id", "=", partner_id.id)])

        ir_params = self.env["ir.config_parameter"].sudo()
        # The parameter l10n_mx_force_only_folio is used when the user create the invoices from a PO and only set
        # the folio in the reference.
        force_folio = ir_params.get_param("l10n_mx_force_only_folio", "")
        if serie_folio and force_folio:
            domain.append("|")
            domain.append(("ref", "=ilike", folio))

        # The parameter documents_force_use_date force search only invoice in the same period that the XML
        # (day or month)
        date_type = ir_params.get_param("documents_force_use_date", "") or ir_params.get_param(
            "l10n_mx_edi_vendor_bills_force_use_date", ""
        )
        if date_type == "day":
            domain.append(
                ("invoice_date", "=", fields.datetime.strptime(cfdi.get("Fecha"), "%Y-%m-%dT%H:%M:%S").date())
            )
        elif date_type == "month":
            xml_date = fields.datetime.strptime(cfdi.get("Fecha"), "%Y-%m-%dT%H:%M:%S").date()
            domain.append(("invoice_date", ">=", xml_date.replace(day=1)))
            # Use day 28, when I sum 4 days I get the next month, so, replace the day for the first day and rest 1
            # to get the last month day
            last_day = (xml_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            domain.append(("invoice_date", "<=", last_day))

        if serie_folio:
            domain.append("|")
            domain.append(("name", "=ilike", serie_folio))
            domain.append(("ref", "=ilike", serie_folio))
            invoice = self.search(domain, limit=1)
            return invoice if not invoice.l10n_mx_edi_cfdi_uuid or invoice.l10n_mx_edi_cfdi_uuid == uuid else False

        domain.append(("state", "!=", "cancel"))

        domain.append(("l10n_mx_edi_cfdi_uuid", "in", (False, uuid)))
        return self.search(domain, limit=1)

    @api.model
    def _get_fuel_codes(self):
        """Return the codes that could be used in FUEL"""
        fuel_codes = [str(r) for r in range(15101500, 15101516)]
        fuel_codes.extend(self.env.user.company_id.l10n_mx_edi_fuel_code_sat_ids.mapped("code"))
        return fuel_codes

    def _get_edi_document_errors(self):
        if self.country_code != "MX":
            return super()._get_edi_document_errors()
        errors = []
        partner_param = self.env["ir.config_parameter"].sudo().get_param("mx_documents_omit_partner_generation", "")
        if not self.partner_id and partner_param:
            errors.append(
                _("The partner does not exist, please create it manually and try to generate the document again.")
            )
        sat_param = self.env["ir.config_parameter"].sudo().get_param("l10n_mx_edi_document.omit_sat_validation", False)
        if (
            not sat_param
            and self.l10n_mx_edi_cfdi_state == "sent"
            and not self.company_id.l10n_mx_edi_pac_test_env
            and self.l10n_mx_edi_cfdi_sat_state != "valid"
            and not self.company_id.l10n_edi_import_canceled_documents
        ):
            errors.append(
                _("The SAT status of this document is not valid in the SAT. (Is %s)", self.l10n_mx_edi_cfdi_sat_state)
            )
        return errors

    def _get_fuel_complement(self, cfdi):
        if not hasattr(cfdi, "Complemento"):
            return None
        attribute = "//ecc12:EstadoDeCuentaCombustible"
        namespace = {"ecc12": "http://www.sat.gob.mx/EstadoDeCuentaCombustible12"}
        node = cfdi.Complemento.xpath(attribute, namespaces=namespace)
        return node[0] if node else None

    def _get_wrong_lines(self):
        """Inherit to change the filtered logic and ignore the ECC lines"""
        result = super()._get_wrong_lines()
        if not result:
            return result
        return result.filtered(lambda line: not line.l10n_mx_edi_is_ecc)

    # Inherit to Odoo methods

    @api.depends("edi_document_ids.state")
    def _compute_show_reset_to_draft_button(self):
        """Inherit to allow reset 2 draft any vendor bill"""
        # OVERRIDE
        result = super()._compute_show_reset_to_draft_button()

        for move in self.filtered(lambda inv: inv.country_code == "MX" and inv.l10n_mx_edi_document_ids):
            move.show_reset_to_draft_button = (
                not move.restrict_mode_hash_table
                and (move.state == "cancel" or (move.state == "posted" and not move.need_cancel_request))
                and (move.is_purchase_document(include_receipts=True) or move.move_type == "entry")
            )

        return result

    def button_cancel(self):
        """Avoid set EDI state to cancel on vendor documents for MX"""
        res = super().button_cancel()
        # TODO: Review Odoo's new l10n_mx_edi.document model and update code to cancel CFDI documents.
        self.filtered(lambda i: i.move_type in ("in_invoice", "in_refund")).l10n_mx_edi_cfdi_state = "cancel"
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_mx_edi_is_ecc = fields.Boolean(help="Indicates that comes from a Fuel Account Statement complement")
