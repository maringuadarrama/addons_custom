from itertools import groupby

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import first
from odoo.tools import float_compare


class StockMoveLocationWizard(models.TransientModel):
    _name = "wiz.stock.move.location"
    _description = "Wizard move location"

    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    picking_type_id = fields.Many2one(
        "stock.picking.type",
        domain="[('company_id', '=', company_id), ('sequence_code', 'in', ('INT', 'INTER', 'INTRA'))]",
    )
    edit_locations = fields.Boolean("Edit locations", default=False)
    apply_putaway_strategy = fields.Boolean("Apply putaway strategy", default=False)
    origin_location_id = fields.Many2one(
        "stock.location", "Origin Location", domain="[('company_id', 'in', (False, company_id))]"
    )
    destination_location_id = fields.Many2one(
        "stock.location", "Destination Location", domain="[('company_id', 'in', (False, company_id))]"
    )
    origin_location_readonly = fields.Boolean(
        compute="_compute_location_readonly", help="technical field to disable the edition of origin location."
    )
    destination_location_readonly = fields.Boolean(
        compute="_compute_location_readonly", help="technical field to disable the edition of destination location."
    )
    line_ids = fields.One2many("wiz.stock.move.location.line", "wizard_id", "Lines")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get("active_model", False) != "stock.quant":
            return res
        quant_ids = self.env["stock.quant"].browse(self.env.context.get("active_ids", False))
        res["line_ids"] = self._create_default_line_ids(quant_ids)
        res["origin_location_id"] = first(quant_ids).location_id.id
        res["picking_type_id"] = first(quant_ids).location_id.warehouse_id.int_type_id.id
        return res

    @api.model
    def _create_default_line_ids(self, quant_ids):
        res = []
        if not self.env.context.get("only_reserved_qty", False):
            res = [
                (
                    0,
                    0,
                    {
                        "product_id": quant.product_id.id,
                        "move_quantity": quant.quantity,
                        "max_quantity": quant.quantity,
                        "lot_id": quant.lot_id.id,
                        "product_uom_id": quant.product_uom_id.id,
                        "custom": False,
                    },
                )
                for quant in quant_ids
            ]
        else:
            for _product, quant in groupby(quant_ids, lambda r: r.product_id):
                # we need only one quant per product
                quant = list(quant)[0]
                qty = quant._get_available_quantity(quant.product_id, quant.location_id)
                if qty:
                    res.append(
                        (
                            0,
                            0,
                            {
                                "product_id": quant.product_id.id,
                                "move_quantity": qty,
                                "max_quantity": qty,
                                "lot_id": quant.lot_id.id,
                                "product_uom_id": quant.product_uom_id.id,
                                "custom": False,
                            },
                        )
                    )
        return res

    @api.depends("edit_locations")
    def _compute_location_readonly(self):
        for wiz in self:
            wiz.origin_location_readonly = self.env.context.get("origin_location_readonly", False)
            wiz.destination_location_readonly = self.env.context.get("destination_location_readonly", False)
            if not wiz.edit_locations:
                wiz.origin_location_readonly = True
                wiz.destination_location_readonly = True

    def _prepare_group_quants(self, location):
        # Using sql as search_group doesn't support aggregation functions
        # leading to overhead in queries to DB
        query = """
            SELECT product_id, lot_id, SUM(quantity) AS quantity,
                SUM(reserved_quantity) AS reserved_quantity
            FROM stock_quant
            WHERE location_id = %s
            GROUP BY product_id, lot_id
            HAVING SUM(quantity) > 0
        """
        self.env.cr.execute(query, (location.id,))
        return self.env.cr.dictfetchall()

    def _prepare_line_ids(self, location):
        product_obj = self.env["product.product"]
        product_data = []
        for group in self._prepare_group_quants(location):
            product = product_obj.browse(group.get("product_id")).exists()
            product_data.append(
                {
                    "product_id": product.id,
                    "move_quantity": group.get("quantity") or 0,
                    "max_quantity": group.get("quantity") or 0,
                    "reserved_quantity": group.get("reserved_quantity"),
                    "lot_id": group.get("lot_id") or False,
                    "product_uom_id": product.uom_id.id,
                    "custom": False,
                }
            )
        return product_data

    @api.onchange("picking_type_id")
    def _onchange_picking_type_id(self):
        if self.picking_type_id:
            self.origin_location_id = (
                self.picking_type_id.default_location_src_id
                if not self.origin_location_id
                else self.origin_location_id
            )
            self.destination_location_id = (
                self.picking_type_id.default_location_dest_id
                if not self.destination_location_id
                else self.destination_location_id
            )

    @api.onchange("origin_location_id")
    def onchange_origin_location(self):
        self.line_ids.unlink()
        # Get origin_location_readonly context key to prevent load all origin
        # location products when user opens the wizard from stock quants to
        # move it to other location.
        if not self.env.context.get("origin_location_readonly") and self.origin_location_id:
            lines = []
            line_obj = self.env["wiz.stock.move.location.line"]
            for line_val in self._prepare_line_ids(self.origin_location_id):
                line = line_obj.create(line_val)
                lines.append(line)
            self.update({"line_ids": [Command.set([line.id for line in lines])]})

    def group_lines(self, lines):
        lines_grouped = {}
        for line in lines:
            lines_grouped.setdefault(line.product_id.id, self.env["wiz.stock.move.location.line"].browse())
            lines_grouped[line.product_id.id] |= line
        return lines_grouped

    def _prepare_sm_vals(self, lines, flag=False):
        product = lines[0].product_id
        product_uom_id = lines[0].product_uom_id.id
        qty = sum(x.move_quantity for x in lines)
        location_dest_id = (
            self.apply_putaway_strategy
            and self.destination_location_id._get_putaway_strategy(product).id
            or self.destination_location_id.id
        )
        return {
            "location_id": self.origin_location_id.id,
            "location_dest_id": location_dest_id,
            "product_id": product.id,
            "product_uom": product_uom_id,
            "product_uom_qty": qty,
            "name": product.display_name,
        }

    def _create_moves(self, picking, lines):
        self.ensure_one()
        groups = self.group_lines(lines)
        for group_lines in groups.values():
            sm_vals = self._prepare_sm_vals(group_lines)
            sm_vals.update({"picking_id": picking.id})
            move = self.env["stock.move"].create(sm_vals)
            if not self.env.context.get("planned"):
                for line in group_lines:
                    _qty_todo, qty_done = line.get_available_quantity()
                    self.env["stock.move.line"].create(
                        {
                            "picking_id": picking.id,
                            "move_id": move.id,
                            "location_id": sm_vals["location_id"],
                            "location_dest_id": sm_vals["location_dest_id"],
                            "product_id": line.product_id.id,
                            "lot_id": line.lot_id.id,
                            "product_uom_id": line.product_uom_id.id,
                            "qty_done": qty_done,
                        }
                    )

    def _unreserve_moves(self):
        moves_to_reassign = self.env["stock.move"]
        lines_to_ckeck_reverve = self.line_ids.filtered(
            lambda ln: (
                ln.move_quantity > ln.max_quantity - ln.reserved_quantity
                and not self.origin_location_id.should_bypass_reservation()
            )
        )
        for line in lines_to_ckeck_reverve:
            move_lines = self.env["stock.move.line"].search(
                [
                    ("state", "=", "assigned"),
                    ("product_id", "=", line.product_id.id),
                    ("location_id", "=", self.origin_location_id.id),
                    ("lot_id", "=", line.lot_id.id),
                    ("qty_done", ">", 0.0),
                ]
            )
            moves_to_unreserve = move_lines.mapped("move_id")
            # Unreserve in old location
            moves_to_unreserve._do_unreserve()
            moves_to_reassign |= moves_to_unreserve
        return moves_to_reassign

    def _action_picking(self, picking_id):
        view = self.env.ref("stock.view_picking_form")
        return {
            "name": _("Picking"),
            "view_mode": "form",
            "res_model": "stock.picking",
            "view_id": view.id,
            "views": [(view.id, "form")],
            "type": "ir.actions.act_window",
            "res_id": picking_id,
        }

    def action_move_location(self):
        self.ensure_one()
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_id.id,
                "location_id": self.origin_location_id.id,
                "location_dest_id": self.destination_location_id.id,
            }
        )
        self._create_moves(picking, self.line_ids)
        if self.env.context.get("planned"):
            picking.action_confirm()
            picking.action_assign()
        else:
            self._unreserve_moves()
            picking.action_confirm()
            picking.button_validate()
            # moves_to_reassign._action_assign()
        return self._action_picking(picking.id)


class StockMoveLocationWizardLine(models.TransientModel):
    _name = "wiz.stock.move.location.line"
    _description = "Wizard move location line"

    wizard_id = fields.Many2one("wiz.stock.move.location")
    company_id = fields.Many2one("res.company", related="wizard_id.company_id", store=True, readonly=True)
    product_id = fields.Many2one("product.product", "Product", required=True)
    product_uom_id = fields.Many2one(
        "uom.uom", "Unit of Measure", compute="_compute_product_uom", store=True, readonly=False, precompute=True
    )
    lot_id = fields.Many2one(
        "stock.lot", "Lot/Serial Number", domain="[('company_id', '=', company_id), ('product_id', '=', product_id)]"
    )
    move_quantity = fields.Float(string="Quantity to move", digits="Product Unit of Measure")
    reserved_quantity = fields.Float("Reserved quantity", digits="Product Unit of Measure")
    max_quantity = fields.Float("Maximum available quantity", digits="Product Unit of Measure")
    custom = fields.Boolean(string="Custom line", default=True)

    @api.constrains("max_quantity", "move_quantity")
    def _constraint_max_move_quantity(self):
        for record in self:
            rounding = record.product_uom_id.rounding
            move_qty_gt_max_qty = float_compare(record.move_quantity, record.max_quantity, rounding) == 1
            move_qty_lt_0 = float_compare(record.move_quantity, 0.0, rounding) == -1
            if move_qty_gt_max_qty:
                raise ValidationError(_("Move quantity can not exceed max quantity"))
            if move_qty_lt_0:
                raise ValidationError(_("Move quantity can not be negative"))

    @api.depends("product_id")
    def _compute_product_uom(self):
        for line in self:
            if not line.product_uom_id or (line.product_id.uom_id.id != line.product_uom_id.id):
                line.product_uom_id = line.product_id.uom_id

    def get_max_qty(self):
        search_args = [
            ("location_id", "=", self.wizard_id.origin_location_id.id),
            ("product_id", "=", self.product_id.id),
        ]
        if self.lot_id:
            search_args.append(("lot_id", "=", self.lot_id.id))
        else:
            search_args.append(("lot_id", "=", False))
        res = self.env["stock.quant"].read_group(search_args, ["quantity"], [])
        return res[0]["quantity"]

    def get_available_quantity(self):
        """We check here if the actual amount changed in the stock.
        We don't care about the reservations but we do care about not moving
        more than exists."""
        self.ensure_one()
        if self.env.context.get("planned"):
            return self.move_quantity, 0
        available_qty = self.get_max_qty()
        if not available_qty:
            # if it is immediate transfer and product doesn't exist in that
            # location -> make the transfer of 0.
            return 0
        rounding = self.product_uom_id.rounding
        available_qty_lt_move_qty = float_compare(available_qty, self.move_quantity, rounding) == -1
        if available_qty_lt_move_qty:
            return available_qty
        return 0, self.move_quantity
