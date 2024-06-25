from odoo import api, fields, models


class UsersUpdateAttendance(models.TransientModel):
    _name = "users.update.attendance"
    _description = "Update Calendar Attendance"

    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        relation="update_attendance_employee_rel",
        column1="wizard_id",
        column2="employee_id",
        string="Employees",
        required=True,
        domain=[("resource_calendar_id", "!=", False), ("user_id", "!=", False)],
    )
    extended_hour = fields.Float(string="Work extended time (HH:MM)", required=True)

    @api.onchange("extended_hour")
    def _onchange_hours(self):
        # avoid negative or multiple days
        self.extended_hour = min(self.extended_hour, 23.99)
        self.extended_hour = max(self.extended_hour, 0.0)

    def update_attendance(self):
        users = self.employee_ids.mapped("user_id")
        users.write(
            {
                "extended_hour": self.extended_hour,
                "extended_date": fields.Date.context_today(self),
            }
        )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "employee_ids" in fields_list and "employee_ids" not in res:
            if self._context.get("active_model") == "hr.employee":
                res["employee_ids"] = [(6, 0, self._context.get("active_ids", []))]
        return res
