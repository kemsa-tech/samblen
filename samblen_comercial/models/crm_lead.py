# -*- coding: utf-8 -*-
from datetime import timedelta

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    samblen_interest = fields.Selection([
        ('concrete', 'Concreto premezclado'),
        ('prefab', 'Prefabricados'),
        ('both', 'Concreto y prefabricados'),
    ], string='Interés', default='concrete')
    obra_name = fields.Char(string='Obra')
    obra_address = fields.Char(string='Dirección de la obra')
    obra_type = fields.Selection([
        ('vivienda', 'Vivienda'),
        ('fraccionamiento', 'Fraccionamiento'),
        ('industrial', 'Nave industrial'),
        ('comercial', 'Comercial'),
        ('infraestructura', 'Infraestructura / gobierno'),
        ('pavimento', 'Pavimento'),
    ], string='Tipo de obra')
    obra_zone_id = fields.Many2one('samblen.commercial.zone', string='Zona')
    obra_distance_km = fields.Float(string='Distancia a planta (km)')
    m3_estimated = fields.Float(string='m3 estimados')
    concrete_design_id = fields.Many2one('concrete.mix.design',
                                         string='Resistencia probable')
    pour_date_estimated = fields.Date(string='Fecha probable de colado')
    visit_datetime = fields.Datetime(string='Visita a obra')
    visit_done = fields.Boolean(string='Visita realizada')

    @api.onchange('obra_zone_id')
    def _onchange_obra_zone(self):
        if self.obra_zone_id.distance_km and not self.obra_distance_km:
            self.obra_distance_km = self.obra_zone_id.distance_km

    def action_schedule_visit(self):
        """Crea la cita de visita a obra en el calendario del vendedor."""
        self.ensure_one()
        start = self.visit_datetime
        if not start:
            # 10:00 hora local del usuario, guardado en UTC
            local = fields.Datetime.context_timestamp(
                self, fields.Datetime.now() + timedelta(days=1)).replace(
                    hour=10, minute=0, second=0, microsecond=0)
            start = local.astimezone(pytz.utc).replace(tzinfo=None)
        partners = (self.user_id.partner_id | self.partner_id).ids
        event = self.env['calendar.event'].create({
            'name': _('Visita a obra: %s') % (self.obra_name or self.name),
            'start': start,
            'stop': start + timedelta(hours=1),
            'location': self.obra_address or False,
            'user_id': (self.user_id or self.env.user).id,
            'partner_ids': [(6, 0, partners)],
            'opportunity_id': self.id,
            'res_model_id': self.env['ir.model']._get_id('crm.lead'),
            'res_id': self.id,
        })
        self.visit_datetime = start
        stage = self.env.ref('samblen_comercial.stage_visita',
                             raise_if_not_found=False)
        if stage and self.stage_id.sequence <= stage.sequence:
            self.stage_id = stage
        return {
            'type': 'ir.actions.act_window', 'res_model': 'calendar.event',
            'res_id': event.id, 'view_mode': 'form',
            'name': _('Visita a obra'),
        }

    def _quote_vals(self, quote_type):
        if not self.partner_id:
            raise UserError(_('Asigna el cliente a la oportunidad antes de '
                              'cotizar.'))
        vals = {
            'partner_id': self.partner_id.id,
            'opportunity_id': self.id,
            'user_id': (self.user_id or self.env.user).id,
            'team_id': self.team_id.id,
            'samblen_quote_type': quote_type,
            'concrete_obra': self.obra_name or self.name,
            'concrete_zone_id': self.obra_zone_id.id,
            'concrete_distance_km': self.obra_distance_km,
            'origin': self.name,
        }
        if self.obra_zone_id.pricelist_id:
            vals['pricelist_id'] = self.obra_zone_id.pricelist_id.id
        if self.pour_date_estimated:
            vals['concrete_pour_datetime'] = fields.Datetime.to_datetime(
                self.pour_date_estimated).replace(hour=14)
            vals['commitment_date'] = vals['concrete_pour_datetime']
        if quote_type == 'concrete':
            vals['concrete_design_id'] = self.concrete_design_id.id
            tmpl = self.env['product.template'].search(
                [('concrete_design_id', '=', self.concrete_design_id.id)],
                limit=1) if self.concrete_design_id else False
            if tmpl and self.m3_estimated:
                vals['order_line'] = [(0, 0, {
                    'product_id': tmpl.product_variant_id.id,
                    'product_uom_qty': self.m3_estimated})]
        return vals

    def _open_quote(self, quote_type):
        self.ensure_one()
        order = self.env['sale.order'].create(self._quote_vals(quote_type))
        if quote_type == 'concrete' and order.order_line:
            order.action_compute_charges()
        return {
            'type': 'ir.actions.act_window', 'res_model': 'sale.order',
            'res_id': order.id, 'view_mode': 'form',
            'name': _('Cotización'),
        }

    def action_quote_concrete(self):
        return self._open_quote('concrete')

    def action_quote_prefab(self):
        return self._open_quote('prefab')
