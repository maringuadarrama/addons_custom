{
    "name": "Marin",
    "summary": """
    Instance creator for Marin. This is the app.
    """,
    "author": "Marin Agro",
    "website": "https://www.agromarin.mx",
    "license": "OPL-1",
    "category": "Installer",
    "version": "1.0",
    "depends": [
        "attachment_indexation",
        "barcodes",
        "base_geolocalize",
        "http_routing",
        "date_range",
        "mail",
        "web_studio",
        "data_recycle",
        "timer",
        "calendar",
        "board",
        "analytic",
        "product",
        "loyalty",
        "sales_team",
        "survey",
        "knowledge",
        "room",
        "fleet",
        "documents_expiry",
        "documents_partner",
        "base_address_extended",
        "hr_attendance",
        "hr_contract",
        "hr_holidays",
        "hr_homeworking",
        "hr_presence",
        "hr_recruitment_survey",
        "hr_appraisal_survey",
        "appointment",
        "project_forecast",
        "product_expiry",
        "stock_barcode_picking_batch",
        "stock_barcode_mrp_subcontracting",
        # "stock_3dpicking",
        "mrp_plm",
        "quality_mrp",
        "account_accountant",
        "account_debit_note",
        "account_budget",
        "account_reports_cash_basis",
        "account_consolidation",
        "account_move_name_sequence",
        # "account_move_operation",
        "product_margin",
        "hr_payroll_expense",
        "l10n_mx_avoid_reversal_entry",
        # "l10n_mx_edi_document",
        "l10n_mx_edi_extended",
        "l10n_mx_edi_payslip",
        "l10n_mx_partner_blocklist",
        # "l10n_mx_edi_related_documents",
        # "l10n_mx_edi_partner_defaults",
        # "l10n_mx_edi_supplier_defaults",
        "l10n_mx_edi_refund",
        "purchase_requisition_stock",
        "stock_landed_costs_company",
        "account_3way_match",
        "purchase_team",
        "account_invoice_margin_sale",
        "delivery",
        "stock_dropshipping",
        "sale_purchase_inter_company_rules",
        "sale_order_global_stock_route",
        "sale_commercial_partner",
        "sale_renting",
        "point_of_sale",
        "website_sale_picking",
        "website_sale_comparison",
        "website_event_sale",
        "website_blog",
        "website_slides",
        "website_customer",
        # "website_tiledesk",
        # "users_working_hours",
        "impersonate",
        "syngenta_edi",
    ],
    #"data": [
    #    "security/res_groups_security.xml",
    #    "security/ir.model.access.csv",
    #    "security/ir_rules.xml",
    #    "data/ir_config_parameter_data.xml",
    #    "data/res_config_settings_data.xml",
    #    "data/ir_actions_server_data.xml",
    #    "data/ir_cron_data.xml",
    #    "data/res_lang_data.xml",
    #    "data/ir_default_data.xml",
    #    "data/mail_activity_data.xml",
    #    "data/res_partner_category_data.xml",
    #    "data/res_partner_age_range_data.xml",
    #    "data/res_bank_data.xml",
    #    "data/documents_folder_data.xml",
    #    "data/documents_facet_data.xml",
    #    "data/documents_tag_data.xml",
    #    "data/documents_workflow_rule_data.xml",
    #    "data/product_removal_data.xml",
    #    "data/website_data.xml",
    #    "report/report_deliveryslip.xml",
    #    "report/report_stock_picking_operations.xml",
    #    "report/report_invoice.xml",
    #    "report/report_payment.xml",
    #    "views/account_account_views.xml",
    #    "views/account_analytic_distribution_model_views.xml",
    #    "views/account_analytic_line_views.xml",
    #    "views/account_bank_statement_views.xml",
    #    "views/account_journal_views.xml",
    #    "views/account_move_views.xml",
    #    "views/account_move_line_views.xml",
    #    "views/account_payment_term_views.xml",
    #    "views/account_payment_views.xml",
    #    "views/crm_lead_views.xml",
    #    "views/documents_document_views.xml",
    #    "views/fleet_vehicle_views.xml",
    #    "views/hr_expense_views.xml",
    #    "views/hr_contract_views.xml",
    #    "views/hr_payslip_views.xml",
    #    "views/pos_config_views.xml",
    #    "views/pos_order_views.xml",
    #    "views/pos_session_views.xml",
    #    "views/product_category_views.xml",
    #    "views/product_product_views.xml",
    #    "views/product_template_views.xml",
    #    "views/purchase_order_views.xml",
    #    "views/purchase_order_line_views.xml",
    #    "views/res_company_views.xml",
    #    "views/res_config_settings_views.xml",
    #    "views/res_partner_views.xml",
    #    "views/res_users_views.xml",
    #    "views/sale_order_views.xml",
    #    "views/sale_order_line_views.xml",
    #    "views/stock_move_views.xml",
    #    "views/stock_picking_type_views.xml",
    #    "views/stock_picking_views.xml",
    #    "views/stock_location_views.xml",
    #    "views/stock_lot_views.xml",
    #    "views/stock_move_line_views.xml",
    #    "views/stock_quant_views.xml",
    #    "views/menuitem_views.xml",
    #    "wizards/authorize_debt.xml",
    #    "wizards/invoice_cash_discount.xml",
    #    "wizards/invoice_line_price_history.xml",
    #    "wizards/pos_cash_transfer_wizard.xml",
    #    "wizards/purchase_order_line_price_history.xml",
    #    "wizards/sale_order_line_price_history.xml",
    #    "wizards/stock_move_location.xml",
    #    "wizards/stock_quant_lot.xml",
    #],
    #"demo": [
    #    "demo/ir_default_data.xml",
    #],
    "pre_init_hook": "_pre_init_xiuman",
    #"assets": {
    #    "web.assets_backend": [
    #        "xiuman/static/src/widgets/**/*",
    #    ],
    #    "point_of_sale._assets_pos": [
    #        "xiuman/static/src/pos/app/**/*",
    #    ],
    #},
    "installable": True,
    "application": True,
}
