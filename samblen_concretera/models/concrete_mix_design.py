# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ConcreteMixDesign(models.Model):
    _name = 'concrete.mix.design'
    _description = 'Diseño de mezcla'
    _order = 'name'

    name = fields.Char(string='Clave del diseño', required=True)
    resistance = fields.Char(string='Resistencia', default='250 kg/cm2')
    tma = fields.Char(string='TMA', default='20 mm')
    revenimiento = fields.Char(string='Revenimiento', default='14 cm')
    tolerance = fields.Float(string='Tolerancia (%)', default=3.0,
                             help='Desviación maxima permitida por material.')
    line_ids = fields.One2many('concrete.mix.design.line', 'design_id',
                               string='Materiales por m3')
    active = fields.Boolean(default=True)
    line_count = fields.Integer(compute='_compute_line_count')

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)


class ConcreteMixDesignLine(models.Model):
    _name = 'concrete.mix.design.line'
    _description = 'Linea de diseño de mezcla'
    _order = 'sequence, id'

    design_id = fields.Many2one('concrete.mix.design', required=True,
                                ondelete='cascade')
    sequence = fields.Integer(default=10)
    material_id = fields.Many2one('concrete.material', string='Material',
                                  required=True)
    uom = fields.Selection(related='material_id.uom', string='UdM', readonly=True)
    qty_per_m3 = fields.Float(string='Cantidad por m3', digits=(16, 3))
