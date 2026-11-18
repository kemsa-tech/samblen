# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SamblenConcreteOption(models.Model):
    """Opción técnica del cotizador de concreto: TMA, revenimiento, aditivo
    o tipo de tiro (descarga). Cada opción tiene su producto de servicio
    para que el cargo aparezca como línea propia en la cotización."""
    _name = 'samblen.concrete.option'
    _description = 'Opción del cotizador de concreto'
    _order = 'option_type, sequence, id'

    name = fields.Char(string='Nombre', required=True)
    option_type = fields.Selection([
        ('tma', 'Tamaño máximo de agregado (TMA)'),
        ('rev', 'Revenimiento'),
        ('additive', 'Aditivo'),
        ('tiro', 'Tipo de tiro / descarga'),
    ], string='Tipo', required=True)
    sequence = fields.Integer(default=10)
    price_m3 = fields.Float(string='Cargo por m³',
                            help='Puede ser negativo (descuento por m³).')
    price_fixed = fields.Float(string='Cargo fijo por servicio')
    product_id = fields.Many2one('product.product', string='Producto de cargo',
                                 readonly=True, copy=False)
    active = fields.Boolean(default=True)

    _type_labels = {
        'tma': 'TMA', 'rev': 'Revenimiento', 'additive': 'Aditivo',
        'tiro': 'Tiro',
    }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec.product_id = self.env['product.product'].create({
                'name': '%s: %s' % (self._type_labels[rec.option_type], rec.name),
                'type': 'service',
                'list_price': 0.0,
                'invoice_policy': 'order',
                'sale_ok': True,
                'purchase_ok': False,
            }).id
        return records

    def _charge_lines(self, m3):
        """Devuelve [(producto, cantidad, precio, descripción)] para m3."""
        lines = []
        for opt in self:
            label = opt.product_id.name
            if opt.price_m3:
                lines.append((opt.product_id, m3, opt.price_m3,
                              '%s (%.1f m³)' % (label, m3)))
            if opt.price_fixed:
                lines.append((opt.product_id, 1.0, opt.price_fixed,
                              '%s - cargo fijo' % label))
        return lines
