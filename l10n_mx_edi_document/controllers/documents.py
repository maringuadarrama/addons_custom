import html
import io
import re

from lxml import etree

from odoo import http
from odoo.http import request

from odoo.addons.web.controllers.binary import Binary


class BinaryL10nMxEdiDocument(Binary):
    @http.route(
        [
            "/web/content",
            "/web/content/<string:xmlid>",
            "/web/content/<string:xmlid>/<string:filename>",
            "/web/content/<int:id>",
            "/web/content/<int:id>/<string:filename>",
            "/web/content/<string:model>/<int:id>/<string:field>",
            "/web/content/<string:model>/<int:id>/<string:field>/<string:filename>",
        ],
        type="http",
        auth="public",
    )
    def content_common(
        self,
        xmlid=None,
        model="ir.attachment",
        id=None,
        field="raw",
        filename=None,
        filename_field="name",
        mimetype=None,
        unique=False,
        download=False,
        access_token=None,
        nocache=False,
    ):
        """Format the content of an XML CFDI file within the Documents previsualization iframe.

        If the document to open is an XML CFDI then the template xmlPreVisualization is shown, this
        contains data related to the XML CFDI."""
        # pylint: disable=redefined-builtin
        response = super().content_common(
            xmlid=xmlid,
            model=model,
            id=id,
            field=field,
            filename=filename,
            filename_field=filename_field,
            mimetype=mimetype,
            unique=unique,
            download=download,
            access_token=access_token,
            nocache=nocache,
        )
        if model == "documents.document" and id:
            xml = request.env[model].browse(id)
            if "xml" in xml.mimetype:
                pdf_content = xml.get_xml_data()
                if not pdf_content:
                    xml_content = xml.attachment_id.raw
                    pretty = self._pretty_print_xml(xml_content)
                    if pretty is not None:
                        xml_content = pretty
                    return "<pre>" + html.escape(xml_content.decode("utf-8")) + "</pre>"
                response = http.request.render(
                    "l10n_mx_edi_document.xmlPreVisualization", {"pdf_content": pdf_content}
                )
        return response

    def _pretty_print_xml(self, xml_str):
        """Prettify the XML (for example, when there is no spaces between tags)."""
        xml_str = xml_str.decode("utf-8")
        parser = etree.XMLParser(remove_blank_text=True, recover=True)
        version, encoding = self._get_meta_from_xml_header(xml_str)
        # Remove the XML header because the lmxl library can't parse it. More at information at:
        # https://stackoverflow.com/questions/28534460/lxml-etree-xml-valueerror-for-unicode-string
        no_head_tag_raw = self._get_content_withouth_xml_header(xml_str, version, encoding)
        try:
            file_obj = io.StringIO(no_head_tag_raw)
            tree = etree.parse(file_obj, parser)
            new_xml_header = self._create_xml_header(version, encoding)
            pretty = new_xml_header + etree.tostring(tree, pretty_print=True)
            return pretty
        except ValueError:
            return None

    def _get_meta_from_xml_header(self, content_str):
        """Get the version and encoding from the XML header."""
        version = ""
        encoding = ""
        match = re.search(r"<\?xml.*version=\"(.*)\" .*\?>", content_str)
        if match:
            version = match.group(1)
        match = re.search(r"<\?xml.*encoding=\"(.*)\".*\?>", content_str)
        if match:
            encoding = match.group(1)
        return version, encoding

    def _get_content_withouth_xml_header(self, content_str, version, encoding):
        """Remove the XML header from the content string."""
        header = re.compile(re.escape('<?xml version="%s" encoding="%s"?>' % (version, encoding)), re.IGNORECASE)
        content_str_clean = header.sub("", content_str)
        return content_str_clean

    def _create_xml_header(self, version, encoding):
        """Create the XML header with the version and encoding provided."""
        version_str = ""
        encoding_str = ""
        if version:
            version_str = 'version="%s"' % version
        if encoding:
            encoding_str = 'encoding="%s"' % encoding
        return b"<?xml %s %s?>\n" % (version_str.encode(encoding.lower()), encoding_str.encode(encoding.lower()))
