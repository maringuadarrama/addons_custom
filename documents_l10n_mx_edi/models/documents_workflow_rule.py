from odoo import _, fields, models


class WorkflowActionRuleEdi(models.Model):
    _inherit = "documents.workflow.rule"

    create_model = fields.Selection(selection_add=[("create.mx.edi.record", "CFDI")])

    def check_document_linked_to_record(self, documents):
        documents_link_record = [d for d in documents if d.res_model != "documents.document"]
        if documents_link_record:
            return {
                'warning': {
                    'title': _("Already linked Documents"),
                    'documents': [d.name for d in documents_link_record],
                }
            }

    def prepare_record_from_mx_edi_action(self):
        action = {
            'name': _('MX EDI to record'),
            'type': 'ir.actions.act_window',
            'res_model': 'documents.mx_edi_to_record_wizard',
            'view_mode': 'form',
            'target': 'new',
            'views': [(False, "form")],
            "context": {}
        }
        return action

    def create_record_from_mx_edi(self, documents):
        self.check_document_linked_to_record(documents)
        action = self.prepare_record_from_mx_edi_action()
        action.update({"context": {"default_document_ids": documents.ids}})
        return action

    def create_record(self, documents=None):
        self.ensure_one()
        if self.create_model == "create.mx.edi.record":
            return self.create_record_from_mx_edi(documents)
        
        return super().create_record(documents=documents)
