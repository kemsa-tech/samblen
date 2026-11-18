# -*- coding: utf-8 -*-
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
        return True

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
        if vals:
            osc.write(vals)
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
