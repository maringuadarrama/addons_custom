# pylint: disable=missing-return
from odoo import _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class HrSuaReportHandler(models.AbstractModel):
    _name = "hr.sua.report.handler"
    _description = "SUA report"
    _inherit = "account.report.custom.handler"

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
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

    def _report_custom_engine_sua_report(
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
        date_from = fields.datetime.strptime(options["date"]["date_from"], DEFAULT_SERVER_DATE_FORMAT).date()
        date_to = fields.datetime.strptime(options["date"]["date_to"], DEFAULT_SERVER_DATE_FORMAT).date()
        for contract in contracts:
            employee = contract.employee_id
            loan = employee.loan_ids.filtered(
                lambda loan: loan.infonavit_type
                and (loan.payment_term == -1 or loan.payslips_count < loan.payment_term)
                and (not loan.date_from or loan.date_from <= date_from)
                and (not loan.date_to or loan.date_to >= date_to)
            )
            if not loan or not (contract.date_start >= date_from and contract.date_start <= date_to):
                continue
            p_columns = [
                {"name": employee.l10n_mx_edi_employer_registration_id.name or employee.company_id.company_registry},
                {"name": employee.ssnid},
                {"name": employee.l10n_mx_rfc},
                {"name": employee.l10n_mx_curp},
                {
                    "name": dict(employee._fields["l10n_mx_edi_type"]._description_selection(self.env)).get(
                        str(employee.l10n_mx_edi_type), ""
                    ),
                    "value": employee.l10n_mx_edi_type or "",
                },
                {
                    "name": dict(contract._fields["l10n_mx_edi_working_type"]._description_selection(self.env)).get(
                        str(contract.l10n_mx_edi_working_type), ""
                    ),
                    "value": contract.l10n_mx_edi_working_type or "",
                },
                {"name": fields.datetime.strftime(contract.date_start, "%d-%m-%Y")},
                {"name": contract.l10n_mx_edi_sdi_total},
                {"name": employee.pin},
                {"name": loan.name},
                {"name": fields.datetime.strftime(loan.date_from, "%d-%m-%Y") if loan else False},
                {
                    "name": dict(loan._fields["infonavit_type"]._description_selection(self.env)).get(
                        str(loan.infonavit_type), ""
                    ),
                    "value": loan.infonavit_type.replace("percentage", "1")
                    .replace("fixed_amount", "2")
                    .replace("vsm", "3"),
                },
                {"name": loan.amount},
            ]
            lines.append(
                {
                    "id": employee.id,
                    "name": employee.name,
                    "type": "line",
                    "footnotes": {},
                    "columns": p_columns,
                    "unfoldable": False,
                    "unfolded": True,
                    "colspan": 1,
                    "level": 2,
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
        return "SUA_%s_%s" % (vat, date.strftime("%Y%m"))

    def get_txt(self, options):
        ctx = self._set_context(options)
        ctx.update({"no_format": True, "print_mode": True, "raise": True})
        return self.with_context(**ctx)._l10n_mx_txt_export(options)

    def _l10n_mx_txt_export(self, options):
        lines = ""
        txt_data = self._get_lines(options)
        employee = self.env["hr.employee"]
        for line in txt_data:
            if line.get("type", False) != "line":
                continue
            columns = line.get("columns", [])
            data = [""] * 14
            employee = employee.browse(line["id"])
            data[0] = (columns[0]["name"] or "").ljust(11).upper()
            data[1] = (columns[1]["name"] or "").ljust(11)[:11]
            data[2] = (columns[2]["name"] or "").ljust(13).upper()
            data[3] = (columns[3]["name"] or "").ljust(18).upper()
            data[4] = (
                (
                    "%s$%s$%s"
                    % (
                        employee.lastname or employee.lastname2 or "",
                        employee.lastname2 or "" if employee.lastname else "",
                        employee.firstname or "",
                    )
                )
                .ljust(50)[:50]
                .upper()
            )
            data[5] = columns[4]["value"] or " "
            data[6] = columns[5]["value"] or " "
            data[7] = (columns[6]["name"] or "").replace("-", "").ljust(8)
            data[8] = (str(columns[7]["name"] or "")).replace(".", "").zfill(7)
            data[9] = (columns[8]["name"] or " ").ljust(17).upper()
            data[10] = (columns[9]["name"] or "").ljust(10)[:10]
            data[11] = (columns[10]["name"] or "").replace("-", "").zfill(8)
            data[12] = columns[11]["value"] or "0"
            data[13] = (str(columns[12]["name"] or "")).replace(".", "").zfill(8)
            lines += "".join(data).upper() + "\n"
        return lines
