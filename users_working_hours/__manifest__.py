{
    "name": "Users Working Hours",
    "summary": """
    Enables set working hours for all users
    """,
    "author": "Vauxoo",
    "website": "https://www.vauxoo.com",
    "license": "OPL-1",
    "category": "Extra Tools",
    "version": "1.0",
    "depends": [
        "hr",
    ],
    "data": [
        # Security
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        # Data
        "data/ir_actions_server.xml",
        # Views
        "views/ir_sessions_views.xml",
        # Wizards
        "wizard/users_allow_login_views.xml",
        "wizard/users_update_attendance_views.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": True,
}
