from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    weight = fields.Float(related='product_id.weight')
    total_weight = fields.Float(compute='_compute_total_weight')

    def _compute_total_weight(self):
        for record in self:
            record.total_weight = record.weight * record.product_qty


class ProductTemplate(models.Model):
    _inherit = "product.template"

    pet = fields.Selection([('cat_food', 'Cat Food'), ('dog_food', 'Dog Food'), ('accessories', 'Accessories')])
    food_type = fields.Selection([('dry', 'Dry'), ('wet', 'Wet'), ('none', 'None')])
    product_type = fields.Selection([('local', 'Local'), ('import', 'Import')])
