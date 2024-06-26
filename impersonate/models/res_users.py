import logging

from decorator import decorator

from odoo import _, api, models
from odoo.exceptions import AccessDenied, AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)


def no_impostor(method):
    """Decorator for unmasking an impostor during a method call.

    Invokes the decorated method with the original credentials
    of the impostor, if there is one. This prevents abusing the
    access rights of the impersonated user.
    """

    def unmask(method, self, *args, **kwargs):
        if request and request.session.impostor:
            self = self.with_user(request.session.impostor)
        return method(self, *args, **kwargs)

    return decorator(unmask, method)


class Users(models.Model):
    _inherit = "res.users"

    @api.model
    def _check_credentials(self, password, user_agent_env):
        try:
            res = super()._check_credentials(password, user_agent_env)
        except AccessDenied:
            credentials = password.partition("/")
            login = credentials[0]
            password = credentials[2]
            if not (login and password):
                raise
            impostor = self.sudo().search([("login", "=", login)], limit=1)
            if not impostor:
                raise
            impostor = impostor.with_user(impostor)
            res = super(Users, impostor)._check_credentials(password, user_agent_env)
            can_spoof_employee = impostor.has_group("impersonate.group_user_spoof")
            can_spoof_customer = impostor.has_group("impersonate.group_customer_spoof")
            spoofed_is_employee = self.has_group("base.group_user")
            allowed = can_spoof_employee or (can_spoof_customer and not spoofed_is_employee)
            if not allowed:
                raise
            support_level = 3
            groups = ["group_support_technical", "group_support_functional", "group_support_salesman"]
            for group in groups:
                if impostor.has_group("impersonate.%s" % group):
                    break
                support_level -= 1
            if request:
                request.session.impostor = impostor.id
                request.session.impostor_info = {
                    "id": impostor.id,
                    "login": impostor.login,
                    "level": support_level,
                }
            _logger.info(
                "User `%s` (#%d) connected as user `%s` (#%d)",
                impostor.login,
                impostor.id,
                self.env.user.login,
                self.env.uid,
            )
        return res

    @no_impostor
    @api.model_create_multi
    def create(self, vals_list):
        # Can't grant admin access via UI except as admin
        new_users = super().create(vals_list)
        new_admins = new_users.filtered(lambda u: u._is_admin())
        if not self.env.su and new_admins:
            msg = _(
                "Privilege escalation attempt while creating an user by %s, logged and reported!",
                self.env.user.login,
            )
            _logger.error(msg)
            raise AccessError(msg)
        return new_users

    @no_impostor
    def write(self, values):
        were_admins = self.filtered(lambda u: u._is_admin())
        result = super().write(values)
        are_admins = self.filtered(lambda u: u._is_admin())
        new_admins = are_admins - were_admins
        # Can't grant admin access via UI except as admin
        if not self.env.su and new_admins:
            msg = _(
                "Privilege escalation attempt while modifying an user by %s, logged and reported!",
                self.env.user.login,
            )
            _logger.error(msg)
            raise AccessError(msg)
        return result

    @no_impostor
    def unlink(self):
        return super().unlink()
