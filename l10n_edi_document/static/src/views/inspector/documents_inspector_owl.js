/** @odoo-module **/

import {inspectorFields} from "@documents/views/inspector/documents_inspector";

inspectorFields.push(
    "customer_journal_id",
    "customer_account_id",
    "vendor_journal_id",
    "vendor_account_id",
    "invoice_date",
    "analytic_account_id",
    "in_finance_folder",
    "show_customer_fields",
    "analytic_group"
);
