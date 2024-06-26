from odoo import api, models


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    def logout_users(self):
        users = (
            self.env["hr.employee"]
            .search([("resource_calendar_id", "in", self.mapped("calendar_id").ids)])
            .mapped("user_id")
        )
        if not users:
            return
        wiz = self.env["users.allow.login"].create({"user_ids": [(6, 0, users.ids)]})
        wiz.logout_users()

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.logout_users()
        return res

    def write(self, values):
        fields2monitor = self._fields2monitor
        if fields2monitor is None:
            fields2monitor = []
        if values is None:
            values = {}
        changed = {field: values[field] for field in fields2monitor if field in values}
        if changed:
            self.logout_users()
        return super().write(values)

    def unlink(self):
        self.logout_users()
        return super().unlink()

    _fields2monitor = [
        "dayofweek",
        "date_from",
        "date_to",
        "hour_from",
        "hour_to",
    ]
