# -*- coding: utf-8 -*-
{
    'name': 'Samblen Concretera',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Surtimiento de concreto, diseno de mezcla, control de desviaciones e integracion con Frumecar (PoC)',
    'description': """
Modulo Concretera para Samblen (Prueba de Concepto)
===================================================
Cubre el flujo: Cotizacion -> Orden de Surtimiento de Concreto (OSC) ->
Dosificacion (Frumecar) -> Control de desviaciones -> Reporte unificado.

- Diseno de mezcla (formula por m3) con tolerancia.
- Orden de Surtimiento de Concreto con vehiculos/ollas y remision Frumecar.
- Comparador diseno vs dosificado con aviso automatico al salir de tolerancia.
- Reporte Concretera (lista + tabla dinamica) y consumo de material.

Punto de integracion Frumecar simulado mediante la accion "Recibir remision"
(en produccion lo dispara el middleware conectado al puerto bidireccional).
""",
    'author': 'Kemsa Solutions',
    'website': 'https://github.com/kemsa-tech/samblen',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/concrete_data.xml',
        'data/demo_scenario.xml',
        'views/concrete_material_views.xml',
        'views/concrete_mix_design_views.xml',
        'views/concrete_supply_order_views.xml',
        'views/concrete_delivery_views.xml',
        'views/concrete_report_views.xml',
        'views/menus.xml',
    ],
    'application': True,
    'installable': True,
}
