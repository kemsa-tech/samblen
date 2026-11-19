# -*- coding: utf-8 -*-
from odoo import fields, models


class SamblenCommercialZone(models.Model):
    """Zona comercial: ajusta el precio del concreto y propone distancia y
    lista de precios al cotizar."""
    _name = 'samblen.commercial.zone'
    _description = 'Zona comercial Samblen'
    _order = 'sequence, name'

    name = fields.Char(string='Zona', required=True)
    sequence = fields.Integer(default=10)
    distance_km = fields.Float(string='Distancia de referencia (km)')
    price_adjust_pct = fields.Float(
        string='Ajuste al concreto (%)',
        help='Positivo = recargo, negativo = descuento sobre el importe de '
             'concreto.')
    pricelist_id = fields.Many2one('product.pricelist',
                                   string='Lista de precios')
    note = fields.Char(string='Municipios / colonias')
    active = fields.Boolean(default=True)
