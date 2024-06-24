from odoo import api, fields, models


class SyngentaSaleAgreement(models.Model):
    _name = "syngenta.sale.agreement"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    company_id = fields.Many2one("res.company", index=True, required=True, default=lambda self: self.env.company.id)
    partner_id = fields.Many2one(
        "res.partner",
        "Customer",
        required=True,
    )
    name = fields.Char(related="partner_id.name", readonly=True)
    number = fields.Char()
    active = fields.Boolean(default=True)
    date_from = fields.Date("From")
    date_to = fields.Date("To")
    agreement_type = fields.Selection(
        [
            ("ally", "Strategic ally"),
            ("big grower", "Big grower"),
            ("ornamentals", "Ornamentals"),
            ("other", "Other"),
        ],
        "Customer type",
    )
    state = fields.Selection(
        [
            ("in_progress", "In Progress"),
            ("closed", "Closed"),
        ],
        "state",
        default="in_progress",
        readonly=True,
    )
    predecesor_id = fields.Many2one(
        "syngenta.sale.agreement",
        "Predecesor agreement",
    )
    sale_line_ids = fields.One2many(
        "syngenta.sale.line",
        "agreement_id",
        "Sale Lines",
        auto_join=True,
        copy=True,
    )
    amount = fields.Float(
        "Amount",
        digits=(16, 2),
        help="Amount asigned to the sale agreement that will be used as base for following calculations.",
    )
    amount_reached = fields.Float(
        "Amount reached",
        digits=(16, 2),
        help="Amount asigned to the sale agreement that will be used as base for following calculations.",
    )
    percentage = fields.Float(
        "Percentage",
        digits=(5, 2),
        help="The base percentage of discount that this agreement can asign to the customers purchases.",
    )
    percentage_reached = fields.Float(
        "Percentage reached",
        digits=(5, 2),
        help="The base percentage of discount that this agreement can asign to the customers purchases.",
    )
    notes = fields.Html(
        "Terms and Conditions", help="The reach levels with their respective discount must be noted here."
    )
    document_ids = fields.One2many(
        "syngenta.sale.document",
        "agreement_id",
        "Documents",
    )
    line_count = fields.Integer(compute="_compute_line_count")
    document_count = fields.Integer(compute="_compute_document_count")

    @api.depends("name", "date_from", "date_to")
    def _compute_display_name(self):
        for agreement in self.sudo():
            name = agreement.name and agreement.name.split("\n")[0] or ""
            if agreement.date_from and agreement.date_to:
                name = "{} [{} - {}]".format(name, agreement.date_from, agreement.date_to)
            agreement.display_name = name

    def action_view_documents(self, documents=False):
        if not documents:
            documents = self.mapped("document_ids")
        action = self.env["ir.actions.actions"]._for_xml_id("syngenta_edi.action_syngenta_sale_document")
        if len(documents) > 1:
            action["domain"] = [("id", "in", documents.ids)]
        elif len(documents) == 1:
            form_view = [(self.env.ref("syngenta_edi.view_syngenta_sale_document_form").id, "form")]
            if "views" in action:
                action["views"] = form_view + [(state, view) for state, view in action["views"] if view != "form"]
            else:
                action["views"] = form_view
            action["res_id"] = documents.id
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action

    def action_view_lines(self, lines=False):
        if not lines:
            lines = self.mapped("sale_line_ids")
        action = self.env["ir.actions.actions"]._for_xml_id("syngenta_edi.action_syngenta_sale_line")
        if len(lines) >= 1:
            action["domain"] = [("id", "in", lines.ids)]
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action

    @api.depends("document_ids")
    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    @api.depends("sale_line_ids")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.sale_line_ids)

    def action_close(self):
        self.state = "closed"

    def action_new_document(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("syngenta_edi.action_syngenta_sale_document")
        action["views"] = [(self.env.ref("syngenta_edi.view_syngenta_sale_document_form").id, "form")]
        action["context"] = {
            "default_agreement_id": self.id,
        }
        return action
