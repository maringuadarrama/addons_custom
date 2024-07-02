from odoo import api, models


class L10nMxEdiDocument(models.Model):
    _inherit = "l10n_mx_edi.document"

    @api.model
    def _decode_cfdi_attachment(self, cfdi_data):
        """Override to add the certificate provider RFC to the data dictionary."""
        res = super()._decode_cfdi_attachment(cfdi_data)
        if not res or not res.get("cfdi_node", False):
            return res
        complement_node = res.get("cfdi_node").find(".//{*}Complemento")
        if complement_node is None:
            return res
        tfd_node = complement_node.xpath(
            "tfd:TimbreFiscalDigital[1]", namespaces={"tfd": "http://www.sat.gob.mx/TimbreFiscalDigital"}
        )
        if len(tfd_node) > 0:
            res["certificate_provider_rfc"] = tfd_node[0].get("RfcProvCertif", False)
        return res
