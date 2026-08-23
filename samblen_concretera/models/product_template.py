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
    is_concrete_material = fields.Boolean(
        string='Es materia prima de concreto',
        help='Material consumido en la produccion de concreto.')
    is_freight = fields.Boolean(
        string='Es flete de concreto',
        help='Producto usado para el cobro de flete por distancia.')
    freight_base = fields.Float(string='Flete base',
                                help='Cargo fijo de flete (independiente de km).')
    freight_per_km = fields.Float(string='Flete por km',
                                  help='Cargo por kilometro a la obra.')
    freight_free_km = fields.Float(
        string='Radio gratis (km)',
        help='Kilometros sin costo de flete; el cobro aplica al excedente.')
