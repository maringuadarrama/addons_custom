from . import wizards
from odoo import tools


def _pre_init_marin(env):
    env.cr.execute("""SELECT setval('"public"."res_partner_id_seq"', 100, true);""")
    tools.convert.convert_file(env, "marin_data", "data/res_company_data.xml", None, mode="init", kind="data")

    env.cr.execute("""SELECT setval('"public"."resource_calendar_id_seq"', 100, true);""")
    env.cr.execute("""SELECT setval('"public"."resource_calendar_attendance_id_seq"', 1000, true);""")
    tools.convert.convert_file(env, "marin_data", "data/resource_calendar_data.xml", None, mode="init", kind="data")

    env.cr.execute("""SELECT setval('"public"."res_partner_id_seq"', 200, true);""")
    env.cr.execute("""SELECT setval('"public"."res_users_id_seq"', 100, true);""")
    tools.convert.convert_file(env, "marin_data", "data/website_data.xml", None, mode="init", kind="data")
    tools.convert.convert_file(env, "marin_data", "data/res_users_data.xml", None, mode="init", kind="data")

    env.cr.execute("""SELECT setval('"public"."stock_location_id_seq"', 1000, true);""")
    env.cr.execute("""SELECT setval('"public"."stock_picking_type_id_seq"', 1000, true);""")
    env.cr.execute("""SELECT setval('"public"."stock_route_id_seq"', 1000, true);""")
    env.cr.execute("""SELECT setval('"public"."stock_rule_id_seq"', 1026, true);""")
    env.cr.execute("""SELECT setval('"public"."stock_warehouse_id_seq"', 100, true);""")

    warehouses = (
        env["stock.warehouse"]
        .sudo()
        .search([("id", ">=", 1), "|", ("active", "=", True), ("active", "=", False)], order="id ASC")
    )
    for wh in warehouses:
        exist = env["ir.model.data"].sudo().search([("model", "=", "stock.warehouse"), ("res_id", "=", wh.id)])
        if not exist:
            env["ir.model.data"].create(
                {
                    "module": "marin_data",
                    "model": "stock.warehouse",
                    "name": "stock_warehouse_%s" % wh.id,
                    "res_id": wh.id,
                    "noupdate": True,
                }
            )
    tools.convert.convert_file(env, "marin_data", "data/stock_warehouse_data.xml", None, mode="init", kind="data")

#    locations = (
#        env["stock.location"]
#        .sudo()
#        .search([("id", ">=", 1), "|", ("active", "=", True), ("active", "=", False)], order="id ASC")
#    )
#    for ln in locations:
#        exist = env["ir.model.data"].sudo().search([("model", "=", "stock.location"), ("res_id", "=", ln.id)])
#        if not exist:
#            env["ir.model.data"].create(
#                {
#                    "module": "marin_data",
#                    "model": "stock.location",
#                    "name": "stock_location_%s" % ln.id,
#                    "res_id": ln.id,
#                    "noupdate": True,
#                }
#            )
#    tools.convert.convert_file(env, "marin_data", "data/stock.location.csv", None, mode="init", kind="data")
#
#    types = (
#        env["stock.picking.type"]
#        .sudo()
#        .search([("id", ">=", 1), "|", ("active", "=", True), ("active", "=", False)], order="id ASC")
#    )
#    for spt in types:
#        exist = env["ir.model.data"].sudo().search([("model", "=", "stock.picking.type"), ("res_id", "=", spt.id)])
#        if not exist:
#            env["ir.model.data"].create(
#                {
#                    "module": "marin_data",
#                    "model": "stock.picking.type",
#                    "name": "stock_picking_type_%s" % spt.id,
#                    "res_id": spt.id,
#                    "noupdate": True,
#                }
#            )
#    tools.convert.convert_file(env, "marin_data", "data/stock.picking.type.csv", None, mode="init", kind="data")
#    tools.convert.convert_file(env, "marin_data", "data/stock.route.csv", None, mode="init", kind="data")
#    # env.cr.execute("""SELECT setval('"public"."stock_rule_id_seq"', 5000, true);""")
#    # tools.convert.convert_file(env, "marin_data", "data/stock.rule.csv", None, mode="init", kind="data")
#
#    env.cr.execute("""SELECT setval('"public"."account_account_id_seq"', 1000, true);""")
#    env.cr.execute("""SELECT setval('"public"."account_analytic_plan_id_seq"', 200, true);""")
#    env.cr.execute("""SELECT setval('"public"."account_journal_id_seq"', 500, true);""")
#    env.cr.execute("""SELECT setval('"public"."account_payment_method_line_id_seq"', 1000, true);""")
#    env.cr.execute("""SELECT setval('"public"."account_payment_term_id_seq"', 100, true);""")
#    env.cr.execute("""SELECT setval('"public"."account_payment_term_line_id_seq"', 100, true);""")
#    env.cr.execute("""SELECT setval('"public"."account_tax_group_id_seq"', 500, true);""")
#    env.cr.execute("""SELECT setval('"public"."account_tax_id_seq"', 500, true);""")
#    env.cr.execute("""SELECT setval('"public"."account_tax_repartition_line_id_seq"', 1000, true);""")
#    tools.convert.convert_file(
#        env, "marin_data", "data/account_analytic_plan_data.xml", None, mode="init", kind="data"
#    )
#    tools.convert.convert_file(env, "marin_data", "data/account.account.csv", None, mode="init", kind="data")
#    tools.convert.convert_file(
#        env, "marin_data", "data/account_journal_group_data.xml", None, mode="init", kind="data"
#    )
#    tools.convert.convert_file(env, "marin_data", "data/account.journal.csv", None, mode="init", kind="data")
#    tools.convert.convert_file(env, "marin_data", "data/account_asset_data.xml", None, mode="init", kind="data")
#    tools.convert.convert_file(env, "marin_data", "data/account.payment.term.csv", None, mode="init", kind="data")
#    tools.convert.convert_file(env, "marin_data", "data/account_tax_group_data.xml", None, mode="init", kind="data")
#    tools.convert.convert_file(env, "marin_data", "data/account_tax_data.xml", None, mode="init", kind="data")

    tools.convert.convert_file(env, "marin_data", "data/crm_team_data.xml", None, mode="init", kind="data")

    tools.convert.convert_file(env, "marin_data", "data/hr_department_data.xml", None, mode="init", kind="data")
    tools.convert.convert_file(env, "marin_data", "data/hr_job_data.xml", None, mode="init", kind="data")
    tools.convert.convert_file(env, "marin_data", "data/hr_payroll_structure_data.xml", None, mode="init", kind="data")
    tools.convert.convert_file(env, "marin_data", "data/hr_salary_rule_data.xml", None, mode="init", kind="data")
    tools.convert.convert_file(env, "marin_data", "data/hr_salary_rule_christmas_bonus_data.xml", None, mode="init", kind="data")
    tools.convert.convert_file(env, "marin_data", "data/hr_salary_rule_nomina_finiquito_data.xml", None, mode="init", kind="data")
    tools.convert.convert_file(env, "marin_data", "data/l10n_mx_edi_employer_registration_data.xml", None, mode="init", kind="data")

#    env.cr.execute("""SELECT setval('"public"."pos_config_id_seq"', 100, true);""")
#    env.cr.execute("""SELECT setval('"public"."pos_payment_method_id_seq"', 100, true);""")
#    tools.convert.convert_file(env, "marin_data", "data/pos_payment_method_data.xml", None, mode="init", kind="data")
#    tools.convert.convert_file(env, "marin_data", "data/pos.category.csv", None, mode="init", kind="data")
#    tools.convert.convert_file(env, "marin_data", "data/pos_config_data.xml", None, mode="init", kind="data")

#    env.cr.execute(
#        """DELETE FROM ir_property WHERE name IN ('property_account_payable_id', 'property_account_receivable_id', 'property_account_expense_categ_id', 'property_account_income_categ_id');"""
#    )
#    tools.convert.convert_file(env, "marin_data", "data/ir_property_data.xml", None, mode="init", kind="data")
#
#    tools.convert.convert_file(env, "marin_data", "data/post_init_data.xml", None, mode="init", kind="data")
#    tools.convert.convert_file(env, "marin_data", "data/res.company.csv", None, mode="init", kind="data")
#    env.cr.execute("""UPDATE ir_model_data SET noupdate='t' WHERE "module"='marin_data'""")

    # instead of xml file
    env.cr.execute("""UPDATE res_company SET account_purchase_tax_id=NULL;""")
    env.cr.execute("""UPDATE res_company SET account_sale_tax_id=NULL;""")
    env.cr.execute("""UPDATE res_company SET extract_in_invoice_digitalization_mode='manual_send';""")
    env.cr.execute("""UPDATE res_company SET extract_out_invoice_digitalization_mode='manual_send';""")
    env.cr.execute("""UPDATE res_company SET recruitment_extract_show_ocr_option_selection='manual_send';""")
    env.cr.execute("""UPDATE res_company SET expense_extract_show_ocr_option_selection='manual_send';""")
    env.cr.execute("""UPDATE res_company SET product_folder=7;""")
    env.cr.execute("""UPDATE res_company SET stock_move_sms_validation='f';""")
    env.cr.execute("""UPDATE res_company SET l10n_mx_edi_pac='finkok';""")
    env.cr.execute("""UPDATE res_company SET l10n_mx_edi_pac_username='marin.guadarrama@gmail.com';""")
    env.cr.execute("""UPDATE res_company SET point_of_sale_update_stock_quantities='real';""")
    env.cr.execute("""UPDATE res_company SET quotation_validity_days=7;""")
    env.cr.execute("""UPDATE res_company SET portal_confirmation_sign='f';""")
    env.cr.execute("""UPDATE res_company SET portal_confirmation_pay='f';""")
    env.cr.execute("""UPDATE res_company SET l10n_mx_edi_minimum_wage=248.93;""")
    env.cr.execute("""UPDATE res_company SET l10n_mx_edi_uma=108.57;""")
    env.cr.execute("""UPDATE res_company SET predict_bill_product='t';""")
    env.cr.execute("""UPDATE res_company SET rule_type='sale_purchase';""")
    env.cr.execute("""UPDATE res_company SET font='Roboto';""")
    env.cr.execute("""UPDATE res_company SET layout_background='Geometric';""")

    # This data will be manually imported, execute queries to avoid future sequence errors
    env.cr.execute("""SELECT setval('"public"."account_asset_id_seq"', 921, true);""")
    env.cr.execute("""SELECT setval('"public"."account_analytic_account_id_seq"', 3055, true);""")
    env.cr.execute("""SELECT setval('"public"."account_analytic_distribution_model_id_seq"', 929, true);""")
    # env.cr.execute("""SELECT setval('"public"."account_analytic_line_id_seq"', 35308, true);""")
    env.cr.execute("""SELECT setval('"public"."account_bank_statement_id_seq"', 833, true);""")
    env.cr.execute("""SELECT setval('"public"."account_bank_statement_line_id_seq"', 34365, true);""")
    env.cr.execute("""SELECT setval('"public"."account_full_reconcile_id_seq"', 83933, true);""")
    env.cr.execute("""SELECT setval('"public"."account_move_id_seq"', 251539, true);""")
    env.cr.execute("""SELECT setval('"public"."account_move_line_id_seq"', 1035692, true);""")
    env.cr.execute("""SELECT setval('"public"."account_payment_id_seq"', 22814, true);""")
    env.cr.execute("""SELECT setval('"public"."account_partial_reconcile_id_seq"', 209286, true);""")
    env.cr.execute("""SELECT setval('"public"."account_reconcile_model_id_seq"', 100, true);""")
    env.cr.execute("""SELECT setval('"public"."calendar_event_id_seq"', 11806, true);""")
    env.cr.execute("""SELECT setval('"public"."calendar_attendee_id_seq"', 8795, true);""")
    env.cr.execute("""SELECT setval('"public"."consolidation_chart_id_seq"', 21, true);""")
    env.cr.execute("""SELECT setval('"public"."consolidation_period_id_seq"', 39, true);""")
    env.cr.execute("""SELECT setval('"public"."consolidation_company_period_id_seq"', 94, true);""")
    env.cr.execute("""SELECT setval('"public"."consolidation_group_id_seq"', 59, true);""")
    env.cr.execute("""SELECT setval('"public"."consolidation_account_id_seq"', 59, true);""")
    env.cr.execute("""SELECT setval('"public"."fleet_vehicle_id_seq"', 130, true);""")
    env.cr.execute("""SELECT setval('"public"."hr_employee_id_seq"', 69, true);""")
    env.cr.execute("""SELECT setval('"public"."hr_expense_id_seq"', 4203, true);""")
    env.cr.execute("""SELECT setval('"public"."hr_contract_id_seq"', 91, true);""")
    env.cr.execute("""SELECT setval('"public"."hr_payslip_id_seq"', 4307, true);""")
    env.cr.execute("""SELECT setval('"public"."hr_payslip_line_id_seq"', 110463, true);""")
    env.cr.execute("""SELECT setval('"public"."mrp_bom_id_seq"', 118, true);""")
    env.cr.execute("""SELECT setval('"public"."mrp_bom_line_id_seq"', 1221, true);""")
    env.cr.execute("""SELECT setval('"public"."mrp_production_id_seq"', 73, true);""")
    env.cr.execute("""SELECT setval('"public"."mrp_workcenter_id_seq"', 2, true);""")
    env.cr.execute("""SELECT setval('"public"."mrp_workorder_id_seq"', 41, true);""")
    env.cr.execute("""SELECT setval('"public"."pos_order_id_seq"', 24620, true);""")
    env.cr.execute("""SELECT setval('"public"."pos_order_line_id_seq"', 55034, true);""")
    env.cr.execute("""SELECT setval('"public"."pos_payment_id_seq"', 25702, true);""")
    env.cr.execute("""SELECT setval('"public"."pos_session_id_seq"', 3563, true);""")
    env.cr.execute("""SELECT setval('"public"."procurement_group_id_seq"', 17400, true);""")
    env.cr.execute("""SELECT setval('"public"."product_template_id_seq"', 1690, true);""")
    env.cr.execute("""SELECT setval('"public"."product_product_id_seq"', 1690, true);""")
    env.cr.execute("""SELECT setval('"public"."product_packaging_id_seq"', 361, true);""")
    env.cr.execute("""SELECT setval('"public"."product_supplierinfo_id_seq"', 613, true);""")
    env.cr.execute("""SELECT setval('"public"."project_task_id_seq"', 1073, true);""")
    env.cr.execute("""SELECT setval('"public"."purchase_order_id_seq"', 3075, true);""")
    env.cr.execute("""SELECT setval('"public"."purchase_order_line_id_seq"', 6801, true);""")
    env.cr.execute("""SELECT setval('"public"."resource_resource_id_seq"', 71, true);""")
    env.cr.execute("""SELECT setval('"public"."res_partner_bank_id_seq"', 141, true);""")
    env.cr.execute("""SELECT setval('"public"."res_partner_id_seq"', 3906, true);""")
    env.cr.execute("""SELECT setval('"public"."stock_lot_id_seq"', 2718, true);""")
    env.cr.execute("""SELECT setval('"public"."stock_move_id_seq"', 208079, true);""")
    env.cr.execute("""SELECT setval('"public"."stock_move_line_id_seq"', 246330, true);""")
    env.cr.execute("""SELECT setval('"public"."stock_picking_id_seq"', 77580, true);""")
    env.cr.execute("""SELECT setval('"public"."stock_picking_type_id_seq"', 1205, true);""")
    env.cr.execute("""SELECT setval('"public"."stock_quant_id_seq"', 4735, true);""")
    env.cr.execute("""SELECT setval('"public"."stock_rule_id_seq"', 5022, true);""")
    env.cr.execute("""SELECT setval('"public"."stock_warehouse_orderpoint_id_seq"', 654, true);""")
    env.cr.execute("""SELECT setval('"public"."sale_order_template_id_seq"', 105, true);""")
    env.cr.execute("""SELECT setval('"public"."sale_order_template_line_id_seq"', 285, true);""")
    env.cr.execute("""SELECT setval('"public"."sale_order_id_seq"', 17898, true);""")
    env.cr.execute("""SELECT setval('"public"."sale_order_line_id_seq"', 72239, true);""")
    env.cr.execute("""SELECT setval('"public"."survey_question_id_seq"', 22, true);""")
    env.cr.execute("""SELECT setval('"public"."survey_question_answer_id_seq"', 67, true);""")
    env.cr.execute("""SELECT setval('"public"."slide_channel_id_seq"', 1, true);""")
    env.cr.execute("""SELECT setval('"public"."slide_slide_id_seq"', 148, true);""")
    env.cr.execute("""SELECT setval('"public"."slide_question_id_seq"', 500, true);""")
    env.cr.execute("""SELECT setval('"public"."slide_answer_id_seq"', 1664, true);""")
