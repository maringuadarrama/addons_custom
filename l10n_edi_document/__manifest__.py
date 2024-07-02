# Copyright 2020 Vauxoo
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "EDI Documents",
    "summary": """
    Main module to allow create EDI documents on Odoo
    """,
    "author": "Vauxoo",
    "website": "https://www.vauxoo.com",
    "license": "LGPL-3",
    "category": "Operations/Documents/Accounting",
    "version": "17.0.1.0.3",
    "depends": [
        "account_edi",
        "documents",
    ],
    "test": [],
    "data": [
        "security/ir.model.access.csv",
        "wizard/attach_document_invoice_wizard_view.xml",
        "data/data.xml",
        "data/ir_cron_data.xml",
        "views/account_move_view.xml",
        "views/documents_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "demo": [],
    "assets": {
        "web.assets_backend": [
            "/l10n_edi_document/static/src/views/inspector/documents_inspector_owl.js",
            "/l10n_edi_document/static/src/views/inspector/documents_inspector.xml",
            "/l10n_edi_document/static/src/sass/widget.scss",
            # TODO: When enabled, these files cause a JS error that prevents Odoo from loading, resulting in
            # a blank page after login. The following is displayed on the browser debug console:
            # 'Uncaught Error: Dependencies should be defined by an array ...'
            # "/l10n_edi_document/static/src/js/checks_widget.js",
            # "/l10n_edi_document/static/src/js/checklist_animation.js",
        ],
        "web.assets_qweb": [
            "/l10n_edi_document/static/src/xml/checks_widget.xml",
        ],
    },
    "installable": True,
    "auto_install": False,
}
