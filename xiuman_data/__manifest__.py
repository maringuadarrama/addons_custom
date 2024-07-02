{
    "name": "Xiuman data",
    "summary": """
    Instance creator for xiuman. This is the app.
    """,
    "author": "Vauxoo",
    "website": "https://www.vauxoo.com",
    "license": "OPL-1",
    "category": "Installer",
    "version": "17.0.0.0.1",
    "depends": [
        "xiuman",
    ],
    "data": [
        "data/res_company_data.xml",
        "data/crm_team_data.xml",
        "data/hr_department_data.xml",
        "data/hr_job_data.xml",
        "data/hr_payroll_structure_data.xml",
        "data/hr_salary_rule_data.xml",
        "data/hr_salary_rule_christmas_bonus_data.xml",
        "data/hr_salary_rule_nomina_finiquito_data.xml",
        "data/l10n_mx_edi_employer_registration_data.xml",
        "data/website_data.xml",
    ],
    "demo": [],
    # "pre_init_hook": "_pre_init_xiuman",
    # "post_init_hook": "_post_init_xiuman",
    "installable": True,
    "auto_install": False,
    "application": False,
}
