from odoo import _, fields, models


class WorkflowActionRuleAccountInherit(models.Model):
    _inherit = "documents.workflow.rule"

    create_model = fields.Selection(selection_add=[("cfdi", "CFDI")])

    def create_record(self, documents=None):
        rv = super().create_record(documents=documents)
        if self.create_model == "cfdi":
            obj_exist = None
            move_ids = []
            for document in documents:
                _is_cfdi, _is_cfdi_signed, cfdi_etree = self.env["l10n_mx_edi.document"].check_objectify_xml(
                    document.datas
                )
                obj_exist = self.env["l10n_mx_edi.document"].xml2record(cfdi_etree)
                if not obj_exist.edi_document_ids:
                    self.env["account.edi.document"].create(
                        {
                            "move_id": obj_exist.id,
                            "edi_format_id": self.env.ref("l10n_mx_edi_documents.edi_cfdi_3_3").id,
                            "attachment_id": document.attachment_id.id,
                            "state": "sent",
                        }
                    )
                document.attachment_id.with_context(no_document=True).write(
                    {
                        "res_model": "account.move",
                        "res_id": obj_exist.id,
                    }
                )
                move_ids.append(obj_exist.id)
            context = dict(self._context)
            action = {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "name": _("Moves"),
                "view_id": False,
                "view_mode": "tree",
                "views": [(False, "list"), (False, "form")],
                "domain": [("id", "in", move_ids)],
                "context": context,
            }
            if len(move_ids) == 1:
                record = obj_exist or self.env["account.move"].browse(move_ids[0])
                view_id = record.get_formview_id() if record else False
                action.update(
                    {
                        "view_mode": "form",
                        "views": [(view_id, "form")],
                        "res_id": move_ids[0],
                        "view_id": view_id,
                    }
                )
            return action
        return rv
