# See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo import models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class ReportsNonMovingStock(models.AbstractModel):
    _name = 'report.scs_non_moving_stock.templates_non_moving_stock'
    _description = 'Report Templates Non Moving Stock'

    def _get_non_moving_stock(self, wiz_id):
        stock_move_product_list = []
        stock_move_ids = self.env['stock.move'].search(
            [('date', '>=', wiz_id.form_date),
             ('date', '<=', wiz_id.to_date)])
        for stock_id in stock_move_ids:
            stock_move_product_list.append(stock_id.product_id.id)
        non_moving_stock_ids = self.env['product.product'].search(
            [('id', 'not in', stock_move_product_list)]).filtered(lambda p: p.type == 'product')
        return non_moving_stock_ids

    def _get_last_sale_date(self, product_id):
        last_sale_date = False
        sale_order_line_ids = self.env['sale.order.line'].search(
            [('product_id', '=', product_id.id)])
        for data in sale_order_line_ids:
            if last_sale_date and data.order_id.date_order and \
                    last_sale_date < data.order_id.date_order:
                last_sale_date = data.order_id.date_order
            if not last_sale_date:
                last_sale_date = data.order_id.date_order
        if last_sale_date:
            last_sale_date = datetime.strftime(
                last_sale_date, DEFAULT_SERVER_DATE_FORMAT)
        return last_sale_date

    def _get_warehouse(self, product_id):
        warehouse_list = []
        location_list = []
        stock_quant_obj = self.env['stock.quant']
        stock_quant_ids = stock_quant_obj.search([('product_id', '=',
                                                   product_id.id)])
        for stock_quant in stock_quant_ids:
            location_list.append(stock_quant.location_id.id)
        location_list = list(set(location_list))
        for rec in self.env['stock.location'].browse(location_list):
            total_qty = 0.0
            total_valuation = 0.0
            for sum in stock_quant_obj.search(
                    [('location_id', '=', rec.id),
                     ('product_id', '=', product_id.id)]):
                if sum.location_id.usage == 'internal':
                    total_qty += sum.quantity
                    total_valuation += product_id.standard_price * sum.quantity
            if rec.usage == 'internal':
                stock_warehouse_id = self.env['stock.warehouse'].search(
                    [('lot_stock_id', '=', rec.id)])
                warehouse_list.append({'st_qu': rec.name,
                                       'wh': stock_warehouse_id.name,
                                       'qty': total_qty,
                                       'valuation': total_valuation})
        return warehouse_list

    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'non.moving.stock',
            'docs': self.env['non.moving.stock'].browse(docids),
            'data': data,
            'get_non_moving_stock': self._get_non_moving_stock,
            'get_last_sale_date': self._get_last_sale_date,
            'get_warehouse': self._get_warehouse,
        }
