# -*- coding: utf-8 -*-
"""Datos de demostración para los 15 módulos del RFP.

Cada sección es independiente e idempotente (marca en ir.config_parameter):
si una app de Odoo no está instalada, la sección se omite y se puede volver
a correr después desde Concretera > Configuración > Cargar datos demo.
"""
import logging
import random
from datetime import timedelta

from odoo import fields

_logger = logging.getLogger(__name__)

VENDORS = [
    ('Cementos del Centro S.A. de C.V. (ficticio)', 'Cemento'),
    ('Agregados Valle Poblano S.A. de C.V. (ficticio)', 'Agregados'),
    ('Aditivos Técnicos para Concreto S.A. de C.V. (ficticio)', 'Aditivos'),
    ('Aceros y Mallas de Puebla S.A. de C.V. (ficticio)', 'Acero'),
    ('Refacciones Pesadas del Golfo S.A. de C.V. (ficticio)', 'Refacciones'),
]

DEPARTMENTS = {
    'Dirección': ['Director General'],
    'Ventas': ['Gerente Comercial', 'Ejecutivo de Ventas', 'Ejecutivo de Ventas',
               'Ejecutivo de Ventas'],
    'Planta Concretera': ['Jefe de Planta', 'Dosificador', 'Laboratorista'],
    'Prefabricados': ['Jefe de Producción', 'Supervisor de Calidad', 'Operario'],
    'Logística y Flotilla': ['Coordinador de Logística', 'Jefe de Taller',
                             'Mecánico'],
    'Obra': ['Residente de Obra', 'Residente de Obra', 'Supervisor de Obra'],
    'Compras y Almacén': ['Comprador', 'Almacenista'],
    'Administración y Finanzas': ['Contador', 'Tesorero', 'Auxiliar Contable'],
    'Sistemas': ['Jefe de Sistemas', 'Soporte Técnico'],
}

NAMES = ['Alejandro Ortiz', 'Beatriz Morales', 'Carlos Domínguez', 'Diana Rosales',
         'Eduardo Pineda', 'Fernanda Castillo', 'Gerardo Salazar', 'Hilda Vargas',
         'Iván Contreras', 'Josefina Ávila', 'Karla Medina', 'Luis Navarro',
         'Mariana Espinoza', 'Nicolás Fuentes', 'Olga Herrera', 'Pablo Ibarra',
         'Raquel Lozano', 'Sergio Camacho', 'Teresa Aguirre', 'Ulises Bravo',
         'Verónica Ríos', 'Wenceslao Cortés', 'Ximena Paredes']

LEADS = [
    ('Concreto para nave industrial 1,200 m3', 2160000, 'Calificado'),
    ('Losas prefabricadas fraccionamiento 300 viviendas', 3400000, 'Propuesta'),
    ('Pavimento hidráulico municipio - licitación', 1850000, 'Nuevo'),
    ('Tubería de concreto drenaje pluvial 2 km', 960000, 'Propuesta'),
    ('Cimentación torre 12 niveles', 1420000, 'Calificado'),
    ('Concreto estampado plaza comercial', 380000, 'Nuevo'),
    ('Firme para bodega 4,000 m2', 720000, 'Ganado'),
    ('Bordillos y guarniciones vialidad', 210000, 'Nuevo'),
    ('Concreto FC 300 puente vehicular', 1150000, 'Calificado'),
    ('Casa habitación particular 40 m3', 78000, 'Ganado'),
]

HELPDESK = [
    ('No timbra factura de cliente con régimen 626', '3'),
    ('Usuario de obra no ve sus órdenes de trabajo', '2'),
    ('Error al importar reporte de Frumecar Cloud', '2'),
    ('Solicitud de nuevo reporte de m3 por vendedor', '1'),
    ('Alta de usuario para nuevo residente', '1'),
    ('Impresora de etiquetas QR no imprime en almacén', '1'),
]


def _done(env, key):
    return env['ir.config_parameter'].sudo().get_param('samblen_demo.' + key)


def _mark(env, key):
    env['ir.config_parameter'].sudo().set_param('samblen_demo.' + key, '1')


def _section(env, key, models, func):
    if _done(env, key):
        return 'ya cargado'
    missing = [m for m in models if m not in env]
    if missing:
        return 'omitido (instalar: %s)' % ', '.join(missing)
    try:
        with env.cr.savepoint():
            func(env)
        _mark(env, key)
        return 'ok'
    except Exception as e:  # noqa: BLE001
        _logger.warning('Demo Samblen [%s]: %s', key, e)
        return 'error: %s' % e


def _product(env, name, ptype='consu', storable=True, price=0.0, uom=None):
    vals = {'name': name, 'type': ptype, 'list_price': price,
            'standard_price': price}
    if ptype == 'consu':
        vals['is_storable'] = storable
    if uom:
        vals['uom_id'] = uom.id
    return env['product.product'].create(vals)


# ------------------------------------------------------------------ CRM (M1)
def _crm(env):
    Stage = env['crm.stage']
    stages = {s.name: s for s in Stage.search([])}
    for name in ['Nuevo', 'Calificado', 'Propuesta', 'Ganado']:
        if name not in stages:
            stages[name] = Stage.create({'name': name,
                                         'is_won': name == 'Ganado'})
    tag_c = env['crm.tag'].create({'name': 'Concreto premezclado'})
    tag_p = env['crm.tag'].create({'name': 'Prefabricados'})
    partners = env['res.partner'].search([('customer_rank', '>', 0)], limit=8)
    for i, (name, amount, stage) in enumerate(LEADS):
        lead = env['crm.lead'].create({
            'name': name, 'type': 'opportunity',
            'partner_id': partners[i % len(partners)].id if partners else False,
            'expected_revenue': amount,
            'stage_id': stages[stage].id,
            'tag_ids': [(6, 0, [(tag_p if 'prefab' in name.lower()
                                 or 'tub' in name.lower()
                                 or 'losa' in name.lower() else tag_c).id])],
            'date_deadline': fields.Date.today() + timedelta(days=7 + i * 4),
        })
        if stage in ('Nuevo', 'Calificado'):
            lead.activity_schedule('mail.mail_activity_data_call',
                                   summary='Llamar para visita a obra')


# ------------------------------------------------------- Proyectos/Obra (M3, M9)
def _projects(env):
    partners = env['res.partner'].search([('customer_rank', '>', 0)], limit=4)
    stage_names = ['Por hacer', 'En proceso', 'Liberado calidad', 'Estimado']
    stages = [env['project.task.type'].create({'name': n, 'sequence': i})
              for i, n in enumerate(stage_names)]
    obras = [
        ('OBRA-001 Torre Las Ánimas', ['Excavación', 'Cimentación', 'Columnas N1-N4',
                                       'Losa nivel 4', 'Muros de carga']),
        ('OBRA-002 Fraccionamiento Bosques de Cholula', ['Urbanización', 'Red de drenaje',
                                                         'Cimentación lote 1-20',
                                                         'Losas prefabricadas']),
        ('OBRA-003 Nave Parque Finsa', ['Trazo y nivelación', 'Zapatas', 'Firme industrial',
                                        'Juntas de control']),
        ('OBRA-004 Pavimento calle 5 de Mayo', ['Demolición', 'Base hidráulica',
                                                'Colado de losas', 'Señalamiento']),
    ]
    today = fields.Date.today()
    for i, (name, tasks) in enumerate(obras):
        project = env['project.project'].create({
            'name': name,
            'partner_id': partners[i % len(partners)].id if partners else False,
            'type_ids': [(6, 0, [s.id for s in stages])],
        })
        for j, tname in enumerate(tasks):
            stage = stages[min(j, 3)] if i < 2 else stages[0 if j > 1 else 1]
            env['project.task'].create({
                'name': tname, 'project_id': project.id,
                'stage_id': stage.id,
                'allocated_hours': 40 + 20 * j,
                'date_deadline': today + timedelta(days=10 * (j + 1)),
            })


# ------------------------------------------------- Compras y almacén (M4, M5)
def _purchase(env):
    kg = env.ref('uom.product_uom_kgm')
    acero = _product(env, 'Varilla corrugada 3/8" (kg)', price=24.5, uom=kg)
    malla = _product(env, 'Malla electrosoldada 6x6 10/10 (pza)', price=890.0)
    llanta = _product(env, 'Llanta 11R22.5 para olla (pza)', price=7800.0)
    filtro = _product(env, 'Filtro de aceite motor olla (pza)', price=650.0)
    mats = env['concrete.material'].search([]).mapped('product_id')

    def by_name(txt):
        return mats.filtered(lambda p: txt.lower() in p.name.lower())[:1]

    vendors = [env['res.partner'].create({'name': n, 'company_type': 'company',
                                          'supplier_rank': 1, 'city': 'Puebla',
                                          'country_id': env.ref('base.mx').id})
               for n, _c in VENDORS]
    orders = [
        (vendors[0], [(by_name('cemento'), 60000, 3.4)], True),
        (vendors[1], [(by_name('grava'), 120000, 0.32), (by_name('arena de r'), 100000, 0.28)], True),
        (vendors[2], [(by_name('ifoplast'), 800, 38.0), (by_name('viscoflow'), 600, 52.0)], False),
        (vendors[3], [(acero, 8000, 24.5), (malla, 120, 890.0)], True),
        (vendors[4], [(llanta, 6, 7800.0), (filtro, 12, 650.0)], False),
        (vendors[0], [(by_name('cemento'), 40000, 3.4)], None),
    ]
    for vendor, lines, state in orders:
        lines = [l for l in lines if l[0]]
        if not lines:
            continue
        po = env['purchase.order'].create({
            'partner_id': vendor.id,
            'order_line': [(0, 0, {'product_id': p.id, 'product_qty': q,
                                   'price_unit': pr}) for p, q, pr in lines],
        })
        if state is None:
            continue
        po.button_confirm()
        if state:
            for picking in po.picking_ids:
                for move in picking.move_ids:
                    move.quantity = move.product_uom_qty
                    move.picked = True
                picking.with_context(skip_backorder=True,
                                     skip_immediate=True).button_validate()
            if hasattr(po, 'action_create_invoice'):
                po.action_create_invoice()


def _warehouses(env):
    WH = env['stock.warehouse']
    main = WH.search([], limit=1)
    if main:
        main.name = 'Planta Concretera Cholula'
    for name, code in [('Planta Prefabricados Atlixco', 'PREF'),
                       ('Almacén de Obra Las Ánimas', 'OB01')]:
        if not WH.search([('code', '=', code)]):
            WH.create({'name': name, 'code': code})


# --------------------------------------------------- Prefabricados (M7)
def _prefab(env):
    tmpl_ids = [env.ref('samblen_comercial.product_prefab_losa', False),
                env.ref('samblen_comercial.product_prefab_tubo', False)]
    route = env.ref('mrp.route_warehouse0_manufacture', False)
    mats = env['concrete.material'].search([]).mapped('product_id')
    cem = mats.filtered(lambda p: 'cemento' in p.name.lower())[:1]
    arena = mats.filtered(lambda p: 'arena de r' in p.name.lower())[:1]
    grava = mats.filtered(lambda p: 'grava' in p.name.lower())[:1]
    acero = env['product.product'].search([('name', 'ilike', 'Varilla corrugada')], limit=1)
    recipes = {0: [(cem, 18), (arena, 40), (grava, 45), (acero, 3.2)],
               1: [(cem, 95), (arena, 180), (grava, 210), (acero, 12)]}
    for idx, tmpl in enumerate(tmpl_ids):
        if not tmpl:
            continue
        tmpl.write({'is_storable': True,
                    'route_ids': [(4, route.id)] if route else []})
        lines = [(0, 0, {'product_id': p.id, 'product_qty': q})
                 for p, q in recipes[idx] if p]
        bom = env['mrp.bom'].create({'product_tmpl_id': tmpl.id,
                                     'product_qty': 1.0, 'bom_line_ids': lines})
        for qty, finish in [(120, True), (80, False)]:
            mo = env['mrp.production'].create({
                'product_id': tmpl.product_variant_id.id,
                'product_qty': qty, 'bom_id': bom.id,
                'origin': 'Programa semanal prefabricados'})
            mo.action_confirm()
            if finish:
                try:
                    with env.cr.savepoint():
                        mo.qty_producing = qty
                        for m in mo.move_raw_ids:
                            m.quantity = m.product_uom_qty
                            m.picked = True
                        mo.with_context(skip_consumption=True,
                                        skip_backorder=True).button_mark_done()
                except Exception as e:  # noqa: BLE001
                    _logger.warning('Demo prefab MO: %s', e)


def _quality(env):
    tmpl = env.ref('samblen_comercial.product_prefab_tubo', False)
    vals = [
        ('Cilindro f\'c 7 días bajo especificación - lote TB-118', '2'),
        ('Fisura en tubo 60 cm - lote TB-121', '1'),
    ]
    for name, prio in vals:
        env['quality.alert'].create({
            'name': name, 'priority': prio,
            'product_tmpl_id': tmpl.id if tmpl else False,
        })


# ------------------------------------------- Flotilla y mantenimiento (M8)
def _maintenance(env):
    cat_olla = env['maintenance.equipment.category'].create({'name': 'Ollas revolvedoras'})
    cat_planta = env['maintenance.equipment.category'].create({'name': 'Equipo de planta'})
    equipments = []
    for v in env['fleet.vehicle'].search([('is_olla', '=', True)]):
        equipments.append(env['maintenance.equipment'].create({
            'name': 'Olla %s' % (v.license_plate or v.id),
            'category_id': cat_olla.id}))
    for name in ['Dosificadora Frumecar línea 1', 'Banda transportadora agregados',
                 'Montacargas prefabricados']:
        equipments.append(env['maintenance.equipment'].create({
            'name': name, 'category_id': cat_planta.id}))
    done = env.ref('maintenance.stage_3', False)
    today = fields.Date.today()
    for i, eq in enumerate(equipments):
        req = env['maintenance.request'].create({
            'name': 'Servicio preventivo 10,000 km' if i < 6 else 'Revisión mensual',
            'equipment_id': eq.id, 'maintenance_type': 'preventive',
            'schedule_date': fields.Datetime.now() + timedelta(days=3 * i + 2),
        })
        if i % 3 == 0:
            corr = env['maintenance.request'].create({
                'name': 'Correctivo: fuga hidráulica' if i < 6 else 'Correctivo: falla sensor',
                'equipment_id': eq.id, 'maintenance_type': 'corrective',
                'request_date': today - timedelta(days=5 + i),
            })
            if done:
                corr.stage_id = done.id


def _fleet_costs(env):
    Svc = env['fleet.vehicle.log.services']
    stype = env['fleet.service.type'].search([], limit=1) or \
        env['fleet.service.type'].create({'name': 'Combustible', 'category': 'service'})
    rng = random.Random(7)
    for v in env['fleet.vehicle'].search([('is_olla', '=', True)]):
        for d in range(0, 28, 7):
            Svc.create({'vehicle_id': v.id, 'service_type_id': stype.id,
                        'amount': round(rng.uniform(2800, 4200), 2),
                        'date': fields.Date.today() - timedelta(days=d),
                        'description': 'Carga de diésel'})


# ----------------------------------------------------- Facturación (M2, M10)
def _invoices(env):
    orders = env['sale.order'].search([('state', '=', 'sale')], limit=6)
    for so in orders:
        try:
            with env.cr.savepoint():
                so._create_invoices()
        except Exception as e:  # noqa: BLE001
            _logger.warning('Demo factura %s: %s', so.name, e)


# ------------------------------------------------------------- RH (M12)
def _hr(env):
    rng = random.Random(12)
    names = iter(NAMES)
    employees = env['hr.employee']
    for dept_name, jobs in DEPARTMENTS.items():
        dept = env['hr.department'].create({'name': dept_name})
        manager = False
        for job in jobs:
            emp = env['hr.employee'].create({
                'name': next(names, 'Empleado %s' % job),
                'job_title': job, 'department_id': dept.id,
                'parent_id': manager.id if manager else False,
            })
            manager = manager or emp
            employees |= emp
        dept.manager_id = manager.id if manager else False
    if 'hr.attendance' in env:
        now = fields.Datetime.now().replace(hour=0, minute=0, second=0)
        for emp in employees[:15]:
            for d in range(1, 6):
                day = now - timedelta(days=d)
                if day.weekday() >= 5:
                    continue
                start = day + timedelta(hours=14, minutes=rng.randint(0, 25))  # 8:00 CST aprox.
                env['hr.attendance'].create({
                    'employee_id': emp.id, 'check_in': start,
                    'check_out': start + timedelta(hours=9, minutes=rng.randint(0, 40))})


# ------------------------------------------------------ Mesa de ayuda (M15)
def _helpdesk(env):
    team = env['helpdesk.team'].create({'name': 'Mesa de ayuda Sistemas Samblen'})
    for name, prio in HELPDESK:
        env['helpdesk.ticket'].create({'name': name, 'team_id': team.id,
                                       'priority': prio})


SECTIONS = [
    ('crm', ['crm.lead'], _crm),
    ('projects', ['project.project'], _projects),
    ('warehouses', ['stock.warehouse'], _warehouses),
    ('purchase', ['purchase.order'], _purchase),
    ('prefab', ['mrp.production'], _prefab),
    ('quality', ['quality.alert'], _quality),
    ('maintenance', ['maintenance.request'], _maintenance),
    ('fleet_costs', ['fleet.vehicle.log.services'], _fleet_costs),
    ('invoices', ['account.move'], _invoices),
    ('hr', ['hr.employee'], _hr),
    ('helpdesk', ['helpdesk.ticket'], _helpdesk),
]


def load_erp_demo(env):
    results = []
    for key, models, func in SECTIONS:
        res = _section(env, key, models, func)
        results.append('%s: %s' % (key, res))
        _logger.info('Demo Samblen [%s]: %s', key, res)
    return results
