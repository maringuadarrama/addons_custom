import odoo
from odoo import SUPERUSER_ID, _, http
from odoo.exceptions import AccessError
from odoo.http import request

from odoo.addons.web.controllers.session import Session


# pylint: disable=invalid-name
@http.route("/web/session/authenticate", type="json", auth="none")
def authenticate(self, db, login, password, base_location=None):
    if not http.db_filter([db]):
        raise AccessError(_("Database not found."))
    pre_uid = request.session.authenticate(db, login, password)
    if pre_uid != request.session.uid:
        # Crapy workaround for unupdatable Odoo Mobile App iOS (Thanks Apple :@) and Android
        # Correct behavior should be to raise AccessError("Renewing an expired session for user
        # that has multi-factor-authentication is not supported. Please use /web/login instead.")
        return {"uid": None}

    request.session.db = db
    registry = odoo.modules.registry.Registry(db)
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, request.session.uid, request.session.context)
        if not request.db and not request.session.is_explicit:
            # request._save_session would not update the session_token
            # as it lacks an environment, rotating the session myself
            http.root.session_store.rotate(request.session, env)
            max_age = http.SESSION_LIFETIME
            if request.session.uid and request.session.uid is not SUPERUSER_ID:
                user = env["res.users"].sudo().browse(request.session.uid)
                max_age = user._get_session_expiration_time()
            request.future_response.set_cookie("session_id", request.session.sid, max_age=max_age, httponly=True)
        return env["ir.http"].session_info()


Session.authenticate = authenticate
