from odoo.tests.common import TransactionCase


class TestStockMoveLocation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "Product A",
                "type": "product",
            }
        )
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.stock_subloc1 = cls.env["stock.location"].create(
            {"name": "subloc1", "usage": "internal", "location_id": cls.stock_location.id}
        )
        cls.stock_subloc2 = cls.env["stock.location"].create(
            {
                "name": "subloc2",
                "usage": "internal",
                "location_id": cls.stock_location.id,
            }
        )
        cls.quant = cls.env["stock.quant"].create(
            {
                "product_id": cls.product.id,
                "location_id": cls.stock_subloc1.id,
                "quantity": 5.0,
            }
        )
        cls.quant2 = cls.env["stock.quant"].create(
            {
                "product_id": cls.product.id,
                "location_id": cls.stock_subloc1.id,
                "quantity": 10.0,
            }
        )
        cls.quant3 = cls.env["stock.quant"].create(
            {
                "product_id": cls.product.id,
                "location_id": cls.stock_subloc1.id,
                "quantity": 20.0,
            }
        )

    def test_01_wizard_move_location(self):
        context = {
            "active_ids": (self.quant | self.quant2).ids,
            "active_model": "stock.quant",
            "only_reserved_qty": True,
            "planned": True,
        }
        move_wizard = (
            self.env["wiz.stock.move.location"]
            .with_context(**context)
            .create(
                {
                    "destination_location_id": self.stock_subloc2.id,
                    "origin_location_id": self.stock_subloc1.id,
                    "picking_type_id": self.env.ref("stock.picking_type_internal").id,
                }
            )
        )
        move_wizard._compute_location_readonly()
        move_wizard.onchange_origin_location()
        move_wizard._onchange_picking_type_id()
        move_wizard.line_ids._compute_product_uom()
        move_wizard.line_ids[0].get_available_quantity()
        move_wizard.action_move_location()

    def test_02_wizard_move_location_not_planned(self):
        context = {
            "active_ids": (self.quant | self.quant2).ids,
            "active_model": "stock.quant",
            "only_reserved_qty": False,
            "planned": False,
        }
        move_wizard = (
            self.env["wiz.stock.move.location"]
            .with_context(**context)
            .create(
                {
                    "destination_location_id": self.stock_subloc2.id,
                    "origin_location_id": self.stock_subloc1.id,
                    "picking_type_id": self.env.ref("stock.picking_type_internal").id,
                }
            )
        )
        move_wizard._compute_location_readonly()
        move_wizard.action_move_location()

    def test_03_wizard_move_location_not_quant(self):
        self.env["wiz.stock.move.location"].create(
            {
                "destination_location_id": self.stock_subloc2.id,
                "origin_location_id": self.stock_subloc1.id,
                "picking_type_id": self.env.ref("stock.picking_type_internal").id,
            }
        )
