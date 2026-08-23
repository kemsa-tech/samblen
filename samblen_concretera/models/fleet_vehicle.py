# -*- coding: utf-8 -*-
from odoo import fields, models


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    is_olla = fields.Boolean(string='Es olla revolvedora')
    capacity_m3 = fields.Float(string='Capacidad (m3)')
