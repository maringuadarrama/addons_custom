from odoo import api, fields, models


class UsersAllowLogin(models.TransientModel):
    _name = "users.allow.login"
    _description = "Allow Login"

    user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="user_allow_login_user_rel",
        column1="wizard_id",
        column2="user_id",
        string="Users",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "user_ids" in fields_list and "user_ids" not in res:
            if self._context.get("active_model") == "res.users":
                res["user_ids"] = [(6, 0, self._context.get("active_ids", []))]
            elif self._context.get("active_model") == "hr.employee":
                employees = self.env["hr.employee"].browse(self._context.get("active_ids", []))
                res["user_ids"] = [(6, 0, employees.mapped("user_id").ids)]
        return res

    def logout_users(self):
        sessions = self.env["ir.sessions"].search([("logged_in", "=", True), ("user_id", "in", self.user_ids.ids)])
        return sessions.action_close_session()

    def logout_all_users(self):
        group = self.env.ref("users_working_hours.group_work_time_unlimited_access", False)
        users = self.env["res.users"].search([("id", "not in", group.users.ids)])
        self.user_ids = users
        return self.logout_users()

    def logout_and_block_users(self):
        self.env["ir.config_parameter"].sudo().set_param("user_workin_hours.not_allow_session", True)
        return self.logout_all_users()

    def allow_login(self):
        self.env["ir.config_parameter"].sudo().set_param("user_workin_hours.not_allow_session", False)
