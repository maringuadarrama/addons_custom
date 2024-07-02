from odoo import _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class HrIdseWageReportHandler(models.AbstractModel):
    _name = "hr.idse.wage.report.handler"
    _description = "IDSE report for Wage Update"
    _inherit = "account.report.custom.handler"

    def _custom_options_initializer(self, report, options, previous_options=None):
        res = super()._custom_options_initializer(report, options, previous_options=previous_options)
        options["columns"] = list(options["columns"])
        options.setdefault("buttons", []).extend(
            (
                {
                    "name": _("Export IMSS (TXT)"),
                    "sequence": 40,
                    "action": "export_file",
                    "action_param": "action_get_imss_txt",
                    "file_export_type": _("IMSS TXT"),
                },
            )
        )
        return res

    def _report_custom_engine_idse_report(
        self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None
    ):
        def build_dict(report, current_groupby, query_res):
            if not current_groupby:
                return query_res[0] if query_res else {k: None for k in report.mapped("line_ids.expression_ids.label")}
            return [(group_res["grouping_key"], group_res) for group_res in query_res]

        report = self.env["account.report"].browse(options["report_id"])
        # query_res = self._execute_query(report, current_groupby, options, offset, limit)
        query_res = self._get_lines(options)
        return build_dict(report, current_groupby, query_res)

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        contracts = self.env["hr.contract"].search(
            [
                ("state", "=", "open"),
            ]
        )
        date_from = fields.datetime.strptime(options["date"]["date_from"], DEFAULT_SERVER_DATE_FORMAT)
        date_to = fields.datetime.strptime(options["date"]["date_to"], DEFAULT_SERVER_DATE_FORMAT)
        for contract in contracts:
            messages = contract.message_ids.filtered(
                lambda m: m.date.date() >= date_from.date()
                and m.date.date() <= date_to.date()
                and m.message_type == "notification"
            )
            if not messages:
                continue
            tracking = (
                messages.sudo().mapped("tracking_value_ids").filtered(lambda t: t.field.name == "l10n_mx_edi_sbc")
            )
            if not tracking:
                continue
            employee = contract.employee_id
            p_columns = [
                {"name": employee.l10n_mx_edi_employer_registration_id.name or employee.company_id.company_registry},
                {"name": employee.ssnid},
                {"name": contract.l10n_mx_edi_sbc},
                {
                    "name": dict(employee._fields["l10n_mx_edi_type"]._description_selection(self.env)).get(
                        str(employee.l10n_mx_edi_type), ""
                    ),
                    "value": employee.l10n_mx_edi_type or "",
                },
                {
                    "name": dict(contract._fields["l10n_mx_edi_salary_type"]._description_selection(self.env)).get(
                        str(contract.l10n_mx_edi_salary_type), ""
                    ),
                    "value": contract.l10n_mx_edi_salary_type or "",
                },
                {
                    "name": dict(contract._fields["l10n_mx_edi_working_type"]._description_selection(self.env)).get(
                        str(contract.l10n_mx_edi_working_type), ""
                    ),
                    "value": contract.l10n_mx_edi_working_type or "",
                },
                {"name": fields.datetime.strftime(tracking.sorted("create_date")[-1].create_date.date(), "%d-%m-%Y")},
                {"name": employee.l10n_mx_edi_medical_unit},
                {"name": employee.l10n_mx_edi_employer_registration_id.guide},
                {"name": employee.barcode or employee.id},
                {"name": employee.l10n_mx_curp},
            ]
            lines.append(
                {
                    "id": employee.id,
                    "type": "line",
                    "name": employee.name,
                    "footnotes": {},
                    "columns": p_columns,
                    "level": 2,
                    "unfoldable": False,
                    "unfolded": True,
                    "colspan": 1,
                }
            )
        return lines

    @api.model
    def _get_report_name(self):
        # Get the month and year from report date filters if exists
        date = fields.date.today()
        if self._context.get("report_date"):
            date = fields.datetime.strptime(self._context["report_date"], "%Y-%m-%d")
        company = self.env.company
        vat = company.vat or ""
        return "IDSE_%s_%s" % (vat, date.strftime("%Y%m"))

    def get_txt(self, options):
        ctx = self._set_context(options)
        ctx.update({"no_format": True, "print_mode": True, "raise": True})
        return self.with_context(**ctx)._l10n_mx_txt_export(options)

    def _l10n_mx_txt_export(self, options):
        txt_data = self._get_lines(options)
        lines = ""
        employee = self.env["hr.employee"]
        for line in txt_data:
            if line.get("type", False) != "line":
                continue
            columns = line.get("columns", [])
            data = [""] * 20
            employee = employee.browse(line["id"])
            data[0] = (columns[0]["name"] or "").ljust(11)
            data[1] = (columns[1]["name"] or "").ljust(11)[:11]
            data[2] = (employee.lastname or "").ljust(27)[:27].upper()
            data[3] = (employee.lastname2 or "").ljust(27)[:27].upper()
            data[4] = (employee.firstname or "").ljust(27)[:27].upper()
            data[5] = (str(columns[2]["name"] or "")).replace(".", "").zfill(6)
            data[6] = "".ljust(6)
            data[7] = columns[3]["value"] or " "
            data[8] = columns[4]["value"] or " "
            data[9] = columns[5]["value"] or " "
            data[10] = (columns[6]["name"] or "").replace("-", "").ljust(8)
            data[12] = "".ljust(5)
            data[13] = "07"
            data[14] = (columns[8]["name"] or "").ljust(5)
            data[15] = (str(columns[9]["name"]) or "").ljust(10)
            data[16] = " "
            data[17] = (columns[10]["name"] or "").ljust(18)
            data[18] = "9"
            lines += "".join(data) + "\n"
        return lines
