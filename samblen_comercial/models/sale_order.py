# -*- coding: utf-8 -*-
import math
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    concrete_pump = fields.Boolean(string='Requiere bombeo')
    concrete_shift = fields.Selection([
        ('day', 'Diurno'),
        ('night', 'Nocturno'),
        ('sunday', 'Domingo / festivo'),
    ], string='Turno de colado', default='day')
    concrete_tma_option_id = fields.Many2one(
        'samblen.concrete.option', string='TMA',
        domain=[('option_type', '=', 'tma')])
    concrete_rev_option_id = fields.Many2one(
        'samblen.concrete.option', string='Revenimiento',
        domain=[('option_type', '=', 'rev')])
    concrete_additive_ids = fields.Many2many(
        'samblen.concrete.option', 'sale_order_concrete_additive_rel',
        'order_id', 'option_id', string='Aditivos',
        domain=[('option_type', '=', 'additive')])
    concrete_tiro_id = fields.Many2one(
        'samblen.concrete.option', string='Tipo de tiro',
        domain=[('option_type', '=', 'tiro')])
    samblen_quote_type = fields.Selection([
        ('concrete', 'Concreto premezclado'),
        ('prefab', 'Prefabricados'),
    ], string='Tipo de cotización', default='concrete', required=True)
    concrete_zone_id = fields.Many2one('samblen.commercial.zone',
                                       string='Zona')
    concrete_wait_minutes = fields.Float(
        string='Tiempo estimado en obra (min)',
        help='Minutos que la olla espera en obra. Lo que pase de los minutos '
             'libres se cobra por hora.')
    concrete_pour_datetime = fields.Datetime(string='Fecha y hora de colado')
    concrete_pour_hours = fields.Float(string='Duración del colado (h)',
                                       default=3.0)
    advance_pct = fields.Float(string='Anticipo (%)')
    advance_amount = fields.Monetary(string='Anticipo',
                                     compute='_compute_advance')
    freight_retention = fields.Boolean(
        string='Retener 4% IVA del flete',
        help='Cliente persona moral: retiene 4% de IVA sobre el flete.')
    retention_amount = fields.Monetary(string='Retención estimada',
                                       compute='_compute_advance')
    prefab_weight_total = fields.Float(string='Peso total (kg)',
                                       compute='_compute_prefab_info')
    prefab_trips = fields.Integer(string='Viajes de flete',
                                  compute='_compute_prefab_info')
    prefab_ready_date = fields.Date(
        string='Entrega estimada',
        help='Según existencias y días de fabricación de cada pieza.',
        compute='_compute_prefab_info')
    max_line_discount = fields.Float(
        string='Descuento máximo (%)', compute='_compute_max_line_discount')
    discount_state = fields.Selection([
        ('none', 'No requiere'),
        ('pending', 'Pendiente de aprobación'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ], string='Aprobación de descuento', default='none', tracking=True,
        copy=False)
    discount_approved_value = fields.Float(
        string='Descuento aprobado (%)', copy=False, readonly=True)
    discount_approver_id = fields.Many2one(
        'res.users', string='Aprobó', copy=False, readonly=True)
    discount_needs_approval = fields.Boolean(
        compute='_compute_max_line_discount')

    @api.depends('order_line.discount', 'user_id.samblen_max_discount',
                 'discount_state', 'discount_approved_value')
    def _compute_max_line_discount(self):
        for order in self:
            disc = max(order.order_line.mapped('discount') or [0.0])
            order.max_line_discount = disc
            tope = order.user_id.samblen_max_discount or 0.0
            approved = (order.discount_state == 'approved'
                        and disc <= order.discount_approved_value)
            order.discount_needs_approval = disc > tope and not approved

    @api.depends('amount_total', 'advance_pct', 'freight_retention',
                 'order_line.price_subtotal')
    def _compute_advance(self):
        flete = self.env.ref('samblen_concretera.product_flete',
                             raise_if_not_found=False)
        prefab_fl = self.env['product.template'].search(
            [('samblen_charge_type', '=', 'prefab_freight')])
        for order in self:
            order.advance_amount = order.amount_total * order.advance_pct / 100.0
            fl_lines = order.order_line.filtered(
                lambda l: l.product_id.product_tmpl_id in (flete | prefab_fl))
            order.retention_amount = (sum(fl_lines.mapped('price_subtotal'))
                                      * 0.04 if order.freight_retention else 0.0)

    def _prefab_lines(self):
        return self.order_line.filtered(
            lambda l: l.product_id.product_tmpl_id.is_prefab)

    @api.depends('order_line.product_uom_qty', 'order_line.product_id')
    def _compute_prefab_info(self):
        truck = self.env['product.template'].search(
            [('samblen_charge_type', '=', 'prefab_freight')], limit=1)
        cap = truck.truck_capacity_kg or 20000.0
        today = fields.Date.context_today(self)
        for order in self:
            lines = order._prefab_lines()
            weight = sum(l.product_uom_qty * l.product_id.prefab_weight_kg
                         for l in lines)
            days = 0
            for l in lines:
                p = l.product_id
                short = p.is_storable and p.qty_available < l.product_uom_qty
                if short or not p.is_storable:
                    days = max(days, p.prefab_lead_days or 0)
            order.prefab_weight_total = weight
            order.prefab_trips = math.ceil(weight / cap) if weight else 0
            order.prefab_ready_date = (today + timedelta(days=days + 1)
                                       if lines else False)

    @api.onchange('concrete_zone_id')
    def _onchange_concrete_zone(self):
        zone = self.concrete_zone_id
        if zone:
            if zone.distance_km and not self.concrete_distance_km:
                self.concrete_distance_km = zone.distance_km
            if zone.pricelist_id:
                self.pricelist_id = zone.pricelist_id

    @api.onchange('concrete_pour_datetime')
    def _onchange_pour_datetime(self):
        if self.concrete_pour_datetime:
            self.commitment_date = self.concrete_pour_datetime
            wd = fields.Datetime.context_timestamp(
                self, self.concrete_pour_datetime)
            if wd.weekday() == 6:
                self.concrete_shift = 'sunday'
            elif wd.hour >= 20 or wd.hour < 6:
                self.concrete_shift = 'night'

    def _charge_product(self, ctype):
        return self.env['product.template'].search(
            [('samblen_charge_type', '=', ctype)], limit=1)

    # ---------- Cargos automáticos ----------
    def _set_charge_line(self, product, qty, price, label):
        line = self.order_line.filtered(lambda l: l.product_id == product)[:1]
        vals = {'product_uom_qty': qty, 'price_unit': price, 'name': label}
        if line:
            line.write(vals)
        else:
            vals['product_id'] = product.id
            self.write({'order_line': [(0, 0, vals)]})

    def _remove_charge_line(self, product):
        self.order_line.filtered(lambda l: l.product_id == product).unlink()

    def action_compute_charges(self):
        """Calcula flete, bombeo y recargo por turno en un solo paso."""
        self.ensure_one()
        if self.concrete_distance_km:
            self.action_compute_freight()
        m3 = self._concrete_qty()
        # Opciones técnicas: TMA, revenimiento, aditivos y tiro
        options = self.env['samblen.concrete.option'].with_context(
            active_test=False).search([])
        self.order_line.filtered(
            lambda l: l.product_id in options.mapped('product_id')).unlink()
        selected = (self.concrete_tma_option_id | self.concrete_rev_option_id
                    | self.concrete_additive_ids | self.concrete_tiro_id)
        new_lines = [(0, 0, {'product_id': p.id, 'product_uom_qty': q,
                             'price_unit': pr, 'name': name})
                     for p, q, pr, name in selected._charge_lines(m3)]
        if new_lines:
            self.write({'order_line': new_lines})

        pump = self.env.ref('samblen_comercial.product_bombeo')
        if self.concrete_pump and not self.concrete_tiro_id:
            self._set_charge_line(
                pump.product_variant_id, m3, pump.list_price,
                _('Servicio de bombeo (%.1f m3)') % m3)
        else:
            self._remove_charge_line(pump.product_variant_id)

        shift = self.env.ref('samblen_comercial.product_recargo_turno')
        pct = {'night': shift.shift_night_pct,
               'sunday': shift.shift_sunday_pct}.get(self.concrete_shift, 0.0)
        concrete_lines = self.order_line.filtered(
            lambda l: l.product_id.product_tmpl_id.is_concrete)
        base = sum(concrete_lines.mapped('price_subtotal'))
        if pct and base:
            label = _('Recargo turno %s (%.0f%%)') % (
                dict(self._fields['concrete_shift'].selection)[
                    self.concrete_shift], pct)
            self._set_charge_line(shift.product_variant_id, 1.0,
                                  round(base * pct / 100.0, 2), label)
        else:
            self._remove_charge_line(shift.product_variant_id)

        # Carga mínima
        short = self._charge_product('short_load')
        if short:
            missing = short.min_load_m3 - m3
            if m3 and missing > 0:
                self._set_charge_line(
                    short.product_variant_id, missing, short.list_price,
                    _('Carga incompleta: %.1f m3 faltantes para la carga '
                      'mínima de %.1f m3') % (missing, short.min_load_m3))
            else:
                self._remove_charge_line(short.product_variant_id)
        # Tiempo de espera
        wait = self._charge_product('wait')
        if wait:
            extra_h = max(0.0, (self.concrete_wait_minutes or 0.0)
                          - wait.wait_free_minutes) / 60.0
            if extra_h:
                self._set_charge_line(
                    wait.product_variant_id, round(extra_h, 2),
                    wait.list_price,
                    _('Tiempo de espera: %.0f min (libres %.0f)') % (
                        self.concrete_wait_minutes, wait.wait_free_minutes))
            else:
                self._remove_charge_line(wait.product_variant_id)
        # Ajuste por zona sobre el importe de concreto
        zone_p = self._charge_product('zone')
        if zone_p:
            concrete_lines = self.order_line.filtered(
                lambda l: l.product_id.product_tmpl_id.is_concrete)
            base = sum(concrete_lines.mapped('price_subtotal'))
            pct = self.concrete_zone_id.price_adjust_pct
            if pct and base:
                self._set_charge_line(
                    zone_p.product_variant_id, 1.0,
                    round(base * pct / 100.0, 2),
                    _('Ajuste zona %s (%+.1f%%)') % (
                        self.concrete_zone_id.name, pct))
            else:
                self._remove_charge_line(zone_p.product_variant_id)
        return True

    def action_compute_prefab(self):
        """Flete por viajes según peso y fecha estimada de entrega."""
        self.ensure_one()
        if not self._prefab_lines():
            raise UserError(_('Agrega piezas prefabricadas a la cotización.'))
        truck = self._charge_product('prefab_freight')
        if truck:
            if self.prefab_trips:
                self._set_charge_line(
                    truck.product_variant_id, self.prefab_trips,
                    truck.list_price,
                    _('Flete prefabricados: %d viaje(s), %.0f kg') % (
                        self.prefab_trips, self.prefab_weight_total))
            else:
                self._remove_charge_line(truck.product_variant_id)
        if self.prefab_ready_date:
            self.commitment_date = fields.Datetime.to_datetime(
                self.prefab_ready_date).replace(hour=15)
        return True

    def action_compute_all(self):
        for order in self:
            if order.samblen_quote_type == 'prefab':
                order.action_compute_prefab()
            else:
                order.action_compute_charges()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        if not self.env.context.get('samblen_no_followup'):
            act = self.env.ref('samblen_comercial.activity_quote_followup',
                               raise_if_not_found=False)
            for order in orders:
                if act and order.user_id:
                    order.activity_schedule(
                        activity_type_id=act.id, user_id=order.user_id.id,
                        date_deadline=fields.Date.context_today(order)
                        + timedelta(days=3),
                        summary=_('Dar seguimiento a la cotización'))
        return orders

    # ---------- Circuito de aprobación ----------
    def _discount_approvers(self):
        group = self.env.ref('samblen_comercial.group_discount_approver')
        return group.user_ids if 'user_ids' in group._fields else group.users

    def action_request_discount_approval(self):
        for order in self:
            if not order.discount_needs_approval:
                raise UserError(_('El descuento está dentro del tope del '
                                  'vendedor; no requiere aprobación.'))
            approvers = order._discount_approvers()
            if not approvers:
                raise UserError(_('No hay usuarios en el grupo "Aprobador '
                                  'de descuentos (Samblen)".'))
            order.discount_state = 'pending'
            for user in approvers:
                order.activity_schedule(
                    'mail.mail_activity_data_todo', user_id=user.id,
                    summary=_('Aprobar descuento %.1f%%') %
                    order.max_line_discount,
                    note=_('El vendedor %s solicita un descuento de %.1f%% '
                           '(tope %.1f%%).') % (
                        order.user_id.name, order.max_line_discount,
                        order.user_id.samblen_max_discount))
        return True

    def _check_approver(self):
        if not self.env.user.has_group(
                'samblen_comercial.group_discount_approver'):
            raise UserError(_('Solo un Aprobador de descuentos puede '
                              'aprobar o rechazar.'))

    def action_approve_discount(self):
        self._check_approver()
        for order in self:
            order.write({
                'discount_state': 'approved',
                'discount_approved_value': order.max_line_discount,
                'discount_approver_id': self.env.user.id,
            })
            order.activity_feedback(['mail.mail_activity_data_todo'],
                                    feedback=_('Descuento aprobado'))
            order.message_post(body=_('Descuento de %.1f%% aprobado por %s.')
                               % (order.max_line_discount,
                                  self.env.user.name))
        return True

    def action_reject_discount(self):
        self._check_approver()
        for order in self:
            order.discount_state = 'rejected'
            order.activity_feedback(['mail.mail_activity_data_todo'],
                                    feedback=_('Descuento rechazado'))
            order.message_post(body=_('Descuento rechazado por %s. Ajustar '
                                      'el descuento al tope del vendedor.')
                               % self.env.user.name)
        return True

    def _create_osc(self):
        osc = super()._create_osc()
        vals = {}
        if self.concrete_tma_option_id:
            vals['tma'] = self.concrete_tma_option_id.name
        if self.concrete_rev_option_id:
            vals['revenimiento'] = self.concrete_rev_option_id.name
        if self.concrete_pour_datetime:
            vals['date_pour'] = self.concrete_pour_datetime
            vals['date_pour_end'] = self.concrete_pour_datetime + timedelta(
                hours=self.concrete_pour_hours or 3.0)
        if vals:
            osc.write(vals)
        osc._notify_plant()
        extras = self.concrete_additive_ids.mapped('name')
        if extras or self.concrete_tiro_id:
            osc.message_post(body=_('Dosificación técnica: aditivos %s; tiro %s.') % (
                ', '.join(extras) or _('ninguno'),
                self.concrete_tiro_id.name or _('directo')))
        return osc

    def action_confirm(self):
        for order in self:
            if order.discount_needs_approval:
                raise UserError(_(
                    'La cotización %s tiene un descuento de %.1f%%, arriba '
                    'del tope del vendedor (%.1f%%). Solicita aprobación '
                    'antes de confirmar.') % (
                    order.name, order.max_line_discount,
                    order.user_id.samblen_max_discount))
        return super().action_confirm()
