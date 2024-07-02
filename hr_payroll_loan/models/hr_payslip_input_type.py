from odoo import fields, models


class HrPayslipInputType(models.Model):
    _inherit = "hr.payslip.input.type"

    use_in_loan = fields.Boolean(
        "Available for Loans",
        help="Select if this input could be used on loans salary rules",
    )
    loan_note = fields.Char(
        translate=True,
        help="This note will be shown on the Loans with this input type. "
        "It specifies some guidelines to fill the loan fields, such as the amount.",
    )
