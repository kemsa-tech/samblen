# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

# Variacion simulada del dosificado real vs diseño, por clave de material.
# Reproduce el escenario de la demo (cemento fuera de tolerancia).
_SIM_VARIANCE = {
    'CEM': 0.95238,      # -4.76%  -> fuera de +/-3%
    'GRA-CAL': 1.0204,   # +2.04%
    'GRA-VIL': 1.0,
    'ARE-RIO': 1.0101,   # +1.01%
    'ARE-TRI': 1.0101,   # +1.01%
    'AGUA': 1.0,         # 0.00%
    'IFO': 0.98810,      # -1.19%
    'VIS': 1.0179,       # +1.79%
}


class ConcreteDelivery(models.Model):
    _name = 'concrete.delivery'
    _description = 'Remisión / Olla'
    _inherit = ['mail.thread']
    _order = 'order_id, olla'

    name = fields.Char(string='Olla', required=True, default='Olla')
    order_id = fields.Many2one('concrete.supply.order', string='Orden',
                               required=True, ondelete='cascade', tracking=True)
    design_id = fields.Many2one(related='order_id.design_id', string='Diseño',
                                readonly=True, store=True)
    olla = fields.Integer(string='No. olla', default=1)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Olla / Unidad',
                                 help='Unidad revolvedora del catalogo de Flota.')
    operator = fields.Char(string='Operador')
    volume_m3 = fields.Float(string='Volumen (m3)', default=7.0)
    frumecar_remision = fields.Char(string='Remisión Frumecar', tracking=True)
    date_load = fields.Datetime(string='Fecha/Hora de carga')
    km_start = fields.Float(string='Km inicial')
    km_end = fields.Float(string='Km final')
    diesel_l = fields.Float(string='Diésel (L)')
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
    production_id = fields.Many2one('mrp.production',
                                    string='Orden de fabricación', readonly=True)

    @api.depends('dosage_ids.out_of_tolerance')
    def _compute_oot(self):
        for rec in self:
            oot = rec.dosage_ids.filtered('out_of_tolerance')
            rec.out_of_tolerance = bool(oot)
            rec.deviation_count = len(oot)

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        for rec in self:
            if rec.vehicle_id and rec.vehicle_id.driver_id:
                rec.operator = rec.vehicle_id.driver_id.name

    def _simulate_dosage(self):
        """Genera el dosificado real a partir del diseño (simula Frumecar)
        cuando la olla aun no tiene lineas de dosificado."""
        Dosage = self.env['concrete.delivery.dosage']
        for rec in self:
            design = rec.order_id.design_id
            if not design:
                continue
            for line in design.line_ids:
                factor = _SIM_VARIANCE.get(line.material_id.code, 1.0)
                qty = line.qty_per_m3 * (rec.volume_m3 or 0.0) * factor
                Dosage.create({
                    'delivery_id': rec.id,
                    'material_id': line.material_id.id,
                    'qty_real': round(qty, 3),
                })

    def action_receive_remisión(self):
        """Simula la recepción de la remisión de Frumecar. En producción lo
        dispara el middleware conectado al puerto bidireccional."""
        for rec in self:
            if not rec.frumecar_remision:
                rec.frumecar_remision = self.env['ir.sequence'].next_by_code(
                    'concrete.frumecar.remision') or ('FRM/%s' % rec.id)
            if not rec.dosage_ids:
                rec._simulate_dosage()
            rec.write({'state': 'dosed', 'date_load': fields.Datetime.now()})
            rec._consume_materials()
            rec._notify_deviation()
            rec.order_id._update_progress()
        return True

    def _consume_materials(self):
        """Genera una orden de fabricación (MRP) que consume del almacen el
        material REAL dosificado por Frumecar -> control de inventario nativo.
        Defensivo: si MRP no puede cerrar la orden en esta instancia, se deja
        confirmada y no se interrumpe el flujo de la demo."""
        Production = self.env['mrp.production']
        tmpl = self.env.ref('samblen_concretera.tmpl_concreto_prod',
                            raise_if_not_found=False)
        bom = self.env.ref('samblen_concretera.bom_fc250_prod',
                           raise_if_not_found=False)
        if not tmpl or not bom or not tmpl.product_variant_id:
            return
        for rec in self:
            if rec.production_id:
                continue
            try:
                mo = Production.create({
                    'product_id': tmpl.product_variant_id.id,
                    'product_qty': rec.volume_m3 or 1.0,
                    'bom_id': bom.id,
                    'origin': '%s / %s' % (rec.order_id.name, rec.name),
                })
                mo.action_confirm()
                # Sustituir el consumo teorico por el dosificado REAL.
                for move in mo.move_raw_ids:
                    dline = rec.dosage_ids.filtered(
                        lambda d: d.material_id.product_id == move.product_id)[:1]
                    if dline:
                        move.quantity = dline.qty_real
                        move.picked = True
                mo.qty_producing = rec.volume_m3 or 1.0
                mo.with_context(skip_consumption=True,
                                skip_backorder=True).button_mark_done()
                rec.production_id = mo.id
            except Exception as e:  # noqa: BLE001
                _logger.warning('No se pudo cerrar la orden de fabricación '
                                'para %s: %s', rec.name, e)
                if 'mo' in locals() and mo:
                    rec.production_id = mo.id

    def action_view_production(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'res_id': self.production_id.id,
            'view_mode': 'form',
        }

    def _notify_deviation(self):
        for rec in self:
            oot = rec.dosage_ids.filtered('out_of_tolerance')
            if oot and rec.order_id:
                names = ', '.join(oot.mapped('material_id.name'))
                tol = rec.order_id.design_id.tolerance or 0.0
                rec.order_id.message_post(body=_(
                    'Aviso de desviación en %s (%s): %s fuera de tolerancia '
                    '(+/-%.1f%%). Revisar el motivo de la dosificación.'
                ) % (rec.name, rec.frumecar_remision or '', names, tol))
                rec.order_id.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Revisar desviación %s') % rec.name,
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
    qty_design = fields.Float(string='Diseño', digits=(16, 3),
                              compute='_compute_qty_design', store=True)
    qty_real = fields.Float(string='Dosificado real', digits=(16, 3))
    deviation = fields.Float(string='Desviación (%)', digits=(16, 2),
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
