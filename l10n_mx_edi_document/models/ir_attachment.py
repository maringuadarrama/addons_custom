# Copyright 2020, Vauxoo, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import logging
from io import BytesIO

from lxml import etree, objectify

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.xml_utils import _check_with_xsd

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model
    def l10n_mx_edi_is_cfdi33(self):
        """Return the UUID of the CFDI if it exists.

        When assigning the mimetype of the XML, the OdooBot user (user_root) must be used,
        this is necessary because when creating or updating the ir.attachment it is verified in the
        check_contents(https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/models/ir_attachment.py#L364)
        method, if the user has not write permissions in the ir.ui.view model, the mimetype is changed
        to text/plain, which causes the preview in the Documents app to be incorrect.
        To prevent this, the user must belong to the Administration/Settings group, but it is not
        recommended  since it is a technical group. So it is better to use the user_root to prevent
        the mimetype from being changed to text/plain in the check_contents method.
        """
        self.ensure_one()
        if not self.datas:
            return None
        try:
            datas = (
                base64.b64decode(self.datas)
                .replace(b"xmlns:schemaLocation", b"xsi:schemaLocation")
                .replace(b"data:text/xml;base64,", b"")
                .replace(b"o;?", b"")
                .replace(b"\xef\xbf\xbd", b"")
            )
            self.sudo().datas = base64.b64encode(datas)
            cfdi = objectify.fromstring(datas)
        except (SyntaxError, ValueError):
            return None
        version = cfdi.get("Version")
        if version not in ["3.3", "4.0"]:
            return None

        self.with_user(self.env.ref("base.user_root").id).mimetype = "application/xml"
        attachment = self.sudo().env.ref("l10n_mx_edi.xsd_cached_cfdv33_xsd", False) if version == "3.3" else False
        try:
            schema = base64.b64decode(attachment.datas) if attachment else b""
            if not hasattr(cfdi, "Complemento"):
                return None
            if hasattr(cfdi, "Addenda"):
                cfdi.remove(cfdi.Addenda)
            if attachment:
                attribute = "registrofiscal:CFDIRegistroFiscal"
                namespace = {"registrofiscal": "http://www.sat.gob.mx/registrofiscal"}
                node = cfdi.Complemento.xpath(attribute, namespaces=namespace)
                if node:
                    cfdi.Complemento.remove(node[0])
                with BytesIO(schema) as xsd:
                    _check_with_xsd(cfdi, xsd)
            return cfdi
        except (ValueError, OSError, UserError, etree.XMLSyntaxError):
            return None

    def l10n_edi_document_type(self, document=False):
        self.ensure_one()
        company = document.company_id or self.company_id if document else self.company_id
        if company.country_code != "MX":
            return super().l10n_edi_document_type(document=document)
        cfdi = self.l10n_mx_edi_is_cfdi33()
        if cfdi is None:
            return False, {"error": "This Document is not a CFDI valid."}
        res_model = {
            "P": "account.payment",
            "I": "account.move",
            "E": "account.move",
        }.get(cfdi.get("TipoDeComprobante"))
        document_type = self._l10n_mx_edi_get_document_type(cfdi, company.vat)
        if not document_type:
            return False, {
                "error": _(
                    "Neither the emitter nor the receiver of this CFDI is this company, please review this document."
                )
            }
        return [("%s%s" % (document_type, cfdi.get("TipoDeComprobante"))) if document_type else False, res_model]

    def _l10n_mx_edi_get_document_type(self, cfdi, vat):
        return (
            "customer" if cfdi.Emisor.get("Rfc") == vat else ("vendor" if cfdi.Receptor.get("Rfc") == vat else False)
        )
