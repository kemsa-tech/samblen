# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ConcreteSupplyOrder(models.Model):
    _name = 'concrete.supply.order'
    _description = 'Orden de Surtimiento de Concreto'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Numero', default='Nueva', copy=False,
                       readonly=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Cliente',
                                 required=True, tracking=True)
    obra = fields.Char(string='Obra / Proyecto', tracking=True)
    tipo = fields.Selection(
        [('interno', 'Interno'), ('externo', 'Externo')],
        string='Tipo', default='externo', tracking=True)
    design_id = fields.Many2one('concrete.mix.design', string='Diseno',
                                required=True, tracking=True)
    resistance = fields.Char(string='Resistencia', default='250 kg/cm2')
    tma = fields.Char(string='TMA', default='20 mm')
    revenimiento = fields.Char(string='Revenimiento', default='14 cm')
    distance_km = fields.Float(string='Distancia a obra (km)')
    qty_m3 = fields.Float(string='Cantidad solicitada (m3)', default=0.0,
                          tracking=True)
    qty_delivered = fields.Float(string='Cantidad surtida (m3)',
                                 compute='_compute_progress', store=True)
    qty_pending = fields.Float(string='Por surtir (m3)',
                               compute='_compute_progress', store=True)
    date_order = fields.Datetime(string='Fecha', default=fields.Datetime.now)
    origin = fields.Char(string='Origen')
    destination = fields.Char(string='Destino')
    delivery_ids = fields.One2many('concrete.delivery', 'order_id',
                                   string='Vehiculos / Ollas')
    delivery_count = fields.Integer(compute='_compute_delivery_count')
    deviation_alert = fields.Boolean(string='Desviacion',
                                     compute='_compute_progress', store=True)
    state = fields.Selection([
        ('draft', 'Solicitado'),
        ('released', 'Liberado'),
        ('dosing', 'Dosificando'),
        ('partial', 'Parcial'),
        ('done', 'Surtido'),
        ('cancel', 'Cancelado'),
    ], string='Estado', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    sale_order_id = fields.Many2one('sale.order', string='Cotizacion',
                                    readonly=True, copy=False)
    olla_capacity = fields.Float(string='Capacidad por olla (m3)', default=7.0)

    @api.depends('delivery_ids')
    def _compute_delivery_count(self):
        for rec in self:
            rec.delivery_count = len(rec.delivery_ids)

    @api.depends('delivery_ids.state', 'delivery_ids.volume_m3',
                 'delivery_ids.out_of_tolerance', 'qty_m3')
    def _compute_progress(self):
        for rec in self:
            dosed = rec.delivery_ids.filtered(lambda d: d.state == 'dosed')
            delivered = sum(dosed.mapped('volume_m3'))
            rec.qty_delivered = delivered
            rec.qty_pending = max((rec.qty_m3 or 0.0) - delivered, 0.0)
            rec.deviation_alert = any(dosed.mapped('out_of_tolerance'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'Nueva':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'concrete.supply.order') or _('OSC/New')
        return super().create(vals_list)

    # ---- workflow ----
    def action_release(self):
        for rec in self:
            rec.state = 'released'
            rec.message_post(body=_(
                'Cotizacion liberada. Notificada al area de Concretera '
                'y agendada para surtido.'))
        return True

    def _generate_ollas(self):
        """Divide la cantidad solicitada en ollas segun la capacidad y les
        asigna una unidad de Flota y su operador de forma ciclica."""
        Delivery = self.env['concrete.delivery']
        ollas = self.env['fleet.vehicle'].search(
            [('is_olla', '=', True)], order='id')
        for rec in self:
            cap = rec.olla_capacity or 7.0
            remaining = rec.qty_m3 or 0.0
            i = 0
            while remaining > 0.001:
                i += 1
                vol = min(cap, remaining)
                vehicle = ollas[(i - 1) % len(ollas)] if ollas else False
                Delivery.create({
                    'name': _('Olla %s') % i,
                    'order_id': rec.id,
                    'olla': i,
                    'volume_m3': vol,
                    'vehicle_id': vehicle.id if vehicle else False,
                    'operator': (vehicle.driver_id.name
                                 if vehicle and vehicle.driver_id else ''),
                })
                remaining -= vol

    def action_send_frumecar(self):
        for rec in self:
            if not rec.delivery_ids:
                rec._generate_ollas()
            rec.state = 'dosing'
            rec.message_post(body=_(
                'Diseno de mezcla %s enviado a Frumecar (Odoo -> Frumecar). '
                'Ollas generadas: %s.'
            ) % (rec.design_id.name or '', len(rec.delivery_ids)))
        return True

    def action_done(self):
        self.write({'state': 'done'})
        return True

    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True

    def action_draft(self):
        self.write({'state': 'draft'})
        return True

    def _update_progress(self):
        for rec in self:
            dosed = rec.delivery_ids.filtered(lambda d: d.state == 'dosed')
            if not dosed:
                continue
            total = sum(dosed.mapped('volume_m3'))
            if rec.qty_m3 and total >= rec.qty_m3:
                rec.state = 'done'
            elif total > 0:
                rec.state = 'partial'

    def action_view_deliveries(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vehiculos / Ollas'),
            'res_model': 'concrete.delivery',
            'view_mode': 'list,form',
            'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id},
        }
