from os.path import splitext

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    assing_document_tags(cr)


def assing_document_tags(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    domain = [("folder_id", "=", env.ref("documents.documents_finance_folder").id)]
    documents = env["documents.document"].search(domain)
    for doc in documents.filtered(lambda r: splitext(r.name)[1].upper() == ".XML"):
        doc._l10n_edi_document_assign_tags_and_folder()
