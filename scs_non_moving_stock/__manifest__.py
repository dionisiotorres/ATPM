# See LICENSE file for full copyright and licensing details.

{
    'name': 'Non Moving Stock Report',
    'version': '13.0.1.0.0',
    'category': 'Warehouse',
    'description': """
    Non Moving Stock
==========================

This application allows you to generate non moving stock report for
taking two dates as an input from the user.
Get non moving stock per warehouse for each product based on its sales and
stock transaction.
    """,
    'summary': """
    Non Moving Stock Report
    This application allows you to generate non moving stock report for
    taking two dates as an input from the user.
    Get non moving stock per warehouse for each product based on its sales
    and stock transaction.
    """,
    'author': 'Serpent Consulting Services Pvt. Ltd.',
    'maintainer': 'Serpent Consulting Services Pvt. Ltd.',
    'website': 'http://www.serpentcs.com',
    'depends': ['sale_stock'],
    'license': 'LGPL-3',
    'data': [
        'wizard/non_moving_stock_report_wiz_view.xml',
        'report/report_non_moving_stock.xml',
        'report/non_moving_stock_templates.xml',
    ],
    'images': ['static/description/nonmoving.png'],
    'installable': True,
    'price': 5,
    'currency': 'EUR',
}
