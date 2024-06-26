from logging import getLogger

from odoo import SUPERUSER_ID, api, models, tools
from odoo.http import request

_logger = getLogger(__name__)

ALLOWED_MODEL_ACCESS = [
    "mail.channel",
    "mail.channel.partner",
    "res.users.log",
    "website.visitor",
    "website.track",
]


class IrModelAccess(models.Model):
    _inherit = "ir.model.access"

    @api.model
    @tools.ormcache_context("self.env.uid", "self.env.su", "model", "mode", "raise_exception", keys=("lang",))
    def check(self, model, mode="read", raise_exception=True):
        # We have to copy the sanity checks of the super function
        if self.env.su:
            # User root have all accesses
            return True

        assert mode in ("read", "write", "create", "unlink"), "Invalid access mode"

        if isinstance(model, models.BaseModel):
            assert model._name == "ir.model", "Invalid model object"
            model_name = model.model
        else:
            model_name = model

        # Log out users functionality
        if model not in ALLOWED_MODEL_ACCESS:
            self.check_allowed_session()

        # TransientModel records have no access rights, only an implicit access rule
        if model_name not in self.env:
            _logger.error("Missing model %s", model_name)
        elif self.env[model_name].is_transient():
            return True

        return super().check(model, mode, raise_exception)

    def check_allowed_session(self):
        skip_test = any(
            (
                # It usually fails when installing other addons with demo data
                self.with_user(SUPERUSER_ID)
                .env["ir.module.module"]
                .search(
                    [
                        ("state", "in", ["to install", "to upgrade"]),
                        ("demo", "=", True),
                    ]
                ),
                # Avoid breaking unaware addons' tests by default
                tools.config["test_enable"] or tools.config["test_file"],
            )
        )
        if skip_test:
            return True
        user = self.env.user
        if not user or user == self.env.ref("base.public_user"):
            return True
        sess_id = request.session.sid
        sessions = user._get_sessions([sess_id])
        if not sessions:
            sessions = user._get_sessions([sess_id], False)
            if sessions:
                request.session.logout(keep_db=True)
                return False
            user.save_session(sess_id)
        if self.user_has_groups("users_working_hours.group_work_time_unlimited_access"):
            return True
        if self.env["ir.config_parameter"].sudo().get_param("user_workin_hours.not_allow_session"):
            sessions._on_session_logout("to")
            request.future_response.set_cookie("session_id", max_age=0)
            return False
        return True
