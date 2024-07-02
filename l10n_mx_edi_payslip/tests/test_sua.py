import time

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests.common import tagged

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged("hr_employee_sua", "post_install", "-at_install")
class TestHrSuaReport(TestAccountReportsCommon):
    def setUp(self):
        super().setUp()
        self.contract = self.env.ref("l10n_mx_edi_payslip.hr_contract_maria")
        self.contract.state = "open"

    def test_001_insured(self):
        """Generated TXT for insured"""
        report = self.env["hr.sua.report"]
        options = self._generate_options(
            report, fields.Date.from_string("2022-01-01"), fields.Date.from_string("2022-12-31")
        )
        data = report.get_txt(options)
        self.assertEqual(
            data.replace("\n", ""),
            "1203256    12345678923MASO451221PM4PUXB571021HNELXR00OLIVIA$MARTINEZ SAGAZ$MARIA                       "
            "10{date}007664812345            CREDIT 123{date}100000180".format(
                date=fields.datetime.strftime(self.contract.date_start, "%d%m%Y")
            ),
            "Error with SUA generation",
        )

    def test_002_affiliation(self):
        """Generated TXT for affiliation"""
        report = self.env["hr.sua.affiliation.report"]
        options = self._generate_options(
            report, fields.Date.from_string("2022-01-01"), fields.Date.from_string("2022-12-31")
        )
        data = report.get_txt(options)
        self.assertEqual(
            data.replace("\n", ""),
            "1203256    1234567892380290                                 11T21EXPERIENCED F0",
            "Error with SUA generation",
        )

    def _test_003_mov(self):
        """Generated TXT for movements"""
        sick_leave = self.env.ref("hr_holidays.hr_holidays_sl_qdp")
        sick_leave.holiday_status_id.l10n_mx_edi_payslip_use_calendar_days = True
        sick_leave._compute_number_of_days()
        leave = self.env["hr.leave"].create(
            {
                "holiday_type": "employee",
                "employee_id": self.contract.employee_id.id,
                "holiday_status_id": self.env.ref("l10n_mx_edi_payslip.mexican_faltas_injustificadas").id,
                "request_date_from": "%s-%s-10" % (time.strftime("%Y"), time.strftime("%m")),
                "request_date_to": "%s-%s-13" % (time.strftime("%Y"), time.strftime("%m")),
                "number_of_days": 1,
                "date_from": "%s-%s-10" % (time.strftime("%Y"), time.strftime("%m")),
                "date_to": "%s-%s-13" % (time.strftime("%Y"), time.strftime("%m")),
            }
        )
        leave._compute_date_from_to()
        leave.action_approve()
        report = self.env["hr.sua.mov.report"]
        options = self._generate_options(
            report, fields.Date.from_string("2022-01-01"), fields.Date.from_string("2022-12-31")
        )
        data = report.get_txt(options)
        messages = self.contract.message_ids.filtered(lambda m: m.message_type == "notification")
        tracking = messages.sudo().mapped("tracking_value_ids").filtered(lambda t: t.field.name == "l10n_mx_edi_sbc")
        self.assertEqual(
            data,
            "1203256    1234567892307{date}        000076648\n"
            "1203256    1234567892311{date2}        0{days}0076648\n"
            "1203256    1234567892312{date3}SICK DAY030076648\n".format(
                date=fields.datetime.strftime(tracking.sorted("create_date").create_date.date(), "%d%m%Y"),
                date2="10%s%s" % (time.strftime("%m"), time.strftime("%Y")),
                date3=fields.datetime.strftime(self.contract.date_start + relativedelta(day=1, weekday=0), "%d%m%Y"),
                days=int(leave.number_of_days),
            ),
            "Error with SUA generation",
        )
