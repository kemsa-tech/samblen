# -*- coding: utf-8 -*-
{
    'name': 'Samblen - Datos de demostración',
    'version': '19.0.1.0.0',
    'category': 'Hidden',
    'summary': 'Escenario de demostración: clientes, obras, diseños, ollas, cotizaciones y surtimientos',
    'description': """
Carga un escenario realista para la demo en vivo:

- 4 diseños de mezcla (FC 150, 200, 250, 300) con su producto de venta.
- 8 clientes (constructoras y particulares) de Puebla y alrededores.
- 6 ollas revolvedoras con su operador.
- 14 cotizaciones en distintos estados (borrador, enviada, por aprobar
  descuento, confirmada) con flete, bombeo y recargo por turno.
- Órdenes de Surtimiento con remisiones dosificadas en los últimos 30 días,
  la mayoría dentro de tolerancia y algunas con desviación.

Los nombres de clientes y obras son ficticios. Instalar SOLO en ramas de
desarrollo o staging, nunca en producción.
""",
    'author': 'Kemsa Solutions',
    'license': 'LGPL-3',
    'depends': ['samblen_concretera', 'samblen_comercial'],
    'data': [],
    'post_init_hook': 'post_init_hook',
    'installable': True,
}
