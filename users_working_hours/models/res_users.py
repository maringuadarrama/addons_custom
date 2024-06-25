from datetime import datetime, timedelta
from math import floor

from pytz import timezone

from odoo import _, fields, models
from odoo.exceptions import AccessDenied
from odoo.http import SESSION_LIFETIME


class ResUsers(models.Model):
    _inherit = "res.users"

    extended_hour = fields.Float(string="Work extended time", help="Time extension of access to the instance.")
    extended_date = fields.Date(
        string="Work extended date", help="Date on which the access time extension applies on."
    )

    def _get_session_expiration_time(self):
        has_group = self.has_group("users_working_hours.group_work_time_unlimited_access")
        if has_group:
            return SESSION_LIFETIME
        param = self.env["ir.config_parameter"].sudo().get_param("user_workin_hours.not_allow_session")
        if param:
            return 0
        calendar = self.employee_id.resource_calendar_id or self.resource_calendar_id
        if not calendar:
            return SESSION_LIFETIME
        now = datetime.now(tz=timezone(calendar.tz))
        now_time = now.hour + now.minute / 60.0
        time_extension = self.extended_date and self.extended_date == now.date() and self.extended_hour or 0.0
        attendance = self.env["resource.calendar.attendance"].search(
            [
                ("calendar_id", "=", calendar.id),
                ("dayofweek", "=", str(now.date().weekday())),
                ("hour_from", "<=", now_time),
            ],
            order="hour_to desc",
            limit=1,
        )
        if not attendance:
            yesterday = (now - timedelta(days=1)).date()
            if not self.extended_date or self.extended_date != yesterday:
                return 0
            attendance = self.env["resource.calendar.attendance"].search(
                [
                    ("calendar_id", "=", calendar.id),
                    ("dayofweek", "=", str(yesterday.weekday())),
                ],
                order="hour_to desc",
                limit=1,
            )
            if not attendance:
                return 0
            time_extension = (self.extended_hour or 0.0) - 24.0
        hour_to = max(min(attendance.hour_to + time_extension, 23.99), 0.0)
        minutes = round(hour_to % 1 * 60)
        hours = floor(hour_to)
        now_2 = now.replace(hour=hours, minute=minutes, second=0)
        delta = (now_2 - now).total_seconds()
        return round(delta) if delta > 0 else 0

    def _check_credentials(self, password, env):
        res = super()._check_credentials(password, env)
        session_time = self._get_session_expiration_time()
        if not session_time:
            raise AccessDenied(_("User not allowed to login at this specific time or day"))
        return res

    def save_session(self, session_id, logged_in=True):
        sessions = self._get_sessions(session_ids=[session_id], logged_in=logged_in)
        if not sessions:
            values = {
                "user_id": self.id,
                "logged_in": True,
                "session_id": session_id,
                "date_login": fields.datetime.now(),
            }
            self.env["ir.sessions"].sudo().create(values)

    def _get_sessions(self, session_ids=False, logged_in=True):
        session_obj = self.env["ir.sessions"].sudo()
        domain = [("user_id", "in", self.ids)]
        if session_ids:
            domain.append(("session_id", "in", session_ids))
        if logged_in:
            domain.append(("logged_in", "=", True))
        return session_obj.search(domain)

    def action_extend_work_time(self):
        return self.mapped("employee_id").action_extend_work_time()

    def action_logout_users(self):
        action = self.env["ir.actions.actions"]._for_xml_id("users_working_hours.action_users_allow_login")
        action["context"] = {
            "active_model": self._name,
            "active_ids": self.ids,
        }
        return action
