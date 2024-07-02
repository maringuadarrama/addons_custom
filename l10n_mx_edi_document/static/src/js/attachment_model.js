/* @odoo-module */

import {patch} from "@web/core/utils/patch";
import {Attachment} from "@mail/core/common/attachment_model";

patch(Attachment.prototype, {
    get isMxXml() {
        return ["application/xml", "text/xml"].includes(this.mimetype);
    },
});
