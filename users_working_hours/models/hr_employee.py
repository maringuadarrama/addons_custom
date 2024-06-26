from odoo import models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def action_extend_work_time(self):
        records = self.filtered(lambda hre: hre.resource_calendar_id and hre.user_id)
        action = self.env["ir.actions.actions"]._for_xml_id("users_working_hours.action_users_update_attendance")
        action["context"] = {
            "active_model": self._name,
            "active_ids": records.ids,
        }
        return action

    def action_logout_users(self):
        records = self.filtered(lambda hre: hre.user_id)
        action = self.env["ir.actions.actions"]._for_xml_id("users_working_hours.action_users_allow_login")
        action["context"] = {
            "active_model": self._name,
            "active_ids": records.ids,
        }
        return action
