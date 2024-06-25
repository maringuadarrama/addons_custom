from odoo import models


class PosCashTransferWizard(models.TransientModel):
    _inherit = "pos.cash.transfer.wizard"

    def _get_schedule_activity_users(self):
        res = super()._get_schedule_activity_users()
        job = self.env.ref("xiuman_data.hr_job_14")
        users = self.env["hr.employee"].search([("job_id", "=", job.id)]).mapped("user_id")
        return users or res
