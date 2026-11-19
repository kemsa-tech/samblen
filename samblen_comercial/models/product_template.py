# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_prefab = fields.Boolean(string='Es prefabricado')
    is_pump_service = fields.Boolean(string='Es servicio de bombeo')
    is_shift_surcharge = fields.Boolean(string='Es recargo por turno')
    shift_night_pct = fields.Float(string='Recargo nocturno (%)')
    shift_sunday_pct = fields.Float(string='Recargo domingo/festivo (%)')

    # Tarifas comerciales (servicios que el cotizador agrega solo)
    samblen_charge_type = fields.Selection([
        ('short_load', 'Carga incompleta (m3 faltantes)'),
        ('wait', 'Tiempo de espera de olla'),
        ('prefab_freight', 'Flete de prefabricados (por viaje)'),
        ('zone', 'Ajuste por zona'),
    ], string='Cargo automático')
    min_load_m3 = fields.Float(string='Carga mínima (m3)', default=3.0)
    wait_free_minutes = fields.Float(string='Minutos libres por colado',
                                     default=60.0)
    truck_capacity_kg = fields.Float(string='Capacidad por viaje (kg)',
                                     default=20000.0)

    # Prefabricados
    prefab_family = fields.Selection([
        ('block', 'Block y tabique'),
        ('adoquin', 'Adoquín'),
        ('tubo', 'Tubería'),
        ('poste', 'Postes'),
        ('trabe', 'Trabes y vigas'),
        ('losa', 'Losas y vigueta'),
        ('otro', 'Otros'),
    ], string='Familia')
    prefab_unit = fields.Selection([
        ('pza', 'Pieza'), ('m2', 'm2'), ('ml', 'Metro lineal'), ('m3', 'm3'),
    ], string='Se vende por', default='pza')
    prefab_weight_kg = fields.Float(string='Peso por unidad (kg)')
    prefab_lead_days = fields.Integer(
        string='Días de fabricación',
        help='Días para fabricar si no hay existencias suficientes.')
