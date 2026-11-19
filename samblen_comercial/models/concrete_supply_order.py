# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _


class ConcreteSupplyOrder(models.Model):
    _inherit = 'concrete.supply.order'

    date_pour = fields.Datetime(string='Inicio de colado', tracking=True)
    date_pour_end = fields.Datetime(string='Fin de colado')
    user_id = fields.Many2one(related='sale_order_id.user_id',
                              string='Vendedor', store=True)

    @api.onchange('date_pour')
    def _onchange_date_pour(self):
        if self.date_pour and not self.date_pour_end:
            self.date_pour_end = self.date_pour + timedelta(hours=3)

    def _plant_users(self):
        group = self.env.ref('samblen_comercial.group_plant_scheduler',
                             raise_if_not_found=False)
        if not group:
            return self.env['res.users']
        return group.user_ids if 'user_ids' in group._fields else group.users

    def _notify_plant(self):
        """Avisa a Programación de planta que hay un colado nuevo."""
        for osc in self:
            when = osc.date_pour and fields.Datetime.context_timestamp(
                osc, osc.date_pour).strftime('%d/%m/%Y %H:%M') or _('sin fecha')
            for user in osc._plant_users():
                osc.activity_schedule(
                    'mail.mail_activity_data_todo', user_id=user.id,
                    date_deadline=(osc.date_pour.date() if osc.date_pour
                                   else fields.Date.context_today(osc)),
                    summary=_('Programar colado %s') % when,
                    note=_('%s m3 para %s, obra %s.') % (
                        osc.qty_m3, osc.partner_id.name, osc.obra or '-'))
        return True


class ConcreteDelivery(models.Model):
    _inherit = 'concrete.delivery'

    date_return = fields.Datetime(string='Regreso estimado',
                                  compute='_compute_date_return', store=True)

    @api.depends('date_load')
    def _compute_date_return(self):
        for rec in self:
            rec.date_return = (rec.date_load + timedelta(hours=2)
                               if rec.date_load else False)
