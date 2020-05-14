# -*- coding: utf-8 -*-
{
    'name': "Stock Balance Report",
    'summary': """
       The module allows to print a stock analysis in a specific period: Incoming stock, outgoing stock, internal transfers, 
       stock adjustments and the cost history by product.
    """,
    'author': "ALPHA BRAINS TECHNOLOGIES",
    'support': 'odoo.alpha.brains.tech@gmail.com',
    'website': "http://www.alpha-brains-technologies.dz",
    'category': 'Warehouse',
    'version': '13.0.1.1',
    'license': 'LGPL-3',
    'depends': ['stock_account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/stock_valuation_wizard_views.xml',
        'reports/stock_valuation_pdf_report.xml',
        'views/menus.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'price': 14.99,
    'currency': 'EUR',
    'css': [
        'static/src/style.css',
    ],
    'images': [
        "static/description/banner.gif",
        "static/description/icon.png",
        "static/description/screenshot1.jpg",
        "static/description/screenshot2.jpg",
    ],
}
