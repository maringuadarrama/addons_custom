import logging

from odoo import _, api, models
from odoo.exceptions import AccessError

from .res_users import no_impostor

_logger = logging.getLogger(__name__)


class Groups(models.Model):
    _inherit = "res.groups"

    @no_impostor
    @api.model_create_multi
    def create(self, vals_list):
        return super().create(vals_list)

    @no_impostor
    def write(self, values):
        # Can't grant admin access via UI except as admin
        check_groups = not self.env.su and "users" in values
        if not check_groups:
            return super().write(values)
        self.ensure_one()
        group_managers = self.env.ref("base.group_erp_manager")
        group_admins = self.env.ref("base.group_system")
        previous_managers = group_managers.users
        previous_admins = group_admins.users
        result = super().write(values)
        managers = group_managers.users
        admins = group_admins.users
        if (admins - previous_admins) or (managers - previous_managers):
            msg = _(
                "Privilege escalation attempt while modifying groups by %s, logged and reported!",
                self.env.user.login,
            )
            _logger.error(msg)
            raise AccessError(msg)
        return result

    @no_impostor
    def unlink(self):
        return super().unlink()
