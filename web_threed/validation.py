import logging
import os

from lxml import etree

from odoo.loglevels import ustr
from odoo.tools import misc, view_validation

_logger = logging.getLogger(__name__)

THREED_VIEW_VALIDATOR = None


@view_validation.validate("threedview")
def schema_threedview(arch, **kwargs):
    """Check the threedview view against its schema

    :type arch: etree._Element
    """
    global THREED_VIEW_VALIDATOR  # pylint: disable=global-statement

    if THREED_VIEW_VALIDATOR is None:
        with misc.file_open(os.path.join("web_threed", "rng", "web_threed.rng")) as file:
            THREED_VIEW_VALIDATOR = etree.RelaxNG(etree.parse(file))

    if THREED_VIEW_VALIDATOR.validate(arch):
        return True

    for error in THREED_VIEW_VALIDATOR.error_log:
        _logger.error(ustr(error))
    return False
