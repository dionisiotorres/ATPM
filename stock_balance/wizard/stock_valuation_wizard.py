# -*- coding: utf-8 -*-
from datetime import date

from dateutil.relativedelta import *

from odoo import models, fields
from odoo.osv import expression


class StockValuationAbstract(models.TransientModel):
    _name = 'stock_balance.stock_valuation_wizard'

    # In odoo 13, the user can select more than one company on the company switcher.
    # To get the selected companies we use self.env.companies
    company_id = fields.Many2one(
        "res.company", "Company",
        default=lambda self: self.env.companies.ids[0],
        domain=lambda self: [('id', 'in', self.env.companies.ids)]
    )
    warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "wizard_warehouse_rel",
        string="Warehouses",
        default=lambda self: self.env['stock.warehouse'].search([]).ids
    )
    location_id = fields.Many2one(
        "stock.location",
        "Locations",
        domain=[('usage', '=', 'internal')]
    )
    date_from = fields.Datetime(
        "From Date",
        required=True,
        default=date.today().replace(day=1)
    )
    date_to = fields.Datetime(
        "To Date",
        required=True,
        default=date.today().replace(day=1) + relativedelta(day=31)
    )
    display_only_summary = fields.Boolean(
        "Display Only Summary?"
    )
    category_ids = fields.Many2many(
        "product.category",
        string="Categories"
    )

    def calculate_validation_lines(self):
        move_domain = [
            ('state', '=', 'done'),
            ('company_id', 'in', [False, self.company_id.id] + self.env.companies.ids),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        location_ids = self.location_id.ids
        if self.warehouse_ids:
            for warehouse in self.warehouse_ids:
                parent_location_id = self.env['stock.location'].search([
                    ('name', '=', warehouse.code),
                    ('company_id', 'in', [False, self.company_id.id] + self.env.companies.ids),
                ])
                location_ids += self.env['stock.location'].search([
                    ('location_id', '=', parent_location_id.id),
                    ('company_id', 'in', [False, self.company_id.id] + self.env.companies.ids),
                    ('usage', '=', 'internal')
                ]).ids
        if len(location_ids) != 0:
            move_domain = expression.AND([
                move_domain,
                ['|', ('location_id', 'in', location_ids), ('location_dest_id', 'in', location_ids)]
            ])
        product_domain = [
            ('type', '=', 'product'),
            ('company_id', 'in', [False, self.company_id.id] + self.env.companies.ids)
        ]
        if self.category_ids:
            product_domain.append(('categ_id', 'in', self.category_ids.ids))
        # We pass `to_date` in the context so that `qty_available` will be computed across moves until date
        # In that way the ending quantity will be product.qty_available
        context = dict(self.env.context, to_date=self.date_to)
        product_ids = self.env['product.product'].with_context(context).search(product_domain)
        stock_move_ids = self.env['stock.move'].search(move_domain)
        lines = []
        for product in product_ids:
            product_move_ids = stock_move_ids.filtered(lambda move: move.product_id == product)
            sale_qty = internal_qty = positive_adjustment_qty = negative_adjustment_qty = received_qty = 0
            for stock_move in product_move_ids:
                # Convert the stock move quantity to product default unit of measure
                qty = stock_move.product_uom._compute_quantity(
                    stock_move.product_qty,
                    product.uom_id
                )
                if stock_move.location_id.usage == 'inventory' and stock_move.location_dest_id.usage == 'internal':
                    positive_adjustment_qty += qty
                elif stock_move.location_id.usage == 'internal' and stock_move.location_dest_id.usage == 'inventory':
                    negative_adjustment_qty -= qty
                elif stock_move.location_id.usage == 'internal' and stock_move.location_dest_id.usage == 'internal':
                    internal_qty += qty
                elif stock_move.location_id.usage == 'internal' and stock_move.location_dest_id.usage == 'customer':
                    sale_qty += qty
                elif stock_move.location_id.usage == 'supplier' and stock_move.location_dest_id.usage == 'internal':
                    received_qty += qty
            ending_qty = product.qty_available
            # We research the same product again with date_from as context to_date parameter
            # In that way the beginning quantity will be product.qty_available
            beginning_qty = self.env['product.product'].with_context(
                dict(self.env.context, to_date=self.date_from)
            ).browse(product.id).qty_available

            # In odoo 13 product.price.history model is not used any more.
            # The stock valuation history is represented by a new model named stock.valuation.layer
            valuation_layer_ids = self.env['stock.valuation.layer'].search([
                ('product_id', '=', product.id),
                ('company_id', 'in', [False, self.company_id.id] + self.env.companies.ids),
                ('create_date', '<=', self.date_to),
            ])
            qty_sum = sum(valuation_layer_ids.mapped('quantity'))
            value_sum = sum(valuation_layer_ids.mapped('value'))
            cost = (value_sum / qty_sum) if qty_sum != 0 else 0
            record = {
                'beginning_qty': beginning_qty,
                'product_id': product.id,
                'received_qty': received_qty,
                'positive_adjustment_qty': positive_adjustment_qty,
                'negative_adjustment_qty': negative_adjustment_qty,
                'internal_qty': internal_qty,
                'sale_qty': -sale_qty,
                'cost': cost,
                'ending_qty': ending_qty,
                'total_value': abs(ending_qty) * cost,
                'company_id': self.company_id.id
            }
            lines.append(record)
        return lines

    def get_data(self):
        return {
            'lines': self.calculate_validation_lines(),
            'warehouses': "All" if not self.warehouse_ids else "\t".join(self.warehouse_ids.mapped('name')),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'display_only_summary': self.display_only_summary,
            'all_categories': self.env['product.category'].search([]).mapped('id'),
            'company_ids': self.company_id.id or self.env.user.company_ids.ids
        }

    def action_confirm(self):
        return self.env.ref('stock_balance.stock_valuation_pdf_report').report_action([], data=self.get_data())
