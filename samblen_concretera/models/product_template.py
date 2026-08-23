# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_concrete = fields.Boolean(
        string='Es concreto',
        help='Marca los productos de concreto premezclado que generan '
             'orden de surtimiento.')
    concrete_design_id = fields.Many2one(
        'concrete.mix.design', string='Diseno por defecto')
    is_freight = fields.Boolean(
        string='Es flete de concreto',
        help='Producto usado para el cobro de flete por distancia.')
    freight_base = fields.Float(string='Flete base',
                                help='Cargo fijo de flete (independiente de km).')
    freight_per_km = fields.Float(string='Flete por km',
                                  help='Cargo por kilometro a la obra.')
