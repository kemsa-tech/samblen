# -*- coding: utf-8 -*-
import logging
import random
from datetime import timedelta

from odoo import fields

from .erp_demo import load_erp_demo

_logger = logging.getLogger(__name__)

# (nombre, resistencia, factor de cemento vs FC 250, precio por m3)
DESIGNS = [
    ('D-FC150-20', '150 kg/cm2', 0.78, 1650.0),
    ('D-FC200-20', '200 kg/cm2', 0.89, 1750.0),
    ('D-FC300-20', '300 kg/cm2', 1.12, 1990.0),
]

CUSTOMERS = [
    ('Constructora Atlixco Norte S.A. de C.V.', 'company', 'Atlixco'),
    ('Desarrollos Cholula del Valle S.A. de C.V.', 'company', 'San Pedro Cholula'),
    ('Grupo Edificador Angelópolis S.A. de C.V.', 'company', 'Puebla'),
    ('Obras y Pavimentos San Andrés S.A. de C.V.', 'company', 'San Andrés Cholula'),
    ('Vivienda Sustentable del Altiplano S.A. de C.V.', 'company', 'Tlaxcala'),
    ('Inmobiliaria Valle de Atoyac S.A. de C.V.', 'company', 'Puebla'),
    ('Ing. Marco Antonio Ruiz Téllez', 'person', 'Santa Isabel Cholula'),
    ('Arq. Laura Méndez Ortega', 'person', 'Huejotzingo'),
]

OBRAS = [
    ('Torre habitacional Las Ánimas - losa nivel 4', 26.4),
    ('Fraccionamiento Bosques de Cholula - cimentación', 12.8),
    ('Nave industrial Parque Finsa - firme', 31.5),
    ('Pavimento calle 5 de Mayo - tramo 2', 9.6),
    ('Conjunto Altiplano etapa 3 - zapatas', 44.0),
    ('Plaza comercial Atoyac - columnas', 15.2),
    ('Casa habitación Santa Isabel - losa', 6.3),
    ('Casa de campo Huejotzingo - firme', 22.7),
]

OLLAS = [
    ('CR-05', 'Hernández Cruz M.'),
    ('CR-06', 'Ramírez Solís A.'),
    ('CR-07', 'Flores Vega J. L.'),
    ('CR-08', 'Torres Aguilar E.'),
]


def _ref(env, xmlid):
    return env.ref(xmlid, raise_if_not_found=False)


def _opt(env, xmlid):
    rec = _ref(env, 'samblen_comercial.' + xmlid)
    return rec.id if rec else False


def _create_designs(env):
    """Clona el diseño FC 250 ajustando cemento y agua por resistencia."""
    base = _ref(env, 'samblen_concretera.design_fc250')
    base_prod = _ref(env, 'samblen_concretera.product_concreto_fc250')
    products = {'250': base_prod}
    designs = {'250': base}
    if not base:
        return designs, products
    for name, res, factor, price in DESIGNS:
        key = res.split(' ')[0]
        lines = []
        for line in base.line_ids:
            qty = line.qty_per_m3
            if line.material_id.code == 'CEM':
                qty = round(qty * factor, 1)
            elif line.material_id.code == 'AGUA':
                qty = round(qty * (1 + (factor - 1) * 0.3), 1)
            lines.append((0, 0, {'material_id': line.material_id.id,
                                 'qty_per_m3': qty}))
        design = env['concrete.mix.design'].create({
            'name': name, 'resistance': res, 'tma': '20 mm',
            'revenimiento': '14 cm', 'tolerance': 3.0, 'line_ids': lines,
        })
        designs[key] = design
        products[key] = env['product.template'].create({
            'name': 'Concreto FC %s' % key,
            'type': 'service', 'list_price': price, 'is_concrete': True,
            'concrete_design_id': design.id, 'invoice_policy': 'order',
        })
    return designs, products


def _create_fleet(env):
    model = _ref(env, 'samblen_concretera.model_olla7')
    if not model:
        return
    for plate, driver in OLLAS:
        partner = env['res.partner'].create({'name': driver})
        env['fleet.vehicle'].create({
            'model_id': model.id, 'license_plate': plate, 'is_olla': True,
            'capacity_m3': 7.0, 'driver_id': partner.id,
        })


def _fake_dosage(delivery, rng, deviate):
    """Dosificado real: dentro de +/-2% salvo cuando se fuerza desviación."""
    design = delivery.order_id.design_id
    vals = []
    bad = rng.choice(['CEM', 'AGUA', 'ARE-RIO']) if deviate else None
    for line in design.line_ids:
        var = rng.uniform(-0.02, 0.02)
        if line.material_id.code == bad:
            var = rng.choice([-1, 1]) * rng.uniform(0.04, 0.07)
        vals.append({
            'delivery_id': delivery.id,
            'material_id': line.material_id.id,
            'qty_real': round(line.qty_per_m3 * delivery.volume_m3 * (1 + var), 2),
        })
    delivery.env['concrete.delivery.dosage'].create(vals)


def _receive(delivery):
    method = getattr(delivery, 'action_receive_remisión', None) or \
        getattr(delivery, 'action_receive_remision', None)
    if method:
        method()


def _setup_company(env):
    """Empresa demo en México con catálogo de cuentas e IVA mexicanos."""
    company = env.company
    mx = env.ref('base.mx')
    pue = env['res.country.state'].search(
        [('country_id', '=', mx.id), ('code', '=', 'PUE')], limit=1)
    for user in (env.user | env.ref('base.user_admin')).filtered(
            lambda u: not u.tz):
        user.tz = 'America/Mexico_City'
    company.write({'name': 'Grupo Samblen (DEMO)', 'country_id': mx.id,
                   'state_id': pue.id or False, 'city': 'Santa Isabel Cholula',
                   'street': 'Carr. Federal Puebla-Atlixco km 20'})
    if company.chart_template != 'mx' and not env['account.move.line'].search_count(
            [('company_id', '=', company.id)]):
        try:
            with env.cr.savepoint():
                env['account.chart.template'].try_loading('mx', company)
        except Exception as e:  # noqa: BLE001
            _logger.warning('Demo Samblen: no se cargó el catálogo MX: %s', e)


def post_init_hook(env):
    rng = random.Random(2026)
    _setup_company(env)
    designs, products = _create_designs(env)
    _create_fleet(env)

    flete = _ref(env, 'samblen_concretera.product_flete')
    if flete:
        flete.write({'freight_base': 350.0, 'freight_per_km': 38.0,
                     'freight_free_km': 8.0})
    # El hook corre como usuario del sistema: los permisos van al administrador
    sellers = env.user | (_ref(env, 'base.user_admin') or env['res.users'])
    sellers.write({'samblen_max_discount': 5.0})
    group = _ref(env, 'samblen_comercial.group_discount_approver')
    if group:
        field = 'user_ids' if 'user_ids' in group._fields else 'users'
        group.write({field: [(4, u.id) for u in sellers]})

    partners = env['res.partner']
    for name, ctype, city in CUSTOMERS:
        partners |= env['res.partner'].create({
            'name': name, 'company_type': ctype, 'city': city,
            'country_id': env.ref('base.mx').id, 'customer_rank': 1,
        })

    now = fields.Datetime.now()
    keys = ['150', '200', '250', '250', '300', '200', '250', '150',
            '250', '300', '200', '250', '250', '150']
    # estado objetivo por cotización
    plan = ['done', 'done', 'done', 'partial', 'done', 'done', 'partial',
            'dosing', 'done', 'released', 'approval', 'sent', 'draft', 'draft']
    m3_options = [7.0, 10.5, 14.0, 21.0, 28.0, 35.0]

    for i, target in enumerate(plan):
        partner = partners[i % len(partners)]
        obra, km = OBRAS[i % len(OBRAS)]
        product = products.get(keys[i]) or products['250']
        if not product:
            continue
        m3 = m3_options[i % len(m3_options)]
        disc = 10.0 if target == 'approval' else (rng.choice([0.0, 0.0, 3.0, 5.0]))
        try:
            with env.cr.savepoint():
                so = env['sale.order'].create({
                    'partner_id': partner.id,
                    'concrete_obra': obra,
                    'concrete_distance_km': km,
                    'concrete_tipo': 'externo',
                    'concrete_design_id': product.concrete_design_id.id,
                    'concrete_tma_option_id': _opt(env, 'opt_tma_10' if i % 4 == 0 else 'opt_tma_20'),
                    'concrete_rev_option_id': _opt(env, 'opt_rev_18' if i % 3 == 0 else 'opt_rev_14'),
                    'concrete_tiro_id': _opt(env, ['opt_tiro_pluma', 'opt_tiro_directo',
                                                   'opt_tiro_canalon', 'opt_tiro_estac'][i % 4]),
                    'concrete_additive_ids': [(6, 0, [x for x in [
                        _opt(env, 'opt_add_fpp') if i % 2 == 0 else False,
                        _opt(env, 'opt_add_imp') if i % 5 == 1 else False,
                        _opt(env, 'opt_add_ret') if i % 6 == 2 else False] if x])],
                    'concrete_shift': 'night' if i % 5 == 0 else (
                        'sunday' if i % 7 == 0 else 'day'),
                    'order_line': [(0, 0, {
                        'product_id': product.product_variant_id.id,
                        'product_uom_qty': m3,
                        'discount': disc,
                    })],
                })
                so.action_compute_charges()
                if target == 'draft':
                    continue
                if target == 'sent':
                    so.state = 'sent'
                    continue
                if target == 'approval':
                    so.action_request_discount_approval()
                    continue
                so.action_confirm()
                osc = so.concrete_osc_ids[:1]
                days_ago = 28 - i * 2
                when = now - timedelta(days=max(days_ago, 0), hours=rng.randint(0, 6))
                so.date_order = when
                if not osc or target == 'released':
                    continue
                osc.date_order = when
                osc.action_send_frumecar()
                ollas = osc.delivery_ids.sorted('olla')
                if target == 'dosing':
                    ollas = ollas[:0]
                elif target == 'partial':
                    ollas = ollas[:max(1, len(ollas) // 2)]
                for n, delivery in enumerate(ollas):
                    _fake_dosage(delivery, rng, deviate=rng.random() < 0.2)
                    km0 = rng.randint(30000, 90000)
                    delivery.write({'km_start': km0,
                                    'km_end': km0 + round(km * 2 + rng.uniform(0, 4), 1),
                                    'diesel_l': round(km * 0.55 + rng.uniform(2, 6), 1)})
                    _receive(delivery)
                    delivery.date_load = when + timedelta(minutes=45 * n)
        except Exception as e:  # noqa: BLE001
            _logger.warning('Demo Samblen: no se pudo crear el escenario %s: %s', i, e)
    _logger.info('Demo Samblen: escenario concretera cargado.')
    load_erp_demo(env)
