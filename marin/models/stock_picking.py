# Copyright 2019 ForgeFlow S.L.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    show_purchase_lines = fields.Boolean(compute="_compute_show_purchase_lines")
    show_sale_lines = fields.Boolean(compute="_compute_show_sale_lines")
    waiting_warning = fields.Text(compute="_compute_waiting_warning")

    @api.depends("group_id")
    def _compute_show_purchase_lines(self):
        for rec in self:
            order = rec.env["purchase.order"].search([("group_id", "=", rec.group_id.id)])
            to_from_supplier = rec.location_id.usage == "supplier" or rec.location_dest_id.usage == "supplier"
            rec.show_purchase_lines = bool(order and to_from_supplier)

    @api.depends("sale_id")
    def _compute_show_sale_lines(self):
        for rec in self:
            to_from_customer = rec.location_dest_id.usage == "customer" or rec.location_id.usage == "customer"
            rec.show_sale_lines = bool(rec.sale_id and to_from_customer)

    def action_view_purchase_order(self):
        self.ensure_one()
        # Remove default_picking_id to avoid defaults get
        # https://github.com/odoo/odoo/blob/master/addons/stock/models/stock_move.py#L624
        ctx = self.env.context.copy()
        ctx.pop("default_picking_id", False)
        return self.with_context(ctx).purchase_id.get_formview_action()

    def action_view_sale_order(self):
        self.ensure_one()
        # Remove default_picking_id to avoid defaults get
        # https://github.com/odoo/odoo/blob/master/addons/stock/models/stock_move.py#L624
        ctx = self.env.context.copy()
        ctx.pop("default_picking_id", False)
        return self.with_context(ctx).sale_id.get_formview_action()

    # backport V17
    def action_reset_draft(self):
        picking_to_reset = self.filtered(lambda p: p.state == "cancel")
        picking_to_reset.do_unreserve()
        picking_to_reset.move_ids.state = "draft"
        picking_to_reset.move_ids.quantity = 0
        picking_to_reset.move_ids.move_line_ids.unlink()

    def _validate_picking(self):
        if self.location_id.child_ids:
            raise UserError(_("Please choose a source end location"))
        if self.move_ids:
            raise UserError(_("Moves lines already exists"))

    def _get_movable_quants(self):
        return self.env["stock.quant"].search([("location_id", "=", self.location_id.id), ("quantity", ">", 0.0)])

    def button_fillwithstock(self):
        # check source location has no children, i.e. we scanned a bin
        self.ensure_one()
        self._validate_picking()
        context = {
            "active_ids": self._get_movable_quants().ids,
            "active_model": "stock.quant",
            "only_reserved_qty": True,
            "planned": True,
        }
        move_wizard = (
            self.env["wiz.stock.move.location"]
            .with_context(**context)
            .create(
                {
                    "destination_location_id": self.location_dest_id.id,
                    "origin_location_id": self.location_id.id,
                    "picking_type_id": self.picking_type_id.id,
                }
            )
        )
        move_wizard.action_move_location()
        return True

    def action_view_moves(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("stock.stock_move_action")
        action["domain"] = [("id", "in", self.move_ids.ids)]
        action["context"] = {
            "search_default_future": 1,
            "search_default_by_product": 1,
            "search_default_groupby_picking_type_id": 1,
            "pivot_measures": ["product_uom_qty", "__count__"],
        }
        return action

    def _validate_deliveryslip(self):
        invalid_pickings = self.filtered(lambda pick: pick.state != "done")
        if invalid_pickings:
            picking_names = "\n".join(picking.name for picking in invalid_pickings)
            raise UserError(_("Following pickings are not valid to print their delivery slip: \n%s", picking_names))
        return True

    @api.model
    def _print_deliveryslip(self):
        self._validate_deliveryslip()
        return self.env.ref("stock.action_report_delivery").report_action(self)

    def _validate_picking_operation(self):
        invalid_pickings = self.filtered(
            lambda pick: pick.state != "assigned"
            and not (
                pick.state == "confirmed"
                and pick.move_ids.filtered(lambda sm: sm.state in ["partially_available", "assigned"])
            )
        )
        if invalid_pickings:
            picking_names = "\n".join(picking.name for picking in invalid_pickings)
            raise UserError(
                _("Following pickings are not valid to print their picking operation: \n%s", picking_names)
            )
        return True

    @api.model
    def _print_picking_operation(self):
        self._validate_picking_operation()
        return self.env.ref("stock.action_report_picking").report_action(self)

    @api.depends("state")
    def _compute_waiting_warning(self):
        for picking in self:
            picking.waiting_warning = (
                _(
                    "All products could not be reserved. Click on the 'Check Availability' button to try to "
                    "reserve products."
                )
                if picking.state == "confirmed"
                else ""
            )
