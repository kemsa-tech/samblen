# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_prefab = fields.Boolean(string='Es prefabricado')
    is_pump_service = fields.Boolean(string='Es servicio de bombeo')
    is_shift_surcharge = fields.Boolean(string='Es recargo por turno')
    shift_night_pct = fields.Float(string='Recargo nocturno (%)')
    shift_sunday_pct = fields.Float(string='Recargo domingo/festivo (%)')
