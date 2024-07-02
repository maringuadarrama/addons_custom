from odoo import fields
from odoo.tests.common import tagged

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged("hr_idse", "post_install", "-at_install")
class TestHrIdse(TestAccountReportsCommon):
    def setUp(self):
        super().setUp()
        self.env["hr.contract"].search([]).write({"state": "draft"})
        self.contract = self.env.ref("l10n_mx_edi_payslip.hr_contract_maria")
        self.contract.state = "open"
        self.contract._compute_integrated_salary()

    def test_001_insured(self):
        """Generated TXT for insured"""
        report = self.env["hr.idse.report"]
        options = self._generate_options(
            report, fields.Date.from_string("2022-01-01"), fields.Date.from_string("2022-12-31")
        )
        data = report.get_txt(options)
        self.assertEqual(
            data.replace("\n", ""),
            "1203256    12345678923OLIVIA                     MARTINEZ SAGAZ             MARIA                      "
            "076648      100{date}T21  08     {id}         PUXB571021HNELXR009".format(
                date=fields.datetime.strftime(self.contract.date_start, "%d%m%Y"), id=self.contract.employee_id.id
            ),
            "Error with IDSE generation",
        )

    def test_002_baja(self):
        """Generated TXT for baja"""
        self.env["hr.departure.wizard"].create(
            {
                "departure_reason_id": self.env.ref("hr.departure_fired").id,
                "employee_id": self.contract.employee_id.id,
            }
        ).action_register_departure()
        self.contract.employee_id.toggle_active()
        report = self.env["hr.idse.baja.report"]
        options = self._generate_options(
            report, fields.Date.from_string("2022-01-01"), fields.Date.from_string("2022-12-31")
        )
        data = report.get_txt(options)
        self.assertEqual(
            data.replace("\n", ""),
            "1203256    12345678923OLIVIA                     MARTINEZ SAGAZ             MARIA                      "
            "000000000000000{date}     02     {id}        1                  9".format(
                date=fields.datetime.strftime(self.contract.employee_id.departure_date, "%d%m%Y"),
                id=self.contract.employee_id.id,
            ),
            "Error with IDSE generation",
        )

    def _test_003_wage(self):
        """Generated TXT for wage"""
        report = self.env["hr.idse.wage.report"]
        options = self._generate_options(
            report, fields.Date.from_string("2022-01-01"), fields.Date.from_string("2022-12-31")
        )
        data = report.get_txt(options)
        messages = self.contract.message_ids.filtered(lambda m: m.message_type == "notification")
        tracking = messages.sudo().mapped("tracking_value_ids").filtered(lambda t: t.field.name == "l10n_mx_edi_sbc")
        self.assertEqual(
            data.replace("\n", ""),
            "1203256    12345678923OLIVIA                     MARTINEZ SAGAZ             MARIA                      "
            "076648      100{date}     07     {id}          PUXB571021HNELXR009".format(
                date=fields.datetime.strftime(tracking.sorted("create_date").create_date.date(), "%d%m%Y"),
                id=self.contract.employee_id.id,
            ),
            "Error with IDSE generation",
        )
