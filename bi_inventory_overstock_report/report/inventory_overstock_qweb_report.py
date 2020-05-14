# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from datetime import date,timedelta

class ReportInventoryCoverage(models.AbstractModel):
    _name = 'report.bi_inventory_overstock_report.template_report'
    _description = "Inventory Overstock Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        past_days = data['form']['past_sale_dur_days']
        advance_days = data['form']['adv_stock_dur_days'] 
        report_data_list =  data['form']['report_data_list']
        ware_obj_list = data['form']['ware_obj_list']
        past_date = fields.datetime.now() - timedelta(days=int(past_days))
        advance_date = fields.datetime.now() + timedelta(days=int(advance_days))
        docs = []
        product_obj = self.env['product.product']
        ware_obj = self.env['stock.warehouse']
        ware_list = []
        for ware in ware_obj_list:
            ware_id = ware_obj.browse(ware)
            ware_list.append({'name':ware_id.name})
        total_overstock_qty = 0
        total_overstock_val = 0
        for each in report_data_list:
            product_id = product_obj.browse(each)
            sale_obj = self.env['sale.order'].search([('state', 'in', ['sale', 'done']),('date_order','>=',past_date),('order_line.product_id','=',product_id.id)])
            purchase_obj = self.env['purchase.order'].search([('state','in',['purchase','done']),('date_order','<=',advance_date),('order_line.product_id','=',product_id.id)])
            picking_obj = self.env['stock.picking'].search([('state', 'in', ['done']),('date_done','>=',past_date)])
            if picking_obj:
                on_hand_qty = pick_done_qty = 0
                for pick in picking_obj:
                    if any(product_id.id == pro.product_id.id for pro in pick.move_ids_without_package):
                        for p_line in pick.move_ids_without_package:
                            if p_line.product_id.id == product_id.id:
                                pick_done_qty = pick_done_qty + p_line.product_uom_qty
                                on_hand_qty = (product_id.qty_available - pick_done_qty)
            else:
                on_hand_qty = product_id.qty_available
            avg_daily_sale = 0
            if past_days and product_id.sales_count:
                avg_daily_sale = (product_id.sales_count/int(past_days))
            total_pur_stock = 0
            recent_pur_qty =  0
            recent_pur_cost = 0
            recent_pur_date = ""
            vendor = ""
            recent_pur_cost = 0
            if purchase_obj:
                for pur in purchase_obj[0]:
                    for pur_line in pur.order_line:
                        if product_id.id == pur_line.product_id.id:
                            recent_pur_qty = recent_pur_qty + pur_line.product_qty
                            recent_pur_cost = recent_pur_cost + pur_line.price_subtotal
                            recent_pur_date = purchase_obj[0].date_order.strftime('%Y-%m-%d')
                            vendor = purchase_obj[0].partner_id.name
                for purchase in purchase_obj:
                    for p_line in purchase.order_line:
                        if product_id.id == p_line.product_id.id:
                            total_pur_stock = total_pur_stock + p_line.product_qty
            total_sale_stock = 0
            if sale_obj:
                for sale in sale_obj:
                    for o_line in sale.order_line:
                        if product_id.id == o_line.product_id.id:
                            total_sale_stock = total_sale_stock + o_line.product_uom_qty
            expected_stock = ((total_pur_stock + product_id.qty_available) - total_sale_stock)
            overstock_qty = on_hand_qty - expected_stock
            overstock_val = (overstock_qty * recent_pur_cost)
            total_overstock_qty = total_overstock_qty + overstock_qty
            total_overstock_val = total_overstock_val + overstock_val
            product_reference =  str(product_id.name) +" "+ "["+ str(product_id.default_code)+"]"
            docs.append({
                'product_reference':product_reference,
                'current_stock':product_id.qty_available,
                'incoming_qty':product_id.incoming_qty,
                'outgoing_qty':product_id.outgoing_qty,
                'on_hand_qty':on_hand_qty,
                'forcasted':product_id.virtual_available,
                'last_sale':product_id.sales_count,
                'avg_daily_sale':round(avg_daily_sale,2),
                'recent_pur_date':recent_pur_date,
                'recent_pur_qty':recent_pur_qty,
                'recent_pur_cost':recent_pur_cost,
                'vendor':vendor,
                'expected_stock':expected_stock,
                'overstock_qty':overstock_qty,
                'overstock_val':overstock_val,
                'stock_coverage':(int(total_pur_stock)+int(total_sale_stock))
                })
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'report_date':date.today(),
            'past_days':int(past_days),
            'advance_days':int(advance_days),
            'ware_list':ware_list,
            'total_warehouse':len(ware_obj_list),
            'total_overstock_qty':total_overstock_qty,
            'total_overstock_val':total_overstock_val,
            'docs': docs,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: