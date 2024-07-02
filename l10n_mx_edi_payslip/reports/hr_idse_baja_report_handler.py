from odoo import _, api, fields, models


class HrIdseBajaReportHandler(models.AbstractModel):
    _name = "hr.idse.baja.report.handler"
    _description = "IDSE report Baja"
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
        employees = self.env["hr.employee"].search(
            [
                ("active", "=", False),
                ("departure_date", ">=", options["date"]["date_from"]),
                ("departure_date", "<=", options["date"]["date_to"]),
            ]
        )
        for employee in employees:
            p_columns = [
                {"name": employee.l10n_mx_edi_employer_registration_id.name or employee.company_id.company_registry},
                {"name": employee.ssnid},
                {"name": fields.datetime.strftime(employee.departure_date, "%d-%m-%Y")},
                {"name": employee.l10n_mx_edi_employer_registration_id.guide},
                {"name": employee.barcode or employee.id},
                {"name": employee.departure_reason_id.l10n_mx_code},
            ]
            lines.append(
                {
                    "id": employee.id,
                    "name": employee.name,
                    "columns": p_columns,
                    "level": 2,
                    "unfoldable": False,
                    "unfolded": True,
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
            columns = line.get("columns", [])
            data = [""] * 20
            employee = employee.browse(line["id"])
            data[0] = (columns[0]["name"] or "").ljust(11)
            data[1] = (columns[1]["name"] or "").ljust(11)[:11]
            data[2] = (employee.lastname or "").ljust(27)[:27].upper()
            data[3] = (employee.lastname2 or "").ljust(27)[:27].upper()
            data[4] = (employee.firstname or "").ljust(27)[:27].upper()
            data[6] = "".zfill(15)
            data[10] = (columns[2]["name"] or "").replace("-", "").ljust(8)
            data[12] = "".ljust(5)
            data[13] = "02"
            data[14] = (columns[3]["name"] or "").ljust(5)
            data[15] = (str(columns[4]["name"]) or "").ljust(10)
            data[16] = str(columns[5]["name"] or "")
            data[17] = "".ljust(18)
            data[18] = "9"
            lines += "".join(data) + "\n"
        return lines
