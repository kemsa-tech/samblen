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
