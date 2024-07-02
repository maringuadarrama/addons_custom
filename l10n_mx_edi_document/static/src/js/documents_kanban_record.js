/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import {DocumentsKanbanRecord} from "@documents/views/kanban/documents_kanban_model";

patch(DocumentsKanbanRecord.prototype, {
    /**
     * @override
     */
    isViewable() {
        return (
            this.data.mimetype === "application/xml" ||
            this.data.mimetype === "text/xml" ||
            super.isViewable(...arguments)
        );
    },
});
