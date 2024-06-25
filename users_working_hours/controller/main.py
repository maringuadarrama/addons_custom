from odoo import http
from odoo.http import request

from odoo.addons.web.controllers.session import Session


class SessionLogin(Session):
    @http.route("/web/session/logout", type="http", auth="none")
    def logout(self, redirect="/web"):
        if request.session:
            sessions = request.env["ir.sessions"].search(
                [("logged_in", "=", True), ("user_id", "=", request.session.uid)]
            )
            if sessions:
                sessions._on_session_logout(logout_type="ul")
        request.session.logout(keep_db=True)
        return super().logout(redirect=redirect)
