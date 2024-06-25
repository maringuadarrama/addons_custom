from odoo import fields, models


class AgricultureSpeciesStage(models.Model):
    _name = "project.agriculture.species.stage"

    name = fields.Char()
    sequence = fields.Integer(default=100)
    active = fields.Boolean("Active", default=True)
    species_ids = fields.Many2many(
        "project.agriculture.species",
        "project_agriculture_species_stage_rel",
        string="Species",
        help="Projects in which this stage is present. If you follow a similar workflow in several projects, "
        "you can share this stage among them and get consolidated information this way.",
    )


class AgricultureSpecies(models.Model):
    _name = "project.agriculture.species"

    name = fields.Char("Name", required=True)
    scientific_name = fields.Char("Species")
    type = fields.Selection(
        [
            ("crop", "Crop"),
            ("livestock", "Livestock"),
            ("pdw", "Pest, disease, weed"),
            ("subspecies", "Subspecies"),
        ],
        "Species type",
        required=True,
        default="crop",
    )
    # detailed_type = fields.Selection([
    #    ("", "Consumable"),
    #    ("service", "Service")],
    #    string="Product Type", default="consu", required=True,
    #    help="A storable product is a product for which you manage stock. The Inventory app has to be installed.\n"
    #         "A consumable product is a product for which stock is not managed.\n"
    #         "A service is a non-material product you provide.")
    species_id = fields.Many2one("project.agriculture.species", string="Species")
    is_subspecies = fields.Boolean(compute="si tiene species_id entonces es subspecie")

    # General agronomical traits
    stage_ids = fields.Many2many(
        "project.agriculture.species.stage", "project_agriculture_species_stage_rel", string="Stages"
    )
    maturity = fields.Integer(
        "Maturity (days)",
        help="Depending on if the species is a variety or a pdw, set the "
        "minimum amount of days with ideal conditions in which a full"
        "cycle can be achieved. "
        "This information will be later used to asses pdw risk or crop plans",
    )
    productivity_uom_id = fields.Many2one(
        "uom.uom",
        "Productivity UoM",
        domain="[('category_id', '=', product_uom_category_id)]",
        ondelete="restrict",
    )
    productivity = fields.Integer(
        "Productivity",
        help="Depending on if the species is a variety, set the "
        "maximum amount of productivity that can be achieved. "
        "This information will be later used to asses pdw risk or crop plans",
    )

    # Potato traits
    skin_color = fields.Char("Skin color", translate=True)
    meat_color = fields.Char("Meat color", translate=True)
    chip = fields.Boolean("Chip")
    mashed = fields.Boolean("Mashed")

    # pdw traits
    pdw_ids = fields.Many2many(
        "project.agriculture.species",
        "project_agriculture_species_species_pdw_rel",
        "species_id",
        "pdw_id",
        string="Pest, disease, weed",
    )
    chemical_control_ids = fields.Many2many(
        "project.agriculture.chemical.control",
        "project_agriculture_species_pdw_chem_control_rel",
        string="Chemical control AI",
    )
    is_quarantine = fields.Boolean()
    damage_root = fields.Boolean()
    damage_foliage = fields.Boolean()
    damage_product = fields.Boolean()
    damage_quality = fields.Boolean()
    severity = fields.Integer(default=5, help="On scale of 1 to 5 1 being almost none and 5 being extreme damage")


class AgricultureChemicalControl(models.Model):
    _name = "project.agriculture.chemical.control"

    species_id = fields.Many2one(
        "project.agriculture.species",
        "Pest, Disease or Weed",
        required=True,
        readonly=True,
        index=True,
        auto_join=True,
        ondelete="cascade",
    )
    active_ingredient = fields.Char(
        "Active ingredient",
    )
    protectant_effectiveness = fields.Integer(
        "Protectant efectiveness", help="Values between 1(less effective) and 5(very effective) "
    )
    curative_effectiveness = fields.Integer(
        "Curative efectiveness", help="Values between 1(less effective) and 5(very effective) "
    )
    rainfastness = fields.Integer("Rainfastness", help="Values between 1(less effective) and 5(very effective) ")
    sistemicity = fields.Selection(
        selection=[
            ("contact", "Contact"),
            ("translaminar", "Translaminar"),
            ("acropetal", "Acropetal"),
            ("dual", "Dual"),
        ],
        string="Productivity",
        default="normal",
    )
