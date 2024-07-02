# pylint: disable=missing-return
from odoo import _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class HrSuaMovReportHandler(models.AbstractModel):
    _name = "hr.sua.mov.report.handler"
    _description = "SUA report Movements"
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
        employees = self.env["hr.employee"].search([("active", "in", [False, True])])
        date_from = fields.datetime.strptime(options["date"]["date_from"], DEFAULT_SERVER_DATE_FORMAT).date()
        date_to = fields.datetime.strptime(options["date"]["date_to"], DEFAULT_SERVER_DATE_FORMAT).date()
        for employee in employees:
            if not employee.active and employee.departure_date >= date_from and employee.departure_date <= date_to:
                lines.append(
                    {
                        "id": employee.id,
                        "name": employee.name,
                        "columns": [{"name": ""} for x in range(7)],
                        "level": 1,
                        "unfoldable": True,
                        "unfolded": True,
                    }
                )
                p_columns = [
                    {
                        "name": employee.l10n_mx_edi_employer_registration_id.name
                        or employee.company_id.company_registry
                    },
                    {"name": employee.ssnid},
                    {"name": "Baja", "value": "02"},
                    {"name": fields.datetime.strftime(employee.departure_date, "%d-%m-%Y")},
                    {"name": employee.l10n_mx_edi_employer_registration_id.guide},
                    {"name": employee.barcode or employee.id},
                    {"name": employee.contract_id.l10n_mx_edi_sdi_total},
                ]
                lines.append(
                    {
                        "id": "02-%s" % employee.id,
                        "parent_id": employee.id,
                        "name": "",
                        "columns": p_columns,
                        "level": 2,
                        "unfoldable": False,
                        "unfolded": False,
                    }
                )
                continue
            contract = employee.contract_id
            if not contract:
                continue
            lines.append(
                {
                    "id": employee.id,
                    "name": employee.name,
                    "columns": [{"name": ""} for x in range(7)],
                    "level": 1,
                    "unfoldable": True,
                    "unfolded": True,
                }
            )
            show = False
            messages = contract.message_ids.filtered(
                lambda m: m.date.date() >= date_from and m.date.date() <= date_to and m.message_type == "notification"
            )
            if messages:
                tracking = (
                    messages.sudo().mapped("tracking_value_ids").filtered(lambda t: t.field.name == "l10n_mx_edi_sbc")
                )
                if tracking:
                    p_columns = [
                        {
                            "name": employee.l10n_mx_edi_employer_registration_id.name
                            or employee.company_id.company_registry
                        },
                        {"name": employee.ssnid},
                        {"name": "Wage Update", "value": "07"},
                        {
                            "name": fields.datetime.strftime(
                                tracking.sorted("create_date")[-1].create_date.date(), "%d-%m-%Y"
                            )
                        },
                        {"name": ""},
                        {"name": ""},
                        {"name": employee.contract_id.l10n_mx_edi_sdi_total},
                    ]
                    lines.append(
                        {
                            "id": "07-%s" % employee.id,
                            "parent_id": employee.id,
                            "name": "",
                            "columns": p_columns,
                            "level": 2,
                            "unfoldable": False,
                            "unfolded": False,
                        }
                    )
                    show = True
            # Ausencias
            leave = self.env.ref("hr_work_entry_contract.work_entry_type_unpaid_leave")
            domain = [("work_entry_type_id", "=", leave.id)]
            leaves = contract._get_worked_leaves(date_from, date_to, domain=domain)
            if leaves:
                leaves = self.env["hr.leave"]
                work_entry = self.env["hr.work.entry"].search(
                    contract._get_work_hours_domain(date_from, date_to, domain=domain, inside=True)
                )
                for entry in work_entry:
                    if entry.leave_id in leaves:
                        continue
                    p_columns = [
                        {
                            "name": employee.l10n_mx_edi_employer_registration_id.name
                            or employee.company_id.company_registry
                        },
                        {"name": employee.ssnid},
                        {"name": "Leaves", "value": "11"},
                        {"name": fields.datetime.strftime(entry.leave_id.date_from.date(), "%d-%m-%Y")},
                        {"name": False},
                        {"name": int(entry.leave_id.number_of_days)},
                        {"name": employee.contract_id.l10n_mx_edi_sdi_total},
                    ]
                    lines.append(
                        {
                            "id": "11-%s" % employee.id,
                            "parent_id": employee.id,
                            "name": "",
                            "columns": p_columns,
                            "level": 2,
                            "unfoldable": False,
                            "unfolded": True,
                        }
                    )
                    leaves |= entry.leave_id
                show = True
            # Incapacidades
            leave = self.env.ref("hr_work_entry_contract.work_entry_type_sick_leave")
            domain = [("work_entry_type_id", "=", leave.id)]
            leaves = contract._get_worked_leaves(date_from, date_to, domain=domain)
            if leaves:
                leaves = self.env["hr.leave"]
                work_entry = self.env["hr.work.entry"].search(
                    contract._get_work_hours_domain(date_from, date_to, domain=domain, inside=True)
                )
                for entry in work_entry:
                    if entry.leave_id in leaves:
                        continue
                    p_columns = [
                        {
                            "name": employee.l10n_mx_edi_employer_registration_id.name
                            or employee.company_id.company_registry
                        },
                        {"name": employee.ssnid},
                        {"name": "Inability", "value": "12"},
                        {"name": fields.datetime.strftime(entry.leave_id.date_from.date(), "%d-%m-%Y")},
                        {"name": entry.leave_id.name},
                        {"name": int(entry.leave_id.number_of_days)},
                        {"name": employee.contract_id.l10n_mx_edi_sdi_total},
                    ]
                    lines.append(
                        {
                            "id": "12-%s" % employee.id,
                            "parent_id": employee.id,
                            "name": "",
                            "columns": p_columns,
                            "level": 2,
                            "unfoldable": False,
                            "unfolded": True,
                        }
                    )
                    leaves |= entry.leave_id
                show = True
            if not show:
                lines.pop()
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
            if line.get("level", False) == 1:
                continue
            columns = line.get("columns", [])
            data = [""] * 7
            employee = employee.browse(line["id"])
            data[0] = (columns[0]["name"] or "").ljust(11)
            data[1] = (columns[1]["name"] or "").ljust(11)[:11]
            data[2] = columns[2]["value"] or "  "
            data[3] = (columns[3]["name"] or "").replace("-", "").ljust(8)
            data[4] = (columns[4]["name"] or "").ljust(8)[:8]
            data[5] = (str(columns[5]["name"]) or "").zfill(2)
            data[6] = (str(columns[6]["name"] or "")).replace(".", "").zfill(7)
            lines += "".join(data).upper() + "\n"
        return lines
