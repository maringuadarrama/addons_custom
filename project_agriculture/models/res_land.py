from odoo import fields, models


class Land(models.Model):
    _name = "res.land"

    name = fields.Char(index=True, default_export_compatible=True)
    parent_id = fields.Many2one("res.land", string="Related Land", index=True)
    child_ids = fields.One2many(
        "res.land", "parent_id", string="Land", domain=[("active", "=", True)]
    )  # force "active_test" domain to bypass _search() override
    category_id = fields.Many2many("res.land.category", column1="land_id", column2="category_id", string="Tags")

    surface = fields.Float("Surface", digits="Surface")

    partner_id = fields.Many2one("res.partner", string="Related Company", index=True)
    ref = fields.Char(string="Reference", index=True)
    state_id = fields.Many2one(
        "res.country.state", string="State", ondelete="restrict", domain='[("country_id", "=?", country_id)]'
    )
    country_id = fields.Many2one("res.country", string="Country", ondelete="restrict")
    company_id = fields.Many2one("res.company", "Company", index=True)
    barcode = fields.Char(help="Use a barcode to identify this contact.", copy=False, company_dependent=True)
