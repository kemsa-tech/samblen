# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    concrete_obra = fields.Char(string='Obra / Proyecto')
    concrete_tipo = fields.Selection(
        [('interno', 'Interno'), ('externo', 'Externo')],
        string='Tipo de surtimiento', default='externo')
    concrete_design_id = fields.Many2one('concrete.mix.design',
                                         string='Diseno de mezcla')
    concrete_distance_km = fields.Float(string='Distancia a obra (km)')
    concrete_osc_ids = fields.One2many('concrete.supply.order', 'sale_order_id',
                                       string='Ordenes de Surtimiento')
    concrete_osc_count = fields.Integer(compute='_compute_osc_count')

    @api.depends('concrete_osc_ids')
    def _compute_osc_count(self):
        for order in self:
            order.concrete_osc_count = len(order.concrete_osc_ids)

    def _concrete_qty(self):
        self.ensure_one()
        lines = self.order_line.filtered(
            lambda l: l.product_id.product_tmpl_id.is_concrete)
        if not lines:
            lines = self.order_line.filtered(lambda l: not l.display_type)
        return sum(lines.mapped('product_uom_qty'))

    def _create_osc(self):
        self.ensure_one()
        design = self.concrete_design_id
        if not design:
            concrete_line = self.order_line.filtered(
                lambda l: l.product_id.product_tmpl_id.concrete_design_id)[:1]
            design = concrete_line.product_id.product_tmpl_id.concrete_design_id
        if not design:
            raise UserError(_(
                'Define un diseno de mezcla en la cotizacion para generar '
                'la Orden de Surtimiento.'))
        return self.env['concrete.supply.order'].create({
            'partner_id': self.partner_id.id,
            'obra': self.concrete_obra,
            'tipo': self.concrete_tipo or 'externo',
            'design_id': design.id,
            'qty_m3': self._concrete_qty(),
            'distance_km': self.concrete_distance_km,
            'origin': self.company_id.partner_id.contact_address or '',
            'sale_order_id': self.id,
            'state': 'released',
        })

    def action_generate_osc(self):
        self.ensure_one()
        osc = self._create_osc()
        self.message_post(body=_(
            'Orden de Surtimiento %s generada desde esta cotizacion.'
        ) % osc.name)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Orden de Surtimiento'),
            'res_model': 'concrete.supply.order',
            'res_id': osc.id,
            'view_mode': 'form',
        }

    def action_view_osc(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ordenes de Surtimiento'),
            'res_model': 'concrete.supply.order',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
        }

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            has_concrete = order.order_line.filtered(
                lambda l: l.product_id.product_tmpl_id.is_concrete)
            if (order.concrete_design_id or has_concrete) \
                    and not order.concrete_osc_ids:
                order._create_osc()
        return res
