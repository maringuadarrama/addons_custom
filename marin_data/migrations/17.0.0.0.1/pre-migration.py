import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    set_xml_id(cr)


def set_xml_id(cr):
    """Set xml_id of record that was created manually."""
    query = """
        INSERT INTO
            ir_model_data (
                name,
                res_id,
                module,
                model,
                noupdate
            )
        VALUES
            ('hr_job_13', 13, 'marin_data', 'hr.job', TRUE),
            ('hr_job_14', 14, 'marin_data', 'hr.job', TRUE);
    """
    cr.execute(query)
