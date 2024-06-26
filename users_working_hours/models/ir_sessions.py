import werkzeug

from odoo import SUPERUSER_ID, fields, models

LOGOUT_TYPES = [
    ("ul", "User Logout"),
    ("to", "Session Timeout"),
    ("sk", "Session Killed"),
]


class IrSessions(models.Model):
    _name = "ir.sessions"
    _description = "Sessions"

    user_id = fields.Many2one("res.users", "User", ondelete="cascade", required=True)
    logged_in = fields.Boolean("Logged in", required=True, index=True)
    session_id = fields.Char("Session ID", size=100, required=True)
    date_login = fields.Datetime("Login", required=True)
    date_logout = fields.Datetime("Logout")
    logout_type = fields.Selection(LOGOUT_TYPES)
    user_kill_id = fields.Many2one(
        "res.users",
        "Killed by",
    )

    _order = "logged_in desc, date_login desc"

    def action_close_session(self):
        redirect = self._close_session(logout_type="sk")
        if redirect:
            return werkzeug.utils.redirect("/web/login?db=%s" % self.env.cr.dbname, 303)

    def _on_session_logout(self, logout_type=None):
        cr = self.pool.cursor()
        cr._cnx.autocommit = True

        for session in self:
            session.sudo().write(
                {
                    "logged_in": False,
                    "logout_type": logout_type,
                    "user_kill_id": self.env.user.id or SUPERUSER_ID,
                }
            )
        cr.commit()  # pylint:disable=invalid-commit
        cr.close()
        return True

    def _close_session(self, logout_type=None):
        redirect = False
        for session in self:
            if session.user_id.id == self.env.user.id:
                redirect = True
            session._on_session_logout(logout_type)
        return redirect
