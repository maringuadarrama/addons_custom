from lxml import etree

from odoo import Command, api, fields, models


class DocumentsDocument(models.Model):
    _inherit = "documents.document"

    just_downloaded = fields.Boolean(
        compute="_compute_just_downloaded",
        search="_search_just_downloaded",
        store=False,
        help="""Used to identify the just donwloaded attachments.
            To evaluate if an attachment was just downloaded, we need to
            check the current context.""",
    )

    def _compute_just_downloaded(self):
        downloaded_ids = self._context.get("downloaded_invoice", [])
        for rec in self:
            rec.just_downloaded = rec.id in downloaded_ids

    def _search_just_downloaded(self, operator, value):
        operator = "in" if value else "not int"
        return [("id", operator, self._context.get("downloaded_invoice", []))]

    def _l10n_edi_get_invoice_date(self):
        cfdi = self._l10n_mx_edi_get_cfdi_data()
        if cfdi is False:
            return False
        return cfdi.get("Fecha").split("T")[0]

    def get_tag_map(self, key):
        default = self.env["documents.tag"]
        values = {
            "I": self.env.ref("l10n_mx_edi_document.ingreso_tag"),
            "E": self.env.ref("l10n_mx_edi_document.egreso_tag"),
            "T": self.env.ref("l10n_mx_edi_document.translado_tag"),
            "P": self.env.ref("l10n_mx_edi_document.reception_tag"),
            "N": self.env.ref("l10n_mx_edi_document.nomina_tag"),
            "R": self.env.ref("l10n_mx_edi_document.retencion_tag"),
        }
        return values.get(key, default)

    @api.model_create_multi
    def create(self, vals_list):
        xml_obj = self.env.context.get("xml_obj", False)

        if not xml_obj:
            return super().create(vals_list)

        xml_type = xml_obj.get("TipoDeComprobante", False)
        tags_type = self.get_tag_map(xml_type)
        for vals in vals_list:
            vals["tag_ids"] = [Command.set(tags_type.ids)]

        return super().create(vals_list)

    def _l10n_mx_edi_get_cfdi_data(self):
        self.ensure_one()
        company = self.attachment_id.company_id
        if company.country_code != "MX":
            return False
        cfdi = self.attachment_id.l10n_mx_edi_is_cfdi33()
        return cfdi if (cfdi is not None) else False

    def _get_document_edi_partner(self):
        """Get the partner from the EDI document."""
        self.ensure_one()
        cfdi = self._l10n_mx_edi_get_cfdi_data()
        if cfdi is False:
            return self.env["res.partner"]
        move_type = "out_invoice" if (self.attachment_id.company_id.vat == cfdi.Emisor.get("Rfc")) else "in_invoice"
        return self.env["account.move"].l10n_mx_edi_get_partner(cfdi, move_type)

    def _get_document_edi_reference(self):
        """Get the reference from the EDI document."""
        self.ensure_one()
        cfdi = self._l10n_mx_edi_get_cfdi_data()
        if cfdi is False:
            return False
        return "%s%s" % (cfdi.get("Serie", ""), cfdi.get("Folio", ""))

    def get_xml_data(self):
        """Get significant data from a CFDI XML to show it on the Documents visualization.

        params:
            self: documents.document objetc

        return:
            dic: contains data from the CFDI related to the self document"""
        mimetype = self.attachment_id.mimetype
        cfdi = self.attachment_id.l10n_mx_edi_is_cfdi33()
        if not cfdi:
            return False
        cfdi_data = self.env["l10n_mx_edi.document"]._decode_cfdi_attachment(etree.tostring(cfdi))
        conceptos = []
        self.attachment_id.mimetype = mimetype
        for concepto in cfdi.Conceptos.Concepto:
            concepto_data = {
                "quantity": concepto.get("Cantidad"),
                "product_service_key": concepto.get("ClaveProdServ"),
                "unity_key": concepto.get("ClaveUnidad"),
                "description": concepto.get("Descripcion"),
                "import": concepto.get("Importe"),
                "identification_number": concepto.get("NoIdentificacion"),
                "imp_object": concepto.get("ObjetoImp"),
                "unity": concepto.get("Unidad"),
                "unit_price": concepto.get("ValorUnitario"),
            }
            conceptos.append(concepto_data)

        pdf_content = {
            "currency": cfdi.get("Moneda"),
            "cetificate": cfdi.get("Certificado"),
            "export": cfdi.get("Exportacion"),
            "date": cfdi.get("Fecha"),
            "folio": cfdi.get("Folio"),
            "payment_form": cfdi.get("FormaPago"),
            "payment_method": cfdi.get("MetodoPago"),
            "seal": cfdi.get("Sello"),
            "serie": cfdi.get("Serie"),
            "subtotal": cfdi.get("SubTotal"),
            "total": cfdi.get("Total"),
            "expedition_place": cfdi.get("LugarExpedicion"),
            "seal_number": cfdi.get("NoCertificado"),
            "voucher_type": cfdi.get("TipoDeComprobante"),
            "concepts": conceptos,
            "emitter_vat": cfdi_data.get("supplier_rfc"),
            "emitter_name": cfdi.Emisor.get("Nombre"),
            "emitter_fiscal_regime": cfdi.Emisor.get("RegimenFiscal"),
            "receptor_vat": cfdi_data.get("customer_rfc"),
            "receptor_name": cfdi.Receptor.get("Nombre"),
            "receptor_fiscal_regime": cfdi.Receptor.get("RegimenFiscalReceptor"),
            "receptor_fiscal_address": cfdi.Receptor.get("DomicilioFiscalReceptor"),
            "cfdi_usage": cfdi_data.get("usage"),
            "fiscal_regime": cfdi_data.get("fiscal_regime"),
            "certificate_sat_number": cfdi_data.get("certificate_sat_number"),
            "expedition": cfdi_data.get("expedition"),
            "sello_sat": cfdi_data.get("sello_sat"),
            "cadena": cfdi_data.get("cadena"),
            "total_transferred_taxes": cfdi.Impuestos.get("TotalImpuestosTrasladados")
            if hasattr(cfdi, "Impuestos")
            else None,
            "total_witheld_taxes": cfdi.Impuestos.get("TotalImpuestosRetenidos")
            if hasattr(cfdi, "Impuestos")
            else None,
            "emission_date_str": cfdi_data.get("emission_date_str"),
            "certificate_provider_rfc": cfdi_data.get("certificate_provider_rfc"),
        }
        return pdf_content

    def _l10n_edi_document_assign_tags_and_folder(self):
        if (self.attachment_id.company_id or self.env.company).country_code != "MX":
            return super()._l10n_edi_document_assign_tags_and_folder()
        cfdi = self._l10n_mx_edi_get_cfdi_data()
        if cfdi is False:
            return
        self._l10n_mx_edi_document_set_tags(cfdi)
        self._l10n_mx_edi_document_set_folder(cfdi)

    def _l10n_mx_edi_document_set_tags(self, cfdi):
        # Assign month and year tags
        date = fields.datetime.strptime(cfdi.get("Fecha"), "%Y-%m-%dT%H:%M:%S")
        if date:
            domain = [
                ("facet_id", "=", self.env.ref("l10n_edi_document.l10n_edi_document_facet_fiscal_month").id),
                ("sequence", "=", date.month),
            ]
            self.tag_ids |= self.env["documents.tag"].search(domain)
            domain = [
                ("facet_id", "=", self.env.ref("documents.documents_finance_fiscal_year").id),
                ("name", "=", str(date.year)),
            ]
            year_tag = self.env["documents.tag"].search(domain)
            # Create year tag and its external id if none found
            if not year_tag:
                tag_name = str(date.year)
                values = {
                    "name": tag_name,
                    "facet_id": self.env.ref("documents.documents_finance_fiscal_year").id,
                    "sequence": date.year,
                }
                year_tag = self.env["documents.tag"].sudo().create(values)
            self.tag_ids |= year_tag
        # Get tag for TipoDeComprobante
        self.tag_ids |= self.get_tag_map(cfdi.get("TipoDeComprobante", False))

    def _l10n_mx_edi_document_set_folder(self, cfdi):
        vat = self.attachment_id.company_id.vat
        if not (vat == cfdi.Emisor.get("Rfc", "") or vat == cfdi.Receptor.get("Rfc", "")):
            # Keep in the same folder if company is neither issuer nor receiver
            return
        import_type = "issued" if vat == cfdi.Emisor.get("Rfc", "") else "received"
        folder = (
            self.env.ref("l10n_edi_document.l10n_edi_document_folder_edi_issued")
            if import_type == "issued"
            else self.env.ref("l10n_edi_document.l10n_edi_document_folder_edi_received")
        )
        child_folders = self._get_children_folder_ids(folder)
        self.folder_id = folder if folder and self.folder_id not in child_folders else self.folder_id
