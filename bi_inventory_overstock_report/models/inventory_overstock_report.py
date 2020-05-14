# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
import logging
_logger = logging.getLogger(__name__)

import io
from datetime import date,timedelta


try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')

try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class InventoryOverstockReport(models.TransientModel):
    _name = 'inventory.overstock'
    _description = "Inventory Overstock Report"
    
    past_sale_dur_days = fields.Integer(string='Last Sale Duration(Days)',required=True, default=30)
    adv_stock_dur_days = fields.Integer(string='Advance Stock Duration(Days)', required=True, default=30)
    product_ids = fields.Many2many('product.product',string='Products')
    warehouse_ids = fields.Many2many('stock.warehouse',string='Warehouse')


    def all_products_all_warehouse(self):
        quants_prd_list = []
        warehouse_obj = self.warehouse_ids.search([])
        if warehouse_obj:
            for each in warehouse_obj:
                for quant in each.lot_stock_id.quant_ids:
                    if quant.location_id.id == each.lot_stock_id.id:
                        quants_prd_list.append(quant.product_id.id)
        product_obj = self.product_ids.search([('id','in',quants_prd_list)])
        return product_obj

    def specific_warehouse(self):
        quants_prd_list = []
        if self.warehouse_ids:
            for each in self.warehouse_ids:
                for quant in each.lot_stock_id.quant_ids:
                    if quant.location_id.id == each.lot_stock_id.id:
                        quants_prd_list.append(quant.product_id.id)
        product_obj = self.product_ids.search([('id','in',quants_prd_list)])
        return product_obj


    def specific_products_in_all_warehouse(self):
        quants_prd_list = []
        product_list = []
        warehouse_obj = self.warehouse_ids.search([])
        if warehouse_obj:
            for each in warehouse_obj:
                for quant in each.lot_stock_id.quant_ids:
                    if quant.location_id.id == each.lot_stock_id.id:
                        quants_prd_list.append(quant.product_id.id)
        if self.product_ids:
            for product in self.product_ids:
                product_list.append(product.id)

        product_obj = self.product_ids.search([('id','in',quants_prd_list),('id','in',product_list)])
        return product_obj


    def specific_products_specific_warehouse(self):
        prd_list = []
        quant_prd_list = []
        if self.warehouse_ids and self.product_ids:
            for prd in self.product_ids:
                prd_list.append(prd.id)
            for ware in self.warehouse_ids:
                for quant in ware.lot_stock_id.quant_ids:
                    if quant.location_id.id == ware.lot_stock_id.id:
                        quant_prd_list.append(quant.product_id.id)
        product_obj = self.product_ids.search([('id','in',prd_list),('id','in',quant_prd_list)])
        return product_obj

    def get_warehouse(self):
        if self.warehouse_ids:
            return self.warehouse_ids
        else:
            ware_obj = self.env['stock.warehouse'].search([])
            return ware_obj


    def get_ware_list(self):
        ware_obj_list = []
        for ware in self.get_warehouse():
            ware_obj_list.append(ware.id)
        return ware_obj_list


    def get_pdf_report(self):
        if self.product_ids:
            report_data_list =[]
            for each in self.specific_products_in_all_warehouse():
                report_data_list.append(each.id)
        if self.warehouse_ids:
            report_data_list =[]
            for each in self.specific_warehouse():
                report_data_list.append(each.id)
        if self.warehouse_ids and self.product_ids:
            report_data_list =[]
            for sp_prd_ware in self.specific_products_specific_warehouse():
                report_data_list.append(sp_prd_ware.id)
        if not self.product_ids and not self.warehouse_ids:
            report_data_list =[]
            for each in self.all_products_all_warehouse():
                report_data_list.append(each.id)
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                    'past_sale_dur_days': self.past_sale_dur_days,
                    'adv_stock_dur_days': self.adv_stock_dur_days,
                    'report_data_list': report_data_list,
                    'ware_obj_list':self.get_ware_list(),
                    }
                }
        return self.env.ref('bi_inventory_overstock_report.inventory_report').report_action(self, data=data)


    def generate_xls_report(self):
        current_date = fields.datetime.now() + timedelta(days=1)
        past_date = fields.datetime.now() - timedelta(days=self.past_sale_dur_days)
        advance_date = fields.datetime.now() + timedelta(days=self.adv_stock_dur_days)

        if self.product_ids:
            get_report_data = self.specific_products_in_all_warehouse()
        if self.warehouse_ids:
            get_report_data = self.specific_warehouse()
        if self.warehouse_ids and self.product_ids:
            get_report_data = self.specific_products_specific_warehouse()
        if not self.product_ids and not self.warehouse_ids:
            get_report_data = self.all_products_all_warehouse()
        
        filename = 'Inventory Overstock Report.xls'
        workbook = xlwt.Workbook()
        stylePC = xlwt.XFStyle()
        alignment = xlwt.Alignment()
        alignment.horz = xlwt.Alignment.HORZ_CENTER
        fontP = xlwt.Font()
        fontP.bold = True
        fontP.height = 200
        stylePC.font = fontP
        stylePC.num_format_str = '@'
        stylePC.alignment = alignment
        style_title = xlwt.easyxf("font:height 300; font: name Liberation Sans, bold on,color black; align: horiz center;pattern: pattern solid, fore_colour aqua;")
        style_table_header = xlwt.easyxf("font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center")
        style = xlwt.easyxf("font:height 200; font: name Liberation Sans,color black;")
        style_header = xlwt.easyxf("font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center;pattern: pattern solid, fore_colour silver_ega;")
        worksheet = workbook.add_sheet('Sheet 1')
        worksheet.write(3, 0, 'Report Date', style_table_header)
        worksheet.write(4, 0, str(date.today()))
        worksheet.write_merge(0, 1, 0, 14, "Inventory Overstock Report",style_title)
        worksheet.write_merge(2, 3, 1, 3,"Last Sale Duration: "+str(self.past_sale_dur_days)+" Days",  style=style_table_header)
        worksheet.write_merge(2, 3, 4, 6,"Advance Stock Duration: "+str(self.adv_stock_dur_days)+" Days", style=style_table_header)
        worksheet.write(6, 0, 'Product SKU', style_header)
        worksheet.write(6, 1, 'Current Stock', style_header)
        worksheet.write(6, 2, 'Incoming Stock', style_header)
        worksheet.write(6, 3, 'Outgoing Stock', style_header)
        worksheet.write(6, 4, 'Net On Hand Stock', style_header)
        worksheet.write(6, 5, 'Sales In Last Days', style_header)
        worksheet.write(6, 6, 'Average Daily Sale', style_header)
        worksheet.write(6, 7, 'Recent Purchase Date', style_header)
        worksheet.write(6, 8, 'Recent Purchase Qty', style_header)
        worksheet.write(6, 9, 'Recent Purchase Cost', style_header)
        worksheet.write(6, 10, 'Vendor Name', style_header)
        worksheet.write(6, 11, 'Stock Coverage', style_header)
        worksheet.write(6, 12, 'Expected Stock', style_header)
        worksheet.write(6, 13, 'Overstock Quantity', style_header)
        worksheet.write(6, 14, 'Overstock Value', style_header)
        ware_obj_data = self.get_warehouse()
        if ware_obj_data:
            worksheet.write_merge(2, 3, 7, 7,"Warehouse",style_table_header)
            c = 8
            for wl in ware_obj_data:
                worksheet.write(3, c, wl.name)
                c+=1
        row = 7
        count = 1
        col = 0
        total_overstock_qty = 0
        total_overstock_val = 0
        
        if get_report_data:
            for product in get_report_data:
                
                count +=1
                sale_obj = self.env['sale.order'].search([('state', 'in', ['sale', 'done']),('date_order','>=',past_date),('order_line.product_id','=',product.id)])
                purchase_obj = self.env['purchase.order'].search([('state','in',['purchase','done']),('date_order','<=',advance_date),('order_line.product_id','=',product.id)])
                picking_obj = self.env['stock.picking'].search([('state', 'in', ['done']),('date_done','>=',past_date)])
                product_reference =  str(product.name) +" "+ "["+ str(product.default_code) +"]" if product.default_code else ''

                worksheet.write(row, col, product_reference, style)
                worksheet.write(row, col+1, product.qty_available, style)
                worksheet.write(row, col+2, product.incoming_qty, style)
                worksheet.write(row, col+3, product.outgoing_qty, style)
                if picking_obj:
                    on_hand_qty = pick_done_qty = 0
                    for pick in picking_obj:
                        if any(product.id == pro.product_id.id for pro in pick.move_ids_without_package):
                            for p_line in pick.move_ids_without_package:
                                if p_line.product_id.id == product.id:
                                    pick_done_qty = pick_done_qty + p_line.product_uom_qty
                    on_hand_qty = (product.qty_available - pick_done_qty)
                    worksheet.write(row, col+4, on_hand_qty, style)
                else:
                    on_hand_qty = product.qty_available
                    worksheet.write(row, col+4, on_hand_qty, style)
                worksheet.write(row, col+5, product.sales_count ,style)
                
                if self.past_sale_dur_days and product.sales_count:
                    avg_daily_sale = (product.sales_count/self.past_sale_dur_days)
                    worksheet.write(row, col+6, round(avg_daily_sale,2), style)

                total_pur_stock = recent_pur_cost = recent_pur_qty =  0
                
                if purchase_obj:
                    for pur in purchase_obj[0]:
                        for pur_line in pur.order_line:
                            if product.id == pur_line.product_id.id:
                                recent_pur_qty = recent_pur_qty + pur_line.product_qty
                                recent_pur_cost = recent_pur_cost + pur_line.price_subtotal

                    for purchase in purchase_obj:
                        for p_line in purchase.order_line:
                            if product.id == p_line.product_id.id:
                                total_pur_stock = total_pur_stock + p_line.product_qty

                    worksheet.write(row, col+7, purchase_obj[0].date_order.strftime('%Y-%m-%d') ,style)
                    worksheet.write(row, col+8, recent_pur_qty , style)
                    worksheet.write(row, col+9, recent_pur_cost ,style)
                    worksheet.write(row, col+10, purchase_obj[0].partner_id.name ,style)
                
                
                
                total_sale_stock = 0
                if sale_obj:
                    for sale in sale_obj:
                        for o_line in sale.order_line:
                            if product.id == o_line.product_id.id:
                                total_sale_stock = total_sale_stock + o_line.product_uom_qty
                
                
                worksheet.write(row, col+11, (total_pur_stock + total_sale_stock), style)
                expected_stock = ((total_pur_stock + product.qty_available) - total_sale_stock)
                overstock_qty = on_hand_qty - expected_stock
                worksheet.write(row, col+12, expected_stock ,style)
                worksheet.write(row, col+13, overstock_qty, style)
                overstock_val = (overstock_qty * recent_pur_cost)
                total_overstock_qty = total_overstock_qty + overstock_qty
                total_overstock_val = total_overstock_val + overstock_val
                worksheet.write(row, col+14, overstock_val, style)
                count += 1
                row += 1
        worksheet.write_merge(count+7, count+8, 1, 4,"Total Overstock Quantity : "+str(total_overstock_qty),  style=style_table_header)
        worksheet.write_merge(count+7, count+8, 5, 7,"Total Overstock Value : "+str(total_overstock_val), style=style_table_header)
        worksheet.write_merge(count+7, count+8, 8, 10,"Total Duration : "+str(self.past_sale_dur_days + self.adv_stock_dur_days), style=style_table_header)
        worksheet.write_merge(count+7, count+8, 11, 13,"Number Of Warehouse : "+str(len(self.get_ware_list())), style=style_table_header)
        fp = io.BytesIO()
        workbook.save(fp)

        export_id = self.env['stock.excel.report'].create({'excel_file': base64.encodestring(fp.getvalue()), 'file_name': filename})
        res = {'view_mode': 'form',
               'res_id': export_id.id,
               'name': 'Inventory Overstock Report',
               'res_model': 'stock.excel.report',
               'view_type': 'form',
               'type': 'ir.actions.act_window',
               'target':'new'
                }
        return res

class stock_excel_report(models.TransientModel):
    _name = 'stock.excel.report'
    _description = "Stock Excel Report"

    excel_file = fields.Binary('Download Excel File', readonly =True)
    file_name = fields.Char('File', readonly=True)