# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Manage Mexican Documents",
    "version": "17.0.1.0.3",
    "author": "Vauxoo",
    "category": "Accounting",
    "license": "Other proprietary",
    "depends": [
        "documents",
        "l10n_mx",
        "l10n_mx_edi",
        "l10n_edi_document",
    ],
    "data": [
        "data/sat_folder.xml",
        "views/documents_views.xml",
        "views/res_config_settings_views.xml",
        "views/templates.xml",
    ],
    "demo": [
        "demo/settings.xml",
    ],
    "qweb": ["static/src/xml/*"],
    "assets": {
        "web.assets_backend": [
            "/l10n_mx_edi_document/static/src/sass/main.scss",
            # TODO: Migrate these files here and in l10n_edi_document to fix JS error.
            # "/l10n_mx_edi_document/static/src/js/checks_widget.js",
            # "/l10n_mx_edi_document/static/src/js/checklist_animation.js",
            "/l10n_mx_edi_document/static/src/js/documents_kanban_record.js",
            "/l10n_mx_edi_document/static/src/js/attachment_model.js",
            "/l10n_mx_edi_document/static/src/js/document_file_viewer.xml",
        ],
        "web.assets_qweb": [
            "/l10n_mx_edi_document/static/src/xml/checks_widget.xml",
        ],
    },
    "installable": True,
}
