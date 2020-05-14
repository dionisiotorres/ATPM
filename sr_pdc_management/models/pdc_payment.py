# -*- coding: utf-8 -*-
##############################################################################
#
#    This module uses OpenERP, Open Source Management Solution Framework.
#    Copyright (C) 2017-Today Sitaram
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from dateutil.relativedelta import *
import datetime
from datetime import timedelta

MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    'out_invoice': 1,
    'in_refund': -1,
    'in_invoice': -1,
    'out_refund': 1,
}


# class ResConfigSettings(models.TransientModel):
#     _inherit = 'res.config.settings'
#
#     customer_pdc_payment_account = fields.Many2one('account.account', 'PDC Payment Account for Customer')
#     vendor_pdc_payment_account = fields.Many2one('account.account', 'PDC Payment Account for Vendors/Suppliers')
#
#     @api.model
#     def get_values(self):
#         res = super(ResConfigSettings, self).get_values()
#
#         res['customer_pdc_payment_account'] = int(
#             self.env['ir.config_parameter'].sudo().get_param('customer_pdc_payment_account', default=0))
#         res['vendor_pdc_payment_account'] = int(
#             self.env['ir.config_parameter'].sudo().get_param('vendor_pdc_payment_account', default=0))
#
#         return res
#
#     @api.model
#     def set_values(self):
#         self.env['ir.config_parameter'].sudo().set_param('customer_pdc_payment_account',
#                                                          self.customer_pdc_payment_account.id)
#         self.env['ir.config_parameter'].sudo().set_param('vendor_pdc_payment_account',
#                                                          self.vendor_pdc_payment_account.id)
#
#         super(ResConfigSettings, self).set_values()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    pdc_id = fields.Many2one('sr.pdc.payment', 'Post Dated Cheques')


class AccountInvoice(models.Model):
    _inherit = "account.move"

    is_pdc_invoice = fields.Boolean('PDC')
    pdc_id = fields.Many2one('sr.pdc.payment', 'Post Dated Cheques')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self._context.get('default_type', False) == 'out_invoice':
            return {'domain': {'partner_id': [('customer_rank', '>', 0)]}}
        elif self._context.get('default_type', False) == 'in_invoice':
            return {'domain': {'partner_id': [('supplier_rank', '>', 0)]}}

    def name_get(self):
        name_array = []
        for record in self:
            if record.name != '/':
                name_array.append(
                    (record.id, record.name + ' ' + '[' + '{:.2f}'.format(record.amount_residual) + ']'))
            else:
                name_array.append((record.id, 'Draft Invoice (*{})'.format(record.id)))
        return name_array

    @api.model
    def _get_default_invoice_date(self):
        return fields.Date.today() if self._context.get('default_type', 'entry') in (
            'in_invoice', 'in_refund', 'in_receipt') else False

    invoice_date = fields.Date(string='Invoice/Bill Date', readonly=True, index=True, copy=False,
                               states={'draft': [('readonly', True)]},
                               default=_get_default_invoice_date)

    @api.model
    def default_get(self, fields_list):
        res = super(AccountInvoice, self).default_get(fields_list)
        if res.get('invoice_date') == False:
            res.update({'invoice_date': datetime.date.today()})
        return res

    @api.depends(
        'state', 'currency_id', 'invoice_line_ids.price_subtotal',
        'move_id.line_ids.amount_residual',
        'move_id.line_ids.currency_id')
    def _compute_residual(self):
        residual = 0.0
        residual_company_signed = 0.0
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        for line in self.sudo().move_id.line_ids:
            if line.account_id == self.account_id:
                residual_company_signed += line.amount_residual
                if line.currency_id == self.currency_id:
                    residual += line.amount_residual_currency if line.currency_id else line.amount_residual
                else:
                    from_currency = line.currency_id or line.company_id.currency_id
                    residual += from_currency._convert(line.amount_residual, self.currency_id, line.company_id,
                                                       line.date or fields.Date.today())
        if self._context.get('pdc'):
            residual = 0
        self.residual_company_signed = abs(residual_company_signed) * sign
        self.residual_signed = abs(residual) * sign
        self.residual = abs(residual)
        digits_rounding_precision = self.currency_id.rounding
        if float_is_zero(self.residual, precision_rounding=digits_rounding_precision):
            self.reconciled = True
        else:
            self.reconciled = False

    # When you click on add in invoice then this method called
    def assign_outstanding_credit(self, credit_aml_id):
        self.ensure_one()
        credit_aml = self.env['account.move.line'].browse(credit_aml_id)
        if not credit_aml.currency_id and self.currency_id != self.company_id.currency_id:
            amount_currency = self.company_id.currency_id._convert(credit_aml.balance, self.currency_id,
                                                                   self.company_id,
                                                                   credit_aml.date or fields.Date.today())
            credit_aml.with_context(allow_amount_currency=True, check_move_validity=False).write({
                'amount_currency': amount_currency,
                'currency_id': self.currency_id.id})
        if credit_aml.payment_id:
            credit_aml.payment_id.write({'invoice_ids': [(4, self.id, None)]})
        if credit_aml.pdc_id:
            credit_aml.pdc_id.write({'invoice_ids': [(4, self.id, None)]})
        return self.register_payment(credit_aml)


class PdcPayment(models.Model):
    _name = "sr.pdc.payment"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    invoice_ids = fields.Many2many('account.move', 'account_invoice_pdc_rel', 'pdc_id', 'invoice_id',
                                   string="Invoices", copy=False, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, copy=False)
    state = fields.Selection(
        [('draft', 'Draft'), ('register', 'Registered'), ('return', 'Returned'), ('deposit', 'Deposited'),
         ('bounce', 'Bounced'), ('done', 'Done'), ('cancel', 'Cancelled')], readonly=True, default='draft', copy=False,
        string="Status")
    journal_id = fields.Many2one('account.journal', string='Payment Journal', required=True,
                                 domain=[('type', 'in', ['bank'])])
    # company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', readonly=True)
    # 6/4/2020 JIQ
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    amount = fields.Monetary(string='Payment Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True, copy=False)
    due_date = fields.Date(string='Due Date', default=fields.Date.context_today, required=True, copy=False)
    # Muhammad Jawaid Iqbal
    # communication = fields.Char(string='Memo')
    communication = fields.Many2many('account.move', string='Memo')
    cheque_ref = fields.Char('Cheque No.')
    agent = fields.Char('Agent / Person')
    bank = fields.Many2one('res.bank', string="Cheque Bank")
    name = fields.Char('Name')
    employee_id = fields.Many2one('hr.employee', 'Receiver')
    receipt_no = fields.Integer('Receipt No.')
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    required=True)
    customer_pdc_payment_account = fields.Many2one('account.account', 'PDC Payment Account for Customer')
    vendor_pdc_payment_account = fields.Many2one('account.account', 'PDC Payment Account for Vendors/Suppliers')
    supplier_rank = fields.Integer(related='partner_id.supplier_rank')
    customer_rank = fields.Integer(related='partner_id.customer_rank')
    attchment_ids = fields.One2many('ir.attachment', 'payment_id', string='Create Attachment')
    attachment_count = fields.Integer(compute='_compute_attachment_count', string='Attachment')
    journal_items_count = fields.Integer(compute='_compute_journal_items_count', string='Journal Items')
    journal_entry_count = fields.Integer(compute='_compute_journal_entry_count', string='Journal Entries')

    def _compute_attachment_count(self):
        self.env.cr.execute(
            """select count(id) from ir_attachment where payment_id = {}""".format(self.id))
        rs = self.env.cr.dictfetchone()
        self.attachment_count = rs['count']

    def _compute_journal_items_count(self):
        self.env.cr.execute(
            """select count(id) from account_move_line where partner_id = {} and pdc_id = {}""".format(
                self.partner_id.id, self.id))
        rs = self.env.cr.dictfetchone()
        self.journal_items_count = rs['count']

    def _compute_journal_entry_count(self):
        self.env.cr.execute(
            """select count(id) from account_move where pdc_id = {} and type = 'entry'""".format(self.id))
        rs = self.env.cr.dictfetchone()
        self.journal_entry_count = rs['count']

    def attachment_on_account_cheque(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Attachment.Details',
            'res_model': 'ir.attachment',
            'view_mode': 'tree,form',
            'domain': [('payment_id', '=', self.id)]
        }

    def action_view_jornal_items(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Items',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.partner_id.id), ('pdc_id', '=', self.id)]
        }

    def action_view_jornal_entry(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Entries',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('pdc_id', '=', self.id), ('type', '=', 'entry')]
        }

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.customer_pdc_payment_account = self.partner_id.customer_pdc_payment_account.id
            self.vendor_pdc_payment_account = self.partner_id.vendor_pdc_payment_account.id
            invoices = self.partner_id.unpaid_invoices
            if invoices:
                return {'domain': {'communication': [('id', 'in', invoices.ids)]}}

    def get_amount_in_words(self, amount_total):
        amount_in_words = self.company_id.currency_id.amount_to_text(amount_total)
        return amount_in_words.upper() + ' ONLY'

    def get_default_date_format(self, payment_date):
        lang_id = self.env['res.lang'].search([('code', '=', self.env.context.get('lang', 'en_US'))])
        if payment_date:
            return datetime.datetime.strptime(str(payment_date), '%Y-%m-%d').strftime(lang_id.date_format)

    def _cron_send_payment_history(self):
        payments = self.search([('due_date', '=', datetime.date.today() + timedelta(days=1))])
        if payments:
            self.env.ref('sr_pdc_management.email_template_reminder_payment').send_mail(payments.ids[0])

    def get_payment_history(self):
        payments = self.search([('due_date', '=', datetime.date.today() + timedelta(days=1))])
        if payments:
            return payments

    def get_user(self):
        return self.env.user.name

    def get_currency_symbol(self):
        if self.env['res.company']._company_default_get():
            return self.env['res.company']._company_default_get().currency_id.symbol

    # @api.onchange('payment_type')
    # def _onchange_payment_type(self):
    #     self.ensure_one()
    #     # Set partner_id domain
    #     if self.payment_type == 'inbound':
    #         return {'domain': {'partner_id': [('customer_rank', '=', 1)]}}
    #     else:
    #         return {'domain': {'partner_id': [('supplier_rank', '=', 1)]}}

    @api.onchange('journal_id')
    def _default_currency(self):
        if self.journal_id:
            journal = self.journal_id
            currency_id = journal.currency_id or journal.company_id.currency_id or self.env.user.company_id.currency_id
            self.currency_id = currency_id.id
        else:
            self.currency_id = False

    @api.model
    def default_get(self, fields):
        rec = super(PdcPayment, self).default_get(fields)
        context = dict(self._context or {})

        # Checks on received invoice records
        invoices = self.env['account.move'].browse(context.get('active_ids'))
        if len(invoices.mapped('partner_id')) > 1:
            raise UserError(_("You must have one partner for both the invoices"))
        # if any(invoice.state != 'open' for invoice in invoices):
        #     raise UserError(_("You can only register check for open invoices"))

        total_amount = sum(inv.amount_residual * MAP_INVOICE_TYPE_PAYMENT_SIGN[inv.type] for inv in invoices)
        # Muhammad Jawaid Iqbal
        # communication = ' '.join([ref for ref in invoices.mapped('invoice_payment_ref') if ref])
        if invoices:
            if invoices.mapped('type')[0] == 'in_invoice':
                payment_type = 'outbound'
            else:
                payment_type = 'inbound'
        else:
            payment_type = 'inbound'
        rec.update({
            'payment_type': payment_type,
            'name': invoices.mapped('name'),
            'amount': abs(total_amount),
            'currency_id': invoices[0].currency_id.id if invoices else False,
            'partner_id': invoices[0].commercial_partner_id.id if invoices else False,
            'customer_pdc_payment_account': invoices[
                0].commercial_partner_id.customer_pdc_payment_account.id if invoices else False,
            'vendor_pdc_payment_account': invoices[
                0].commercial_partner_id.vendor_pdc_payment_account.id if invoices else False,
            'communication': [(6, 0, self._context.get('active_ids'))],
        })
        return rec

    def get_credit_entry(self, partner_id, move, credit, debit, amount_currency, journal_id, name,
                         account_id, currency_id, payment_date):
        return {
            'partner_id': partner_id.id,
            # 'invoice_id': invoice_ids.id if len(invoice_ids) == 1 else False,
            'move_id': move.id,
            'debit': debit,
            'credit': credit,
            'amount_currency': amount_currency or False,
            'payment_id': False,
            'journal_id': journal_id.id,
            'name': name,
            'account_id': account_id,
            'currency_id': currency_id if currency_id != self.company_id.currency_id.id else False,
            'date_maturity': payment_date,
            'exclude_from_invoice_tab': True,
            'pdc_id': self.id
        }

    def get_debit_entry(self, partner_id, move, credit, debit, amount_currency, journal_id, name,
                        account_id, currency_id):
        return {
            'partner_id': partner_id.id,
            # 'invoice_id': invoice_ids.id if len(invoice_ids) == 1 else False,
            'move_id': move.id,
            'debit': debit,
            'credit': credit,
            'amount_currency': amount_currency or False,
            'payment_id': False,
            'journal_id': journal_id.id,
            'name': name,
            'account_id': account_id,
            'currency_id': currency_id if currency_id != self.company_id.currency_id.id else False,
            'exclude_from_invoice_tab': True,
            'pdc_id': self.id
        }

    def cancel(self):
        self.state = 'cancel'

    def register(self):
        if self.customer_pdc_payment_account or self.vendor_pdc_payment_account:
            all_move_vals = []
            inv = self.env['account.move'].browse(self._context.get('active_ids')) or self.invoice_ids
            if inv:
                inv.write({'is_pdc_invoice': True, 'pdc_id': self.id})
            self.state = 'register'
            if self.customer_rank > 0:
                self.name = self.env['ir.sequence'].next_by_code('pdc.payment')
                account_id = self.partner_id.property_account_receivable_id
                balance = -self.amount
            else:
                self.name = self.env['ir.sequence'].next_by_code('pdc.payment.vendor')
                account_id = self.partner_id.property_account_payable_id
                balance = self.amount
            move_vals = {
                'date': self.payment_date,
                'ref': ','.join(self.communication.mapped('name')),
                'journal_id': self.journal_id.id,
                'currency_id': self.journal_id.currency_id.id or self.company_id.currency_id.id,
                'partner_id': self.partner_id.id,
                'line_ids': [
                    # Receivable / Payable / Transfer line.
                    (0, 0, {
                        'name': '{} Payment: '.format('Customer' if self.customer_rank > 0 else 'Vendor') + ','.join(
                            self.communication.mapped('name')),
                        'amount_currency': 0.0 + 0.0,
                        'currency_id': False,
                        'debit': balance + 0.0 > 0.0 and balance + 0.0 or 0.0,
                        'credit': balance + 0.0 < 0.0 and -balance - 0.0 or 0.0,
                        'date_maturity': self.payment_date,
                        'partner_id': self.partner_id.id,
                        'account_id': account_id.id,
                        'pdc_id': self.id,
                    }),
                    # Liquidity line .
                    (0, 0, {
                        'name': self.name,
                        'amount_currency': -0.0,
                        'currency_id': False,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'date_maturity': self.payment_date,
                        'partner_id': self.partner_id.id,
                        'account_id': self.partner_id.customer_pdc_payment_account.id if self.customer_rank > 0 else self.partner_id.vendor_pdc_payment_account.id,
                        'pdc_id': self.id,
                    }),
                ],
            }
            all_move_vals.append(move_vals)
            moves = self.env['account.move'].with_context(default_type='entry').create(all_move_vals)
            moves.filtered(lambda move: move.journal_id.post_at != 'bank_rec').post()
            if self.payment_type in ('inbound', 'outbound'):
                if inv:
                    (moves[0] + inv).line_ids.filtered(
                        lambda line: not line.reconciled and line.account_id == account_id).reconcile()
        else:
            raise UserError(_("Configuration Error: Please define account for the PDC payment."))
        return

    def return_cheque(self):
        self.state = 'return'
        return

    def deposit(self):
        # if self.customer_pdc_payment_account or self.vendor_pdc_payment_account:
        #     # JIQ 20/4/2020
        #     inv = self.env['account.move'].browse(self._context.get('active_ids'))
        #     # JIQ 20/4/2020
        #     aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        #     if inv:
        #         inv.invoice_payment_state = 'paid'
        #         custom_currency_id = inv.currency_id
        #         company_currency_id = inv.company_id.currency_id
        #         account_id = inv.account_id.id
        #     else:
        #         custom_currency_id = self.currency_id
        #         company_currency_id = self.env.user.company_id.currency_id
        #         if self.payment_type == 'inbound':
        #             account_id = self.partner_id.property_account_receivable_id.id
        #         else:
        #             account_id = self.partner_id.property_account_payable_id.id
        #     amount_currency, debit, credit = list(
        #         aml_obj._get_fields_onchange_subtotal_model(self.amount, 'entry', self.currency_id,
        #                                                     self.env.user.company_id, self.payment_date).values())
        #     move = self.env['account.move'].create(self._get_move_vals())
        #     #################    Credit Entry  ######################
        #     name = ''
        #     if inv:
        #         name += 'PDC Payment: '
        #         for record in inv:
        #             if record.move_id:
        #                 name += record.number + ', '
        #         name = name[:len(name) - 2]
        #     if self.payment_type == 'inbound':
        #         credit_entry = self.get_credit_entry(self.partner_id, move, debit, credit, amount_currency,
        #                                              self.journal_id, name, account_id, custom_currency_id.id,
        #                                              self.payment_date)
        #     else:
        #         credit_entry = self.get_credit_entry(self.partner_id, move, debit, credit, amount_currency,
        #                                              self.journal_id, name, self.vendor_pdc_payment_account.id,
        #                                              custom_currency_id.id,
        #                                              self.payment_date)
        #     aml_obj.create(credit_entry)
        #     ################ Debit Entry #############################
        #     if self.payment_type == 'inbound':
        #         debit_entry = self.get_debit_entry(self.partner_id, move, credit, debit, amount_currency,
        #                                            self.journal_id, name, self.customer_pdc_payment_account.id,
        #                                            custom_currency_id.id)
        #     else:
        #         debit_entry = self.get_debit_entry(self.partner_id, move, credit, debit, amount_currency,
        #                                            self.journal_id, name, account_id, custom_currency_id.id)
        #     aml_obj.create(debit_entry)
        #     move.post()
        # else:
        #     raise UserError(_("Configuration Error: Please define account for the PDC payment."))
        self.state = 'deposit'
        return True

    def bounce(self):
        if self.customer_pdc_payment_account or self.vendor_pdc_payment_account:
            if self.payment_type == 'inbound':
                account_id = self.partner_id.property_account_receivable_id.id
            else:
                account_id = self.partner_id.property_account_payable_id.id
            aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
            amount_currency, debit, credit = list(
                aml_obj._get_fields_onchange_subtotal_model(self.amount, 'entry', self.currency_id,
                                                            self.env.user.company_id, self.payment_date).values())
            move = self.env['account.move'].create(self._get_move_vals())
            #################    Credit Entry  ######################
            # name = ''
            # if self.invoice_ids:
            #     name += 'PDC Payment: '
            #     for record in self.invoice_ids:
            #         if record.move_id:
            #             name += record.number + ', '
            #     name = name[:len(name) - 2]
            name = 'PDC return'
            if self.payment_type == 'inbound':
                credit_entry = self.get_credit_entry(self.partner_id, move, debit, credit,
                                                     amount_currency,
                                                     self.journal_id, name, self.customer_pdc_payment_account.id, False,
                                                     self.payment_date)
            else:
                credit_entry = self.get_credit_entry(self.partner_id, move, debit, credit,
                                                     amount_currency,
                                                     self.journal_id, name, account_id, False,
                                                     self.payment_date)
            aml_obj.create(credit_entry)
            ################ Debit Entry #############################
            if self.payment_type == 'inbound':
                debit_entry = self.get_debit_entry(self.partner_id, move, credit, debit,
                                                   amount_currency,
                                                   self.journal_id, name, account_id, False)
            else:
                debit_entry = self.get_debit_entry(self.partner_id, move, credit, debit,
                                                   amount_currency,
                                                   self.journal_id, name, self.vendor_pdc_payment_account.id, False)

            aml_obj.create(debit_entry)
            move.post()
            self.state = 'bounce'
            for record in self.invoice_ids:
                record.state = 'posted'
        else:
            raise UserError(_("Configuration Error: Please define account for the PDC payment."))
        return True

    def done(self):
        if self.customer_pdc_payment_account or self.vendor_pdc_payment_account:
            aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
            amount_currency, debit, credit = list(
                aml_obj._get_fields_onchange_subtotal_model(self.amount, 'entry', self.currency_id,
                                                            self.env.user.company_id, self.payment_date).values())

            move = self.env['account.move'].create(self._get_move_vals())
            if self.payment_type == 'inbound':
                account_id = self.journal_id.default_debit_account_id.id
            else:
                account_id = self.journal_id.default_credit_account_id.id
            #################    Credit Entry  ######################
            name = ''
            if self.invoice_ids:
                name += 'PDC Payment: '
                for record in self.invoice_ids:
                    if record:
                        name += record.name + ', '
                name = name[:len(name) - 2]
            if self.payment_type == 'inbound':
                credit_entry = self.get_credit_entry(self.partner_id, move, debit, credit,
                                                     amount_currency,
                                                     self.journal_id, name, self.customer_pdc_payment_account.id, False,
                                                     self.payment_date)
            else:
                credit_entry = self.get_credit_entry(self.partner_id, move, debit, credit,
                                                     amount_currency,
                                                     self.journal_id, name, account_id, False,
                                                     self.payment_date)
            aml_obj.create(credit_entry)
            ################ Debit Entry #############################
            if self.payment_type == 'inbound':
                debit_entry = self.get_debit_entry(self.partner_id, move, credit, debit,
                                                   amount_currency,
                                                   self.journal_id, name, account_id, False)
            else:
                debit_entry = self.get_debit_entry(self.partner_id, move, credit, debit,
                                                   amount_currency,
                                                   self.journal_id, name, self.vendor_pdc_payment_account.id, False)
            aml_obj.create(debit_entry)
            move.post()
            self.state = 'done'
        else:
            raise UserError(_("Configuration Error: Please define account for the PDC payment."))
        return True

    def _get_move_vals(self, journal=None):
        """ Return dict to create the payment move
        """
        journal = journal or self.journal_id
        return {
            'date': self.payment_date,
            'ref': ','.join(self.communication.mapped('name')) or '',
            'company_id': self.company_id.id,
            'journal_id': journal.id,
            'pdc_id': self.id
        }


class PdcReportWizard(models.TransientModel):
    _name = 'pdc.report.wizard'

    from_date = fields.Date(string="Start Date")
    to_date = fields.Date(string="End Date")
    partner_ids = fields.Many2many('res.partner', string='Partner')
    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')])
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type')
    state = fields.Selection(
        [('register', 'Registered'), ('return', 'Returned'), ('deposit', 'Deposited'),
         ('bounce', 'Bounced'), ('done', 'Done'), ('cancel', 'Cancelled')], string="Status")

    def get_state_label(self, state):
        return dict(self.env['sr.pdc.payment'].fields_get(['state'])['state']['selection'])[state]

    def get_default_date_format(self, payment_date):
        lang_id = self.env['res.lang'].search([('code', '=', self.env.context.get('lang', 'en_US'))])
        if payment_date:
            return datetime.datetime.strptime(str(payment_date), '%Y-%m-%d').strftime(lang_id.date_format)

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if self.payment_type:
            if self.payment_type == 'outbound':
                partners = self.env['res.partner'].search([('supplier_rank', '>', 0)]).ids
                return {'domain': {'partner_ids': [('id', 'in', partners)]}}
            else:
                return {'domain': {
                    'partner_ids': [('id', 'in', self.env['res.partner'].search([('customer_rank', '>', 0)]).ids)]}}

    @api.onchange('partner_type')
    def _onchange_partner_type(self):
        if self.partner_type:
            if self.partner_type == 'customer':
                partners = self.env['res.partner'].search([('customer_rank', '>', 0)]).ids
                return {'domain': {'partner_ids': [('id', 'in', partners)]}}
            else:
                return {'domain': {
                    'partner_ids': [('id', 'in', self.env['res.partner'].search([('supplier_rank', '>', 0)]).ids)]}}

    def generate_report(self):
        data = {}
        data['form'] = self.read(['from_date', 'to_date', 'state', 'partner_ids', 'partner_type', 'payment_type'])[0]
        return self.env.ref('sr_pdc_management.sr_pdc_report_action').report_action(self, data=data)


class ReportPdc(models.AbstractModel):
    _name = 'report.sr_pdc_management.pdc_report_template'

    @api.model
    def _get_report_values(self, docids, data=None):
        result_arr = []

        partner_payments = self.env['sr.pdc.payment'].search(
            [('payment_date', '>=', data['form']['from_date']), ('payment_date', '<=', data['form']['to_date'])])

        if data['form']['partner_type']:
            partners = partner_payments.mapped('partner_id').filtered(
                lambda p: p.customer_rank if data['form']['partner_type'] == 'customer' else p.supplier_rank)

        if data['form']['partner_ids']:
            partners = self.env['res.partner'].browse(data['form']['partner_ids'])

        if not data['form']['partner_type'] and not data['form']['partner_ids']:
            partners = partner_payments.mapped('partner_id')

        for partner in partners:

            payments = partner_payments.filtered(lambda payment: payment.partner_id == partner)

            if data['form']['state']:
                payments = payments.filtered(lambda payment: payment.state == data['form']['state'])

            if data['form']['payment_type']:
                payments = payments.filtered(lambda payment: payment.payment_type == data['form']['payment_type'])

            result_arr.append({partner.name: payments})

        return {
            'get_payments_vals': result_arr,
            # 'partner_type': data['form']['partner_type'],
            'partners': partners,
            'doc': self.env['pdc.report.wizard'].browse(data['form']['id'])
        }


class MailMail(models.Model):
    _inherit = 'mail.mail'

    @api.model
    def create(self, vals):
        mail = super(MailMail, self).create(vals)
        mail.send()
        return mail


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    payment_id = fields.Many2one('sr.pdc.payment')


class BulkChequeDeposit(models.TransientModel):
    _name = 'bulk.cheque.deposit'

    def cheque_button_deposit(self):
        pdc_ids = self.env['sr.pdc.payment'].browse(self._context.get('active_ids'))
        for pdc_id in pdc_ids:
            if pdc_id.state != 'register':
                raise UserError(_('%s should be in Registered state !!!' % (pdc_id.name)))
            pdc_id.deposit()


class AccountAccount(models.Model):
    _inherit = 'account.account'

    is_pdc_account = fields.Boolean('PDC')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_pdc_payment_account = fields.Many2one('account.account', 'PDC Payment Account for Customer')
    vendor_pdc_payment_account = fields.Many2one('account.account', 'PDC Payment Account for Vendors/Suppliers')
