# -*- coding: utf-8 -*-
{
    'name': 'Samblen Comercial',
    'version': '19.0.1.2.2',
    'category': 'Sales',
    'summary': 'Cotizador de concreto y prefabricados, CRM de obra y agenda de colados (Fase 1)',
    'description': """
Módulo Comercial para Samblen (Fase 1 - Módulo 1 del RFP)
=========================================================
- Topes de descuento por usuario.
- Circuito de aprobación digital cuando un descuento supera el tope.
- Cargos automáticos: bombeo por m3 y recargo por turno (nocturno / domingo).
- Cotizador técnico: TMA, revenimiento, aditivos, tiro, carga mínima,
  tiempo de espera, zonas y listas de precios, anticipo y retención.
- Cotizador de prefabricados: flete por viajes según peso y fecha de
  entrega según existencias.
- CRM de obra: datos de obra en la oportunidad, visita agendada y botón
  para cotizar concreto o prefabricados.
- Agenda de colados (calendario y Gantt) con aviso a Programación de planta.
- PDF "Cotización Samblen".
""",
    'author': 'Kemsa Solutions',
    'website': 'https://github.com/kemsa-tech/samblen',
    'license': 'LGPL-3',
    'depends': ['sale_management', 'samblen_concretera', 'crm', 'sale_crm', 'calendar',
                'utm', 'web_gantt'],
    'data': [
        'security/samblen_comercial_security.xml',
        'security/ir.model.access.csv',
        'data/product_data.xml',
        'data/concrete_option_data.xml',
        'data/comercial_data.xml',
        'views/res_users_views.xml',
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/concrete_option_views.xml',
        'views/commercial_zone_views.xml',
        'views/crm_lead_views.xml',
        'views/agenda_views.xml',
        'report/quote_report.xml',
    ],
    'installable': True,
}
