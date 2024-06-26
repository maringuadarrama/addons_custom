from odoo import Command, api
from odoo.exceptions import AccessDenied, AccessError
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger


@tagged("user")
class TestUser(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_admin = cls.env.ref("base.user_admin")
        cls.uid = cls.user_admin.id
        cls.env = api.Environment(cls.cr, cls.uid, {})
        cls.user_demo = cls.env.ref("base.user_demo")
        cls.group_admin = cls.env.ref("base.group_system")
        cls.group_can_spoof = cls.env.ref("impersonate.group_user_spoof")
        cls.superuser = cls.env.ref("base.user_root")

    def create_admin_user(self):
        user = self.env["res.users"].create(
            {
                "name": "New admin",
                "login": "new.admin@example.com",
                "groups_id": [Command.set(self.group_admin.ids)],
            }
        )
        return user

    def test_01_modify_user_without_privileges(self):
        """Try to make an user admin without being superuser"""
        error_msg = "Privilege escalation attempt while modifying an user"
        expected_log = "odoo.addons.impersonate.models.res_users"
        with self.assertRaisesRegex(AccessError, error_msg), mute_logger(expected_log):
            self.user_demo.groups_id |= self.group_admin

    def test_02_modify_user_with_privileges(self):
        """Make an user admin being superuser"""
        self.user_demo.sudo().groups_id |= self.group_admin
        self.assertIn(self.group_admin, self.user_demo.groups_id)

    def test_03_create_user_without_privileges(self):
        """Try to create an admin user without being superuser"""
        error_msg = "Privilege escalation attempt while creating an user"
        expected_log = "odoo.addons.impersonate.models.res_users"
        with self.assertRaisesRegex(AccessError, error_msg), mute_logger(expected_log):
            self.create_admin_user()

    def test_04_create_user_with_privileges(self):
        """Create an admin user being superuser"""
        self.uid = self.superuser.id
        self.env = api.Environment(self.cr, self.uid, {})
        new_admin = self.create_admin_user()
        self.assertTrue(new_admin)

    def test_05_add_user_admin_group_without_privileges(self):
        """Try to add an user to the admin group without being superuser"""
        error_msg = "Privilege escalation attempt while modifying group"
        expected_log = "odoo.addons.impersonate.models.res_groups"
        with self.assertRaisesRegex(AccessError, error_msg), mute_logger(expected_log):
            self.group_admin.users |= self.user_demo

    def test_06_add_user_admin_group_without_privileges(self):
        """Try to add an user to the admin group being superuser"""
        self.user_demo.sudo().groups_id |= self.group_admin
        self.assertIn(self.group_admin, self.user_demo.groups_id)

    def test_07_spoof_user(self):
        """Thest spoofing an user

        Several combinations are covered:
        - Standard login
        - Loging by spoofing the user (belonging to group that allows so)
        - Loging belonging to users that can spoof but providing an invalid username or password
        - Loging without belonging to users that can spoof
        """
        # Standard login
        session = self.authenticate(user="demo", password="demo")
        self.assertEqual(session.uid, self.user_demo.id)

        # Loging by spoofing the user
        self.user_admin.groups_id |= self.group_can_spoof
        session = self.authenticate(user="demo", password="admin/admin")
        self.assertEqual(session.uid, self.user_demo.id)

        # Try to login by spoofing providing an invalid user
        with self.assertRaises(AccessDenied):
            self.authenticate(user="demo", password="admin2/admin")

        # Try to login by spoofing providing an invalid password
        with self.assertRaises(AccessDenied):
            self.authenticate(user="demo", password="admin/admin2")

        # Try to login by spoofing without belonging to the group that can spoof
        self.user_admin.groups_id -= self.group_can_spoof
        with self.assertRaises(AccessDenied):
            self.authenticate(user="demo", password="admin/admin")

        # A standard login failure
        with self.assertRaises(AccessDenied):
            self.authenticate(user="demo", password="demo2")
