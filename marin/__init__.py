from . import models
from . import report
from . import wizards


def _pre_init_marin(env):
    env.cr.execute("""SELECT setval('"public"."res_partner_category_id_seq"', 100, true);""")
