# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ConcreteDelivery(models.Model):
    _name = 'concrete.delivery'
    _description = 'Remision / Olla'
    _inherit = ['mail.thread']
    _order = 'order_id, olla'

    name = fields.Char(string='Olla', required=True, default='Olla')
    order_id = fields.Many2one('concrete.supply.order', string='Orden',
                               required=True, ondelete='cascade', tracking=True)
    design_id = fields.Many2one(related='order_id.design_id', string='Diseno',
                                readonly=True)
    olla = fields.Integer(string='No. olla', default=1)
    unit = fields.Char(string='Unidad (CR)')
    operator = fields.Char(string='Operador')
    volume_m3 = fields.Float(string='Volumen (m3)', default=7.0)
    frumecar_remision = fields.Char(string='Remision Frumecar', tracking=True)
    date_load = fields.Datetime(string='Fecha/Hora de carga')
    state = fields.Selection([
        ('waiting', 'En espera'),
        ('dosed', 'Dosificada'),
    ], string='Estado', default='waiting', tracking=True)
    dosage_ids = fields.One2many('concrete.delivery.dosage', 'delivery_id',
                                 string='Dosificado real')
    out_of_tolerance = fields.Boolean(string='Fuera de tolerancia',
                                      compute='_compute_oot', store=True)
    deviation_count = fields.Integer(string='Desviaciones',
                                     compute='_compute_oot', store=True)

    @api.depends('dosage_ids.out_of_tolerance')
    def _compute_oot(self):
        for rec in self:
            oot = rec.dosage_ids.filtered('out_of_tolerance')
            rec.out_of_tolerance = bool(oot)
            rec.deviation_count = len(oot)

    def action_receive_remision(self):
        """Simula la recepcion de la remision de Frumecar (en produccion lo
        dispara el middleware conectado al puerto bidireccional)."""
        for rec in self:
            if not rec.frumecar_remision:
                rec.frumecar_remision = self.env['ir.sequence'].next_by_code(
                    'concrete.frumecar.remision') or ('FRM/%s' % rec.id)
            rec.write({'state': 'dosed', 'date_load': fields.Datetime.now()})
            rec._notify_deviation()
            rec.order_id._update_progress()
        return True

    def _notify_deviation(self):
        for rec in self:
            oot = rec.dosage_ids.filtered('out_of_tolerance')
            if oot and rec.order_id:
                names = ', '.join(oot.mapped('material_id.name'))
                tol = rec.order_id.design_id.tolerance or 0.0
                rec.order_id.message_post(body=_(
                    'Aviso de desviacion en %s (%s): %s fuera de tolerancia '
                    '(+/-%.1f%%). Revisar el motivo de la dosificacion.'
                ) % (rec.name, rec.frumecar_remision or '', names, tol))
                rec.order_id.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Revisar desviacion %s') % rec.name,
                    note=_('Materiales fuera de tolerancia: %s') % names)


class ConcreteDeliveryDosage(models.Model):
    _name = 'concrete.delivery.dosage'
    _description = 'Dosificado real por material'
    _order = 'id'

    delivery_id = fields.Many2one('concrete.delivery', required=True,
                                  ondelete='cascade')
    order_id = fields.Many2one(related='delivery_id.order_id', store=True,
                               string='Orden')
    material_id = fields.Many2one('concrete.material', string='Material',
                                  required=True)
    uom = fields.Selection(related='material_id.uom', string='UdM',
                           readonly=True)
    qty_design = fields.Float(string='Diseno', digits=(16, 3),
                              compute='_compute_qty_design', store=True)
    qty_real = fields.Float(string='Dosificado real', digits=(16, 3))
    deviation = fields.Float(string='Desviacion (%)', digits=(16, 2),
                             compute='_compute_deviation', store=True)
    out_of_tolerance = fields.Boolean(string='Fuera de tolerancia',
                                      compute='_compute_oot', store=True)

    @api.depends('delivery_id.volume_m3', 'material_id',
                 'delivery_id.order_id.design_id.line_ids.qty_per_m3')
    def _compute_qty_design(self):
        for rec in self:
            design = rec.delivery_id.order_id.design_id
            per = 0.0
            if design:
                line = design.line_ids.filtered(
                    lambda l: l.material_id == rec.material_id)[:1]
                per = line.qty_per_m3 if line else 0.0
            rec.qty_design = per * (rec.delivery_id.volume_m3 or 0.0)

    @api.depends('qty_design', 'qty_real')
    def _compute_deviation(self):
        for rec in self:
            rec.deviation = ((rec.qty_real - rec.qty_design) / rec.qty_design
                             * 100.0) if rec.qty_design else 0.0

    @api.depends('deviation', 'delivery_id.order_id.design_id.tolerance')
    def _compute_oot(self):
        for rec in self:
            tol = rec.delivery_id.order_id.design_id.tolerance or 0.0
            rec.out_of_tolerance = abs(rec.deviation) > tol if tol else False
