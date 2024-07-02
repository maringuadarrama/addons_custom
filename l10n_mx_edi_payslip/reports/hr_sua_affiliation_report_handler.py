# pylint: disable=missing-return
from odoo import _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class HrSuaAffiliationReportHandler(models.AbstractModel):
    _name = "hr.sua.affiliation.report.handler"
    _description = "SUA report Affiliation"
    _inherit = "account.report.custom.handler"

    filter_date = {"mode": "range", "filter": "this_month"}
    filter_hierarchy = None

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
        states = {
            "AGU": "01",
            "BCN": "02",
            "BCS": "03",
            "CAM": "04",
            "COA": "05",
            "COL": "06",
            "CHP": "07",
            "CHH": "08",
            "DIF": "09",
            "DUR": "10",
            "GUA": "11",
            "GRO": "12",
            "HID": "13",
            "JAL": "14",
            "MEX": "15",
            "MIC": "16",
            "MOR": "17",
            "NAY": "18",
            "NLE": "19",
            "OAX": "20",
            "PUE": "21",
            "QUE": "22",
            "ROO": "23",
            "SLP": "24",
            "SIN": "25",
            "SON": "26",
            "TAB": "27",
            "TAM": "28",
            "TLA": "29",
            "VER": "30",
            "YUC": "31",
            "ZAC": "32",
        }

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
                {"name": employee.private_zip},
                {"name": fields.datetime.strftime(employee.birthday, "%d-%m-%Y") if employee.birthday else False},
                {"name": employee.place_of_birth},
                {
                    "name": employee.l10n_mx_birth_state_id.name,
                    "value": (states.get(employee.l10n_mx_birth_state_id.code)),
                },
                {"name": employee.l10n_mx_edi_medical_unit},
                {"name": employee.job_title},
                {"name": employee.gender},
                {
                    "name": dict(contract._fields["l10n_mx_edi_salary_type"]._description_selection(self.env)).get(
                        str(contract.l10n_mx_edi_salary_type), ""
                    ),
                    "value": contract.l10n_mx_edi_salary_type or "",
                },
            ]
            lines.append(
                {
                    "id": employee.id,
                    "type": "line",
                    "level": 2,
                    "name": employee.name,
                    "footnotes": {},
                    "columns": p_columns,
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
            columns = line.get("columns", [])
            data = [""] * 10
            employee = employee.browse(line["id"])
            data[0] = (columns[0]["name"] or "").ljust(11)
            data[1] = (columns[1]["name"] or "").ljust(11)[:11]
            data[2] = (columns[2]["name"] or "").ljust(5)
            data[3] = (columns[3]["name"] or "").replace("-", "").ljust(8)
            data[4] = (columns[4]["name"] or "").ljust(25)[:25]
            data[5] = columns[5]["value"] or "  "
            data[6] = columns[6]["name"] or "   "
            data[7] = (columns[7]["name"] or "").ljust(12)[:12]
            data[8] = (columns[8]["name"] or " ")[0].upper()
            data[9] = columns[9]["value"] or " "
            lines += "".join(data).upper() + "\n"
        return lines
