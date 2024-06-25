from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    change_xml_ids(cr)
    uninstall_old_l10n_mx_documents(cr)


def uninstall_old_l10n_mx_documents(cr):
    """Uninstall custom module l10n_mx_edi_documents as it will be replaced."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    module = env["ir.module.module"].search([("name", "=", "l10n_mx_edi_documents")])
    if module:
        module.button_uninstall()


def change_xml_ids(cr):
    """Update records xml ids, set the new module that will replace module l10n_mx_edi_documents."""
    query = """
        UPDATE
            ir_model_data
        SET
            module = 'l10n_mx_edi_document'
        WHERE
            module = 'l10n_mx_edi_documents'
            AND name in (
                'xunnel_xml_facet',
                'ingreso_tag',
                'egreso_tag',
                'translado_tag',
                'reception_tag',
                'nomina_tag',
                'retencion_tag'
            )
    """
    query2 = """
        UPDATE
            ir_model_data
        SET
            module = 'l10n_edi_document'
        WHERE
            module = 'l10n_mx_edi_documents'
            AND name in (
                'l10n_edi_document_folder_edi_doc',
                'edi_document_rule',
                'documents_replace_inbox_edi_document',
                'documents_add_documents_edi_document',
                'documents_incorrect_edi_folder',
                'documents_edi_not_found_folder',
                'documents_edi_automatic_partner_tag',
                'documents_edi_facet',
                'documents_edi_automatic_tag',
                'documents_edi_partner_requires_po_tag',
                'documents_edi_requires_po_tag',
                'l10n_edi_document_folder_edi_received',
                'l10n_edi_document_folder_edi_issued',
                'l10n_edi_document_documents_without_records',
                'l10n_edi_document_facet_fiscal_month',
                'l10n_edi_document_fiscal_month_01',
                'l10n_edi_document_fiscal_month_02',
                'l10n_edi_document_fiscal_month_03',
                'l10n_edi_document_fiscal_month_04',
                'l10n_edi_document_fiscal_month_05',
                'l10n_edi_document_fiscal_month_06',
                'l10n_edi_document_fiscal_month_07',
                'l10n_edi_document_fiscal_month_08',
                'l10n_edi_document_fiscal_month_09',
                'l10n_edi_document_fiscal_month_10',
                'l10n_edi_document_fiscal_month_11',
                'l10n_edi_document_fiscal_month_12'
            )
    """
    cr.execute(query)
    cr.execute(query2)
