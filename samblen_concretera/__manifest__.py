# -*- coding: utf-8 -*-
{
    'name': 'Samblen Concretera',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Surtimiento de concreto, diseño de mezcla, control de desviaciones e integración con Frumecar (PoC)',
    'description': """
Módulo Concretera para Samblen (Prueba de Concepto)
===================================================
Cubre el flujo: Cotización -> Orden de Surtimiento de Concreto (OSC) ->
Dosificación (Frumecar) -> Control de desviaciones -> Reporte unificado.

- Diseño de mezcla (fórmula por m3) con tolerancia.
- Orden de Surtimiento de Concreto con vehículos/ollas y remisión Frumecar.
- Comparador diseño vs dosificado con aviso automático al salir de tolerancia.
- Reporte Concretera (lista + tabla dinámica) y consumo de material.

Punto de integración Frumecar simulado mediante la acción "Recibir remisión"
(en producción lo dispara el middleware conectado al puerto bidireccional).
""",
    'author': 'Kemsa Solutions',
    'website': 'https://github.com/kemsa-tech/samblen',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'fleet', 'sale_management', 'mrp'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/concrete_data.xml',
        'data/stock_mrp_data.xml',
        'data/fleet_data.xml',
        'data/product_data.xml',
        'data/demo_scenario.xml',
        'views/concrete_material_views.xml',
        'views/concrete_mix_design_views.xml',
        'views/concrete_supply_order_views.xml',
        'views/concrete_delivery_views.xml',
        'views/concrete_report_views.xml',
        'views/concrete_config_views.xml',
        'views/sale_order_views.xml',
        'views/menus.xml',
    ],
    'application': True,
    'installable': True,
}
