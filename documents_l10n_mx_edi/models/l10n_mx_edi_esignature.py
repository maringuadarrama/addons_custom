import base64
import ssl
import subprocess
import tempfile
from datetime import datetime

from OpenSSL import crypto
from pytz import timezone

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

DEFAULT_TZ = timezone("America/Mexico_City")


def convert_key_cer_to_pem(key, password):
    # TODO compute it from a python way
    with tempfile.NamedTemporaryFile(
        "wb", suffix=".key", prefix="edi.mx.tmp."
    ) as key_file, tempfile.NamedTemporaryFile(
        "wb", suffix=".txt", prefix="edi.mx.tmp."
    ) as pwd_file, tempfile.NamedTemporaryFile(
        "rb", suffix=".key", prefix="edi.mx.tmp."
    ) as keypem_file:
        key_file.write(key)
        key_file.flush()
        pwd_file.write(password)
        pwd_file.flush()
        subprocess.call(
            (
                "openssl pkcs8 -in %s -inform der -outform pem -out %s -passin file:%s"
                % (key_file.name, keypem_file.name, pwd_file.name)
            ).split()
        )
        key_pem = keypem_file.read()
    return key_pem


# pylint: disable=invalid-name
def str_to_datetime(dt_str, tz=DEFAULT_TZ):
    return tz.localize(fields.Datetime.from_string(dt_str))


class Esignature(models.Model):
    _name = "l10n_mx_edi.esignature"
    _description = "MX E-signature"

    content = fields.Binary(
        string="Esignature",
        help="Esignature in der format",
        required=True,
        attachment=False,
    )
    key = fields.Binary(
        string="Esignature Key",
        help="Esignature Key in der format",
        required=True,
        attachment=False,
    )
    password = fields.Char(
        string="Esignature Password",
        help="Password for the Esignature Key",
        required=True,
    )
    holder = fields.Char(
        help="Holder for the certificate",
        required=False,
    )
    holder_vat = fields.Char(
        string='Holder"s VAT',
        help='Holder"s Vat for the certificate',
        required=False,
    )
    serial_number = fields.Char(
        string="Serial number", help="The serial number to add to electronic documents", readonly=True, index=True
    )
    date_start = fields.Datetime(
        string="Available date", help="The date on which the certificate starts to be valid", readonly=True
    )
    date_end = fields.Datetime(
        string="Expiration date", help="The date on which the certificate expires", readonly=True
    )
    company_id = fields.Many2one("res.company", "Company", default=lambda self: self.env.company)

    @tools.ormcache("content")
    def get_pem_cer(self, content):
        """Get the current content in PEM format"""
        self.ensure_one()
        return ssl.DER_cert_to_PEM_cert(base64.decodebytes(content)).encode("UTF-8")

    @tools.ormcache("key", "password")
    def get_pem_key(self, key, password):
        """Get the current key in PEM format"""
        self.ensure_one()
        return convert_key_cer_to_pem(base64.decodebytes(key), password.encode("UTF-8"))

    def get_cert_data(self):
        """Return the content (b64 encoded) and the certificate decrypted"""
        self.ensure_one()
        cer_pem = self.get_pem_cer(self.content)
        certificate = crypto.load_certificate(crypto.FILETYPE_PEM, cer_pem)
        for to_del in ["\n", ssl.PEM_HEADER, ssl.PEM_FOOTER]:
            cer_pem = cer_pem.replace(to_del.encode("UTF-8"), b"")
        return cer_pem, certificate

    def get_pk_data(self):
        """Return the content (b64 encoded) and the certificate decrypted"""
        self.ensure_one()
        key_pem = convert_key_cer_to_pem(base64.decodebytes(self.key), self.password.encode("UTF-8"))
        private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
        return key_pem, private_key

    def get_mx_current_datetime(self):
        """Get the current datetime with the Mexican timezone."""
        return fields.Datetime.context_timestamp(self.with_context(tz="America/Mexico_City"), fields.Datetime.now())

    def get_valid_esignature(self):
        """Search for a valid esignature that is available and not expired."""
        mexican_dt = self.get_mx_current_datetime()
        for record in self:
            date_start = str_to_datetime(record.date_start)
            date_end = str_to_datetime(record.date_end)
            if date_start <= mexican_dt <= date_end:
                return record
        return None

    @api.constrains("content", "key", "password")
    def _check_credentials(self):
        """Check the validity of content/key/password and fill the fields
        with the certificate values.
        """
        mexican_tz = timezone("America/Mexico_City")
        mexican_dt = self.get_mx_current_datetime()
        date_format = "%Y%m%d%H%M%SZ"
        for record in self:
            # Try to decrypt the certificate
            try:
                _cer_pem, certificate = record.get_cert_data()
                before = mexican_tz.localize(
                    datetime.strptime(certificate.get_notBefore().decode("utf-8"), date_format)
                )
                after = mexican_tz.localize(datetime.strptime(certificate.get_notAfter().decode("utf-8"), date_format))
                serial_number = certificate.get_serial_number()
                holder = certificate.get_subject().CN
                holder_vat = certificate.get_subject().x500UniqueIdentifier.split(" ")[0]
            except UserError as exc_orm:
                raise exc_orm
            except Exception:
                raise ValidationError(_("The esignature content is invalid."))
            # Assign extracted values from the certificate
            record.holder = holder
            record.holder_vat = holder_vat
            record.serial_number = ("%x" % serial_number)[1::2]
            record.date_start = before.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            record.date_end = after.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            if mexican_dt > after:
                raise ValidationError(_("The certificate is expired since %s", record.date_end))
            # Check the pair key/password
            try:
                record.get_pk_data()
            except Exception:
                raise ValidationError(_("The certificate key and/or password is/are invalid."))
