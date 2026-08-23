# -*- coding: utf-8 -*-
from odoo import fields, models


class ConcreteMaterial(models.Model):
    _name = 'concrete.material'
    _description = 'Material para concreto'
    _order = 'sequence, name'

    name = fields.Char(string='Material', required=True)
    code = fields.Char(string='Clave')
    sequence = fields.Integer(default=10)
    uom = fields.Selection(
        [('kg', 'kg'), ('l', 'L')],
        string='Unidad de medida', default='kg', required=True)
    product_id = fields.Many2one(
        'product.product', string='Producto almacenable',
        help='Producto de inventario que representa este material.')
    active = fields.Boolean(default=True)
