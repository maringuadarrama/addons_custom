from . import models
from . import report
from . import wizards
from odoo import tools

def _pre_init_marin(env):
    env["ir.module.module"].search([("name", "=", "attachment_indexation")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "barcodes")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "base_geolocalize")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "http_routing")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "base_address_extended")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "web_studio")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "data_recycle")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "analytic")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "product")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "calendar")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "loyalty")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "sales_team")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "board")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "survey")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "knowledge")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "room")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "fleet")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "documents")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "hr")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "hr_attendance")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "hr_contract")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "hr_holidays")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "hr_homeworking")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "hr_presence")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "hr_recruitment")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "hr_recruitment_survey")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "hr_appraisal_survey")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "appointment")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "project_forecast")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "product_expiry")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "stock_barcode_picking_batch")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "stock_barcode_mrp_subcontracting")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "mrp_plm")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "quality_mrp")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "product_margin")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "hr_payroll_expense")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "account_consolidation")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "purchase_requisition_stock")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "stock_landed_costs_company")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "account_3way_match")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "delivery")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "sale_purchase_inter_company_rules")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "stock_dropshipping")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "sale_renting")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "crm")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "point_of_sale")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "website_sale_picking")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "website_event_sale")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "website_sale_comparison")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "website_customer")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "website_crm_partner_assign")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "website_blog")]).sudo().button_install()
    env["ir.module.module"].search([("name", "=", "website_slides")]).sudo().button_install()

    env.cr.execute("""SELECT setval('"public"."res_partner_category_id_seq"', 100, true);""")

    env.cr.execute("""SELECT setval('"public"."product_category_id_seq"', 100, true);""")
    env.cr.execute("""SELECT setval('"public"."product_pricelist_id_seq"', 100, true);""")
    env.cr.execute("""SELECT setval('"public"."product_pricelist_item_id_seq"', 1000, true);""")
    env.cr.execute("""SELECT setval('"public"."uom_category_id_seq"', 100, true);""")
    env.cr.execute("""SELECT setval('"public"."uom_uom_id_seq"', 100, true);""")
    tools.convert.convert_file(env, "marin", "data/product.category.csv", None, mode="init", kind="data")
    tools.convert.convert_file(env, "marin", "data/product.tag.csv", None, mode="init", kind="data")
    tools.convert.convert_file(env, "marin", "data/product_pricelist_data.xml", None, mode="init", kind="data")
    tools.convert.convert_file(env, "marin", "data/uom.category.csv", None, mode="init", kind="data")
    tools.convert.convert_file(env, "marin", "data/uom.uom.csv", None, mode="init", kind="data")

    tools.convert.convert_file(env, "marin", "data/fleet.vehicle.model.brand.csv", None, mode="init", kind="data")
    tools.convert.convert_file(env, "marin", "data/fleet.vehicle.model.category.csv", None, mode="init", kind="data")
    tools.convert.convert_file(env, "marin", "data/fleet.vehicle.model.csv", None, mode="init", kind="data")
    tools.convert.convert_file(env, "marin", "data/stock.package.type.csv", None, mode="init", kind="data")
    tools.convert.convert_file(env, "marin", "data/stock.storage.category.csv", None, mode="init", kind="data")

def _post_init_marin(env):
    env.cr.execute("""SELECT setval('"public"."res_partner_id_seq"', 100, true);""")
    tools.convert.convert_file(env, "marin", "data/res_company_data.xml", None, mode="init", kind="data")

    env.cr.execute("""SELECT setval('"public"."resource_calendar_id_seq"', 100, true);""")
    env.cr.execute("""SELECT setval('"public"."resource_calendar_attendance_id_seq"', 1000, true);""")
    tools.convert.convert_file(env, "marin", "data/resource_calendar_data.xml", None, mode="init", kind="data")

    env.cr.execute("""SELECT setval('"public"."res_partner_id_seq"', 200, true);""")
    env.cr.execute("""SELECT setval('"public"."res_users_id_seq"', 100, true);""")
    tools.convert.convert_file(env, "marin", "data/website_data.xml", None, mode="init", kind="data")
    tools.convert.convert_file(env, "marin", "data/res_users_data.xml", None, mode="init", kind="data")

    env.cr.execute("""SELECT setval('"public"."stock_location_id_seq"', 1000, true);""")
    env.cr.execute("""SELECT setval('"public"."stock_picking_type_id_seq"', 1000, true);""")
    env.cr.execute("""SELECT setval('"public"."stock_route_id_seq"', 1000, true);""")
    env.cr.execute("""SELECT setval('"public"."stock_rule_id_seq"', 1026, true);""")
    env.cr.execute("""SELECT setval('"public"."stock_warehouse_id_seq"', 100, true);""")

    warehouses = (
        env["stock.warehouse"]
        .sudo()
        .search([("active", "in", (True, False))], order="id ASC")
    )
    for wh in warehouses:
        exist = env["ir.model.data"].sudo().search([("model", "=", "stock.warehouse"), ("res_id", "=", wh.id)])
        if not exist:
            env["ir.model.data"].create(
                {
                    "module": "marin",
                    "model": "stock.warehouse",
                    "name": "stock_warehouse_%s" % wh.id,
                    "res_id": wh.id,
                    "noupdate": True,
                }
            )
    tools.convert.convert_file(env, "marin", "data/stock_warehouse_data.xml", None, mode="init", kind="data")

    env["ir.module.module"].search([("name", "=", "snailmail")]).sudo().button_uninstall()
    env["ir.module.module"].search([("name", "=", "partner_autocomplete")]).sudo().button_uninstall()
    env["ir.module.module"].search([("name", "=", "google_gmail")]).sudo().button_uninstall()
    env["ir.module.module"].search([("name", "=", "crm_iap_mine")]).sudo().button_uninstall()
    env["ir.module.module"].search([("name", "=", "crm_iap_enrich")]).sudo().button_uninstall()
    env["ir.module.module"].search([("name", "=", "account_bank_statement_import_ofx")]).sudo().button_uninstall()
    env["ir.module.module"].search([("name", "=", "account_bank_statement_import_camt")]).sudo().button_uninstall()
