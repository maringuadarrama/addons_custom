from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class StockPickingTypeInherit(models.Model):
    _inherit = "stock.picking.type"

    # This is a bug fix
    @api.constrains("active")
    def _check_active(self):
        for picking_type in self:
            pos_config = self.env["pos.config"].search([("picking_type_id", "=", picking_type.id)], limit=1)
            if not picking_type.active and pos_config:
                raise ValidationError(
                    _(
                        "You cannot archive '%s' as it is used by a POS configuration '%s'.",
                        picking_type.name,
                        pos_config.name,
                    )
                )

    # Add search
    count_picking_ready = fields.Integer(search="_search_count_picking_ready")
    count_picking_waiting = fields.Integer(search="_search_count_picking_waiting")
    allowed_user_ids = fields.Many2many(
        "res.users",
        "stock_picking_type_res_users_rel",
        "picking_type_id",
        "user_id",
        "Allowed Users",
        help="Users that can visualize and perform pickings with this type of operation.",
    )
    show_move_onhand = fields.Boolean(
        "Show Move On hand stock",
        help="Show a button 'Move On Hand' in the Inventory Dashboard "
        "to initiate the process to move the products in stock "
        "at the origin location.",
    )
    pos_avoid_locations = fields.Many2many("stock.location")
    route_ids = fields.Many2many(
        "stock.route",
        "stock_route_picking_type",
        "picking_type_id",
        "route_id",
        "Default destination route",
        help="Default route to be used.",
    )

    def _search_count_picking_ready(self, operator, value):
        if operator not in ["=", "!="] or not isinstance(value, bool):
            raise UserError(_("Operation not supported"))
        picking_type_ids = []
        pickings_groupby = self.env["stock.picking"].read_group(
            [("state", "=", "assigned")], ["picking_type_id"], ["picking_type_id"]
        )
        for picking_type in pickings_groupby:
            picking_type_ids.append(picking_type["picking_type_id"][0])
        return [("id", "in", picking_type_ids)]

    def _search_count_picking_waiting(self, operator, value):
        if operator not in ["=", "!="] or not isinstance(value, bool):
            raise UserError(_("Operation not supported"))
        picking_type_ids = []
        pickings_groupby = self.env["stock.picking"].read_group(
            [("state", "in", ("confirmed", "waiting"))], ["picking_type_id"], ["picking_type_id"]
        )
        for picking_type in pickings_groupby:
            picking_type_ids.append(picking_type["picking_type_id"][0])
        return [("id", "in", picking_type_ids)]

    def action_move_location(self):
        action = self.env.ref("marin.wiz_stock_move_location_action").read()[0]
        action["context"] = {
            "default_picking_type_id": self.id,
            "default_origin_location_id": self.default_location_src_id.id,
            "default_destination_location_id": self.default_location_dest_id.id,
            "default_edit_locations": False,
        }
        return action
