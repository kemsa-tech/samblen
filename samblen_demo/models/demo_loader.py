# -*- coding: utf-8 -*-
from odoo import api, models

from ..erp_demo import load_erp_demo


class SamblenDemoLoader(models.AbstractModel):
    _name = 'samblen.demo.loader'
    _description = 'Cargador de datos demo Samblen'

    @api.model
    def action_load(self):
        results = load_erp_demo(self.env)
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': 'Datos demo Samblen',
                       'message': ' | '.join(results), 'sticky': True},
        }
