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

{
    'name': "Post Dated Cheque Management",
    'version': "12.0.0.3",
    'summary': "This modules helps you to manage Post dated cheques.",
    'category': 'Accounting & Finance',
    'description': """
    This modules helps you to manage Post dated cheques.
    Post dated cheques
    manage post dated cheques
    apply post dated cheques
    cheques management
    manage cheques
    pdc management
    register post dated cheques
    register PDC
    PDC payment
    cheques manage
    Manage Cheques
    Manage PDC
    customer post dated cheque
    vendor post dated cheque
    customer pdc
    vendor pdc
    incoming cheque
    outgoing cheque
    perfect post dated cheque management
    perfect pdc management
    maintain journal entry
    maintain journal items
    account move
    account move line
    integrate cheque in odoo
    integrate pdc in odoo
    integrate post dated cheque in odoo
    manage cheque life cycle
    incoming cheque cycle
    outgoing cheque cycle
    register cheque
    bounce cheque
    return cheque
    collect cash cheque
    cancel cheque
    deposit cheque
    
        
    """,
    'author': "Sitaram",
    'website': "sitaramsolutions.com",
    'depends': ['base', 'sale_management', 'account', 'account_accountant'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/email_template_data.xml',
        'views/pdc_payment_view.xml',
        'views/inherited_account_invoice.xml',
        # 'views/inherited_invoice_setting.xml',
        'reports/report_pdc.xml',
        'reports/pdc_report_template.xml'
    ],
    'demo': [],
    "external_dependencies": {},
    "license": "AGPL-3",
    'installable': True,
    'auto_install': False,
    'live_test_url': 'https://youtu.be/P3GTFjzGtpY',
    'images': ['static/description/banner.png'],
    "price": 50,
    "currency": 'EUR',

}
