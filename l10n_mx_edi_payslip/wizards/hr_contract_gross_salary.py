from odoo import api, fields, models


class HrContractGrossSalary(models.TransientModel):
    _name = "hr.contract.gross.salary"
    _description = "Get Gross Salary based on Net Salary"

    net_salary = fields.Monetary(
        required=True,
        help="Base amount to get the gross salary.",
    )
    lower_limit = fields.Monetary(
        compute="_compute_gross_salary",
        help="It is the minimum value that exists when placing the income in the range of the ISR table for each "
        "period.",
    )
    excess_lower_limit = fields.Monetary(
        compute="_compute_gross_salary",
        help="Excess value, which results from subtracting the minimum value of the range of the ISR table from the "
        "taxable base of the period.",
    )
    percentage = fields.Float(
        "% over the lower limit excess",
        compute="_compute_gross_salary",
        help="% that will be applied to the value exceeding the lower limit.",
    )
    marginal_tax = fields.Monetary(
        compute="_compute_gross_salary",
        help="Resulting tax when applying the corresponding rate.",
    )
    fixed_tax_rate = fields.Monetary(
        compute="_compute_gross_salary",
        help="Amount that must be added to the marginal tax, which is considered in the ISR table.",
    )
    isr = fields.Monetary(
        "ISR",
        compute="_compute_gross_salary",
        help="Amount for ISR",
    )
    gross_salary = fields.Monetary(
        compute="_compute_gross_salary",
        help="Amount to be set like wage in the contract.",
    )
    include_imss = fields.Boolean(
        help="If True, will to get the gross salary considering the IMSS amount.",
    )
    imss = fields.Monetary(
        compute="_compute_gross_salary",
        help="Amount to paid for the employee social security.",
    )
    company_id = fields.Many2one(
        "res.company",
        compute="_compute_company_id",
        help="Contract company",
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        help="Currency in company",
    )
    include_subsidy = fields.Boolean(
        help="If True, will to get the gross salary considering the subsidy amount.",
    )
    subsidy = fields.Monetary(
        compute="_compute_gross_salary",
        help="Amount to paid for the employee subsidy.",
    )

    def _compute_company_id(self):
        self.company_id = self.env["hr.contract"].browse(self._context.get("active_ids", [])).company_id

    @api.depends("net_salary", "include_imss", "include_subsidy")
    def _compute_gross_salary(self):
        imss = subsidy = 0
        if self.include_subsidy:
            subsidy = self.get_subsidy_amount(self.net_salary)
        lower_limit, excess_lower_limit, percentage, marginal_tax, fixed_tax_rate, isr = self.get_isr_amount(subsidy)
        if self.include_imss:
            imss = self.get_imss_amount(self.net_salary + isr - subsidy)
            lower_limit, excess_lower_limit, percentage, marginal_tax, fixed_tax_rate, isr = self.get_isr_amount(
                imss - subsidy
            )
        gross = round(isr + self.net_salary + imss - subsidy, 2)
        last_gross = 0
        while (
            self.net_salary
            and (self.include_subsidy or self.include_imss)
            and self._get_isr(gross)[-1]
            + (self.get_imss_amount(gross) if imss else 0)
            - subsidy
            + self.net_salary
            - gross
            and gross != last_gross
        ):
            last_gross = gross
            if self.include_subsidy:
                subsidy = self.get_subsidy_amount(gross)
            if self.include_imss:
                imss = self.get_imss_amount(gross)
            lower_limit, excess_lower_limit, percentage, marginal_tax, fixed_tax_rate, isr = self.get_isr_amount(
                imss - subsidy
            )
            gross = round(isr + self.net_salary + imss - subsidy, 2)
        self.imss = imss
        self.subsidy = subsidy
        self.lower_limit = lower_limit
        self.excess_lower_limit = excess_lower_limit
        self.percentage = percentage * 100
        self.marginal_tax = marginal_tax
        self.fixed_tax_rate = fixed_tax_rate
        self.isr = isr
        self.gross_salary = gross

    def _get_isr(self, amount):
        """Get monthly ISR corresponding to the amount given."""
        table = [
            (0.01, 746.04, 0.00, 0.0192),
            (746.05, 6332.05, 14.32, 0.0640),
            (6332.06, 11128.01, 371.83, 0.1088),
            (11128.02, 12935.82, 893.63, 0.1600),
            (12935.83, 15487.71, 1182.88, 0.1792),
            (15487.72, 31236.49, 1640.18, 0.2136),
            (31236.50, 49233.00, 5004.12, 0.2352),
            (49233.01, 93993.90, 9236.89, 0.3000),
            (93993.91, 125325.20, 22665.17, 0.3200),
            (125325.21, 375975.61, 32691.18, 0.3400),
            (375975.62, 999999999, 117912.32, 0.3500),
        ]
        lower_limit = excess_lower_limit = percentage = marginal_tax = fixed_tax_rate = isr = higher_limit = 0
        for value in table:
            if value[1] >= amount >= value[0]:
                lower_limit = value[0]
                percentage = value[3]
                fixed_tax_rate = value[2]
                higher_limit = value[1]
                excess_lower_limit = amount - lower_limit
                marginal_tax = excess_lower_limit * percentage
                isr = round(marginal_tax + fixed_tax_rate, 2)
        return lower_limit, excess_lower_limit, higher_limit, percentage, marginal_tax, fixed_tax_rate, isr

    def get_isr_amount(self, extra=None):
        """Based on ISR rule, get the ISR amount (Recursive to get the correct value)"""
        base_amount = self.net_salary + (extra or 0)
        amount = base_amount
        lower_limit, excess_lower_limit, higher_limit, percentage, marginal_tax, fixed_tax_rate, isr = self._get_isr(
            amount
        )
        higher = higher_limit
        less = base_amount
        if base_amount + isr > higher:
            (
                lower_limit,
                excess_lower_limit,
                higher_limit,
                percentage,
                marginal_tax,
                fixed_tax_rate,
                isr,
            ) = self._get_isr(  # noqa
                base_amount + isr
            )
            higher = higher_limit
        last_amount = 0
        while round(amount - isr, 2) != base_amount and last_amount != round(amount - isr, 2):
            last_amount = round(amount - isr, 2)
            amount = (higher + less) / 2
            (
                lower_limit,
                excess_lower_limit,
                higher_limit,
                percentage,
                marginal_tax,
                fixed_tax_rate,
                isr,
            ) = self._get_isr(  # noqa
                amount
            )
            if base_amount <= amount - isr <= higher:
                higher = amount
            elif base_amount >= amount - isr <= less:
                less = amount
        return lower_limit, excess_lower_limit, percentage, marginal_tax, fixed_tax_rate, isr

    def get_imss_amount(self, wage):
        """Get IMSS amount if is activated the option (Comes from IMSS Rule)"""
        contract = self.env["hr.contract"].browse(self._context.get("active_ids", []))
        sbc = contract._get_integrated_salary(wage)[1]
        uma = contract.company_id.l10n_mx_edi_uma
        days_work = 31
        specie_excess = ((sbc - (uma * 3)) * 0.004 * days_work) if (sbc - (uma * 3)) > 0 else 0
        benefits = 0.0025 * sbc * days_work
        pensioners = 0.00375 * sbc * days_work
        disability = 0.00625 * sbc * days_work
        unemployment = 0.01125 * sbc * days_work
        return round(specie_excess + benefits + pensioners + disability + unemployment, 2)

    def get_subsidy_amount(self, wage):
        """Get subsidy amount if is activated the option (Comes from subsidy rule)"""
        table = [
            (0.01, 1768.96, 407.02),
            (1768.97, 2653.38, 406.83),
            (2653.39, 3472.84, 406.62),
            (3472.85, 3537.87, 392.77),
            (3537.88, 4446.15, 382.46),
            (4446.16, 4717.18, 354.23),
            (4717.19, 5335.42, 324.87),
            (5335.43, 6224.67, 294.63),
            (6224.68, 7113.90, 253.54),
            (7113.91, 7382.33, 217.61),
            (7382.34, 99999999.00, 0),
        ]
        for value in table:
            if value[0] <= wage <= value[1]:
                return round(value[2], 2)
        return 0

    def set_wage(self):
        """Assign the calculated amount in the contract"""
        self.env["hr.contract"].browse(self._context.get("active_ids", [])).write({"wage": self.gross_salary})
