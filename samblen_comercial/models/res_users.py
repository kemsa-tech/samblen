# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    samblen_max_discount = fields.Float(
        string='Tope de descuento (%)', default=0.0,
        help='Descuento máximo por línea que el usuario puede dar sin '
             'aprobación. Arriba de este tope la cotización requiere '
             'aprobación de un Aprobador de descuentos.')
