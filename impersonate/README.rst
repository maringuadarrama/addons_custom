Odoo impersonate
================

Allows you to be able to impersonate an internal user.

- Go to web/login page
- At login filed introduce the user's login you want to impersonate
- At password field you must introduce your credentials as login/password.

e.g.
login: demo@email.com
password: admin@email.com/adminpassword

After that you will be logged in as demo user.


Also you will need to setup your user with the groups
- Spoof Employee (In order to impersonate an internal user)
- Spoof Customer/Portal (In order to impersonate a Customer/portal user)


Also were added new role levels for all internal users, you can setup
following groups:
- Technical user role
- Sales man user role
- Functional user role

Use theme to track support level type.



Contributors
------------

* Hugo Adan <hugo@vauxoo.com>

Maintainer
----------

.. image:: https://www.vauxoo.com/logo.png
    :alt: Vauxoo
    :target: https://vauxoo.com

This module is maintained by Vauxoo.

a latinamerican company that provides training, coaching,
development and implementation of enterprise management
sytems and bases its entire operation strategy in the use
of Open Source Software and its main product is odoo.

To contribute to this module, please visit http://www.vauxoo.com.
