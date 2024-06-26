from odoo import api, fields, models


class MxEdiToRecordWizard(models.TransientModel):
    _name = "documents.mx_edi_to_record_wizard"
    _description = "MX EDI to Record"


    document_ids = fields.Many2many('documents.document', 'Documents', readonly=True)
    # invoice_date = fields.Date(
    #     compute="_compute_invoice_date",
    #     store=True,
    #     help="Date to be used in the invoice to generate, if is empty will be used the CFDI date.",
    # )
    # customer_journal_id = fields.Many2one(
    #     "account.journal",
    #     domain=lambda self: "[('type', '=', 'sale'), ('company_id', 'in', %s)]"
    #     % (self.company_id | self.env.company).ids,
    #     help="This journal will be used in the customer invoices generated by this document.",
    # )
    # vendor_journal_id = fields.Many2one(
    #     "account.journal",
    #     domain=lambda self: "[('type', '=', 'purchase'), ('company_id', 'in', %s)]"
    #     % (self.company_id | self.env.company).ids,
    #     help="This journal will be used in the vendor bills generated by this document.",
    # )
    # customer_account_id = fields.Many2one(
    #     "account.account",
    #     domain=lambda self: "[('company_id', 'in', %s)]" % (self.company_id | self.env.company).ids,
    #     help="This account will be used in the customer invoices generated by this document. If this account is not "
    #     "set, will be used the default account.",
    # )
    # vendor_account_id = fields.Many2one(
    #     "account.account",
    #     domain=lambda self: "[('company_id', 'in', %s)]" % (self.company_id | self.env.company).ids,
    #     help="This account will be used in the vendor bills generated by this document. If this account is not set, "
    #     "will be used the default account.",
    # )
    # analytic_account_id = fields.Many2one(
    #     "account.analytic.account",
    #     help="Analytic account to be used in the invoices to generate.",
    # )
    # show_customer_fields = fields.Boolean(compute="_compute_show_customer_fields")
    # show_vendor_fields = fields.Boolean(compute="_compute_show_customer_fields")
    # analytic_group = fields.Boolean(compute="_compute_show_fields")


    #@api.depends("folder_id")
    #def _compute_show_fields(self):
    #    folders = self.env.ref("documents.documents_finance_folder")
    #    folders |= self._get_children_folder_ids(folders)
    #    for record in self:
    #        record.in_finance_folder = record.folder_id in folders
    #        record.show_customer_fields = (record.company_id or self.env.company).l10n_edi_import_customer_invoices
    #        record.analytic_group = self.user_has_groups("analytic.group_analytic_accounting")

    def create_records(self):
        move_ids = []
        for document in self.document_ids:
            _is_cfdi, _is_cfdi_signed, cfdi_etree = self.env["l10n_mx_edi.document"].check_objectify_xml(document.datas)
            obj_exist = self.env["l10n_mx_edi.document"].xml2record(cfdi_etree)
            document.attachment_id.with_context(no_document=True).write(
                {
                    "res_model": "account.move",
                    "res_id": obj_exist.id,
                }
            )
            move_ids.append(obj_exist.id)
        context = dict(self._context)
        action = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "name": _("Moves"),
            "view_id": False,
            "view_mode": "tree",
            "views": [(False, "list"), (False, "form")],
            "domain": [("id", "in", move_ids)],
            "context": context,
        }
        if len(move_ids) == 1:
            record = obj_exist or self.env["account.move"].browse(move_ids[0])
            view_id = record.get_formview_id() if record else False
            action.update(
                {
                    "view_mode": "form",
                    "views": [(view_id, "form")],
                    "res_id": move_ids[0],
                    "view_id": view_id,
                }
            )
        return action