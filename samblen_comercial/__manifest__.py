# -*- coding: utf-8 -*-
{
    'name': 'Samblen Comercial',
    'version': '19.0.1.1.0',
    'category': 'Sales',
    'summary': 'Cotizador de concreto y prefabricados: bombeo, turnos, topes de descuento y aprobación (Fase 1)',
    'description': """
Módulo Comercial para Samblen (Fase 1 - Módulo 1 del RFP)
=========================================================
- Topes de descuento por usuario.
- Circuito de aprobación digital cuando un descuento supera el tope.
- Cargos automáticos: bombeo por m3 y recargo por turno (nocturno / domingo).
- Productos de prefabricados identificados para cotizaciones separadas.
""",
    'author': 'Kemsa Solutions',
    'website': 'https://github.com/kemsa-tech/samblen',
    'license': 'LGPL-3',
    'depends': ['sale_management', 'samblen_concretera'],
    'data': [
        'security/samblen_comercial_security.xml',
        'security/ir.model.access.csv',
        'data/product_data.xml',
        'data/concrete_option_data.xml',
        'views/res_users_views.xml',
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/concrete_option_views.xml',
    ],
    'installable': True,
}
