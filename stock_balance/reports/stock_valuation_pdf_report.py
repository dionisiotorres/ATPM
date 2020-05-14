# -*- coding: utf-8 -*-
from odoo import models, api


class StockValuationPDF(models.AbstractModel):
    _name = 'report.stock_balance.stock_valuation_pdf_report_template'

    def cat_has_valuation(self, categs, category_id):
        if category_id in categs:
            return True
        return False

    def has_valuation(self, stock_valuation_lines, company_id):
        for valuation in stock_valuation_lines:
            if not valuation['company_id'] or valuation['company_id'] == company_id.id:
                return True
        return False

    def product_of_categ(self, product_id, categ_id):
        return self.env['product.product'].browse(product_id).categ_id.id == categ_id

    def get_product_name(self, product_id):
        return self.env['product.product'].browse(product_id).mapped('display_name')[0]

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'docs': self,
            'lines': data['lines'],
            'categs': self.env['product.product'].browse(
                [valuation['product_id'] for valuation in data['lines']]).mapped('categ_id'),
            'warehouses': data['warehouses'],
            'date_from': data['date_from'],
            'all_categories': self.env['product.category'].browse(data['all_categories']),
            'date_to': data['date_to'],
            'cat_has_valuation': self.cat_has_valuation,
            'get_product_name': self.get_product_name,
            'product_of_categ': self.product_of_categ,
            'has_valuation': self.has_valuation,
            'all_companies': self.env['res.company'].browse(data['company_ids']),
            'display_only_summary': data['display_only_summary']
        }
