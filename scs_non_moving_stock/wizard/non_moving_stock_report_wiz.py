# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class NonMovingStock(models.TransientModel):

    _name = 'non.moving.stock'
    _description = 'Non Moving Stock'

    form_date = fields.Date(string='Form Date', required=True)
    to_date = fields.Date(string='To Date', required=True)

    @api.constrains('to_date', 'form_date')
    def is_validate(self):
        if self.form_date > self.to_date:
            raise ValidationError(_("To date should be greater "
                                    "than Form date"))

    def print_report(self):
        return self.env.ref(
            'scs_non_moving_stock.report_non_moving_stock').report_action(self)
