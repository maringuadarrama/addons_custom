import logging
from os.path import splitext

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class Document(models.Model):
    _inherit = "documents.document"

    edi_reference = fields.Char(
        string="Reference",
        compute="_compute_partner_and_reference",
        store=True,
    )
    tag_ids = fields.Many2many(compute="_compute_tags", inverse="_inverse_tags", store=True)
    customer_journal_id = fields.Many2one(
        "account.journal",
        domain=lambda self: "[('type', '=', 'sale'), ('company_id', 'in', %s)]"
        % (self.company_id | self.env.company).ids,
        help="This journal will be used in the customer invoices generated by this document.",
    )
    vendor_journal_id = fields.Many2one(
        "account.journal",
        domain=lambda self: "[('type', '=', 'purchase'), ('company_id', 'in', %s)]"
        % (self.company_id | self.env.company).ids,
        help="This journal will be used in the vendor bills generated by this document.",
    )
    customer_account_id = fields.Many2one(
        "account.account",
        domain=lambda self: "[('company_id', 'in', %s)]" % (self.company_id | self.env.company).ids,
        help="This account will be used in the customer invoices generated by this document. If this account is not "
        "set, will be used the default account.",
    )
    vendor_account_id = fields.Many2one(
        "account.account",
        domain=lambda self: "[('company_id', 'in', %s)]" % (self.company_id | self.env.company).ids,
        help="This account will be used in the vendor bills generated by this document. If this account is not set, "
        "will be used the default account.",
    )
    in_finance_folder = fields.Boolean(
        compute="_compute_show_fields",
        store=True,
        help="Indicates if document is in finance folder",
    )
    show_customer_fields = fields.Boolean(compute="_compute_show_customer_fields", store=True)
    analytic_group = fields.Boolean(compute="_compute_show_fields", store=True)
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        help="Analytic account to be used in the invoices to generate.",
    )
    invoice_date = fields.Date(
        help="Date to be used in the invoice to generate, if is empty will be used the CFDI date.",
        compute="_compute_invoice_date",
        store=True,
    )

    @api.depends("attachment_id")
    def _compute_partner_and_reference(self):
        for record in self.filtered(lambda r: r.attachment_id):
            record.partner_id = record._get_document_edi_partner()
            record.edi_reference = record._get_document_edi_reference()

    @api.depends("partner_id")
    def _compute_tags(self):
        for record in self.filtered(lambda r: (splitext(r.name)[1].upper() == ".XML") and r.partner_id):
            tag_pairs = [
                (  # Tag to process document automatically
                    self.env.ref("l10n_edi_document.documents_edi_automatic_partner_tag"),
                    self.env.ref("l10n_edi_document.documents_edi_automatic_tag"),
                ),
                (  # Invoice requires PO to be processed
                    self.env.ref("l10n_edi_document.documents_edi_partner_requires_po_tag"),
                    self.env.ref("l10n_edi_document.documents_edi_requires_po_tag"),
                ),
            ]
            for pair in tag_pairs:
                partner_tag, document_tag = pair
                if partner_tag in record.partner_id.category_id:
                    record.tag_ids |= document_tag

    @api.depends("folder_id")
    def _compute_show_fields(self):
        folders = self.env.ref("documents.documents_finance_folder")
        folders |= self._get_children_folder_ids(folders)
        for record in self:
            record.in_finance_folder = record.folder_id in folders
            record.show_customer_fields = (record.company_id or self.env.company).l10n_edi_import_customer_invoices
            record.analytic_group = self.user_has_groups("analytic.group_analytic_accounting")

    @api.depends("attachment_id")
    def _compute_invoice_date(self):
        for record in self.filtered(lambda r: splitext(r.name)[1].upper() == ".XML"):
            record.invoice_date = record._l10n_edi_get_invoice_date()

    def _l10n_edi_get_invoice_date(self):
        """This method is intended to be overridden by l10n modules to read the invoice date
        from the document attachment.
        """
        return False

    def _inverse_tags(self):
        for _record in self:
            continue

    def _get_document_edi_partner(self):
        """Override this method in l10n modules to read the partner value from the document attachment."""
        self.ensure_one()
        return self.env["res.partner"]

    def _get_document_edi_reference(self):
        """Override this method in l10n modules to read the reference value from the document attachment."""
        self.ensure_one()
        return False

    def _l10n_edi_document_automatic_process(self, limit=10):
        """This method is called by the cron to process the documents."""
        tag = self.env.ref("l10n_edi_document.documents_edi_automatic_tag")
        workflow = self.env.ref("l10n_edi_document.edi_document_rule")
        records = self.search([("partner_id", "!=", False)]).filtered(
            lambda r: (splitext(r.name)[1].upper() == ".XML") and tag in r.tag_ids
        )
        for record in records[:limit]:
            try:
                with self.env.cr.savepoint():
                    workflow.create_record(record)
            except Exception as e:
                _logger.error(e)

    def _l10n_edi_document_assign_tags_and_folder(self):
        """This method is called when a document is created to assign the tags
        and is intended to be overridden by l10n modules.
        """
        self.ensure_one()
        return False

    @api.model_create_multi
    def create(self, vals_list):
        documents = super().create(vals_list)
        for doc in documents.filtered(lambda r: splitext(r.name)[1].upper() == ".XML"):
            doc._l10n_edi_document_assign_tags_and_folder()
        return documents

    # Recursive function to fetch children
    def _get_children_folder_ids(self, folder_ids):
        if not folder_ids:
            return self.env["documents.folder"]
        subfolders = folder_ids.mapped("children_folder_ids")
        if subfolders:
            subfolders |= self._get_children_folder_ids(subfolders)
        return subfolders
