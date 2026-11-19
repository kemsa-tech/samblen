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
    orders = env['sale.order'].search([('state', '=', 'sale'),
                                       ('invoice_ids', '=', False)], limit=6)
    Wizard = env['sale.advance.payment.inv']
    for so in orders:
        try:
            with env.cr.savepoint():
                ctx = {'active_model': 'sale.order', 'active_ids': so.ids}
                Wizard.with_context(**ctx).create({
                    'advance_payment_method': 'delivered',
                    'sale_order_ids': [(6, 0, so.ids)],
                }).create_invoices()
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


# ------------------------------------- Cotizador, CRM de obra y agenda (M1)
ZONES = [
    ('Puebla centro', 'Puebla, San Andrés Cholula', 8, 0.0),
    ('Cholula - Santa Isabel', 'San Pedro Cholula, Santa Isabel', 12, 0.0),
    ('Corredor industrial Huejotzingo', 'Huejotzingo, San Martín', 25, 3.0),
    ('Atlixco', 'Atlixco, Tianguismanalco', 35, 5.0),
    ('Tlaxcala sur', 'Zacatelco, Tlaxcala capital', 40, 6.0),
]

PREFABS = [
    # nombre, familia, unidad, peso kg, precio, días fabricación, existencia
    ('Block hueco 15x20x40', 'block', 'pza', 13.5, 14.5, 3, 18000),
    ('Block macizo 12x20x40', 'block', 'pza', 16.0, 16.8, 3, 6000),
    ('Adoquín hexagonal 8 cm (m2)', 'adoquin', 'm2', 180.0, 245.0, 5, 900),
    ('Adoquín rectangular 6 cm (m2)', 'adoquin', 'm2', 140.0, 210.0, 5, 400),
    ('Tubo de concreto simple 30 cm x 1.25 m', 'tubo', 'pza', 140.0, 420.0, 7, 120),
    ('Tubo de concreto reforzado 90 cm x 2.5 m', 'tubo', 'pza', 1650.0, 3850.0, 12, 10),
    ('Poste de concreto 9 m', 'poste', 'pza', 750.0, 2900.0, 10, 25),
    ('Trabe pretensada AASHTO tipo III 15 m', 'trabe', 'pza', 9800.0, 68000.0, 25, 0),
    ('Vigueta pretensada 12-4 (ml)', 'losa', 'ml', 19.0, 68.0, 4, 3500),
    ('Bovedilla de concreto 15x25x56', 'losa', 'pza', 11.0, 13.5, 3, 9000),
    ('Guarnición trapezoidal 15x20x50 cm (ml)', 'otro', 'ml', 95.0, 185.0, 6, 300),
]

NEW_LEADS = [
    # nombre, interés, tipo, zona idx, m3, resistencia, días, ingreso, fuente, etapa, es_lead
    ('Losa de entrepiso edificio de oficinas', 'concrete', 'comercial', 0, 180, '250', 20, 342000, 'utm_source_llamada', 'Visita a obra', False),
    ('Plaza comercial Atlixco - cimentación', 'both', 'comercial', 3, 420, '300', 35, 980000, 'utm_source_constructora', 'Calificado', False),
    ('Fraccionamiento 80 viviendas Huejotzingo', 'both', 'fraccionamiento', 2, 900, '200', 45, 2100000, 'utm_source_visita', 'Propuesta', False),
    ('Banquetas y guarniciones municipio Cholula', 'prefab', 'infraestructura', 1, 0, False, 30, 450000, 'utm_source_licitacion', 'Nuevo', False),
    ('Barda perimetral bodega Tlaxcala', 'prefab', 'industrial', 4, 0, False, 15, 160000, 'utm_source_llamada', 'Visita a obra', False),
    ('Ampliación nave automotriz - firme', 'concrete', 'industrial', 2, 650, '250', 25, 1230000, 'utm_source_constructora', 'Propuesta', False),
    ('Casa habitación en Lomas de Angelópolis', 'concrete', 'vivienda', 0, 35, '250', 10, 68000, 'utm_source_llamada', 'Nuevo', True),
    ('Pozos de visita drenaje sanitario', 'prefab', 'infraestructura', 3, 0, False, 40, 380000, 'utm_source_licitacion', 'Calificado', False),
    ('Pavimento estacionamiento hospital', 'concrete', 'pavimento', 1, 300, '300', 30, 610000, 'utm_source_visita', 'Visita a obra', False),
    ('Cisterna y losa de cimentación residencial', 'concrete', 'vivienda', 0, 22, '250', 8, 45000, 'utm_source_llamada', 'Nuevo', True),
]


def _comercial(env):
    today = fields.Date.today()
    now = fields.Datetime.now()
    SO = env['sale.order'].with_context(samblen_no_followup=True)

    # Zonas y lista de precios por cliente
    pl = env['product.pricelist'].create({
        'name': 'Constructoras preferentes (-3%)',
        'item_ids': [(0, 0, {'applied_on': '3_global',
                             'compute_price': 'percentage',
                             'percent_price': 3.0})]})
    zones = []
    for i, (name, note, km, pct) in enumerate(ZONES):
        zones.append(env['samblen.commercial.zone'].create({
            'name': name, 'note': note, 'distance_km': km,
            'price_adjust_pct': pct, 'sequence': i}))
    customers = env['res.partner'].search([('customer_rank', '>', 0),
                                           ('is_company', '=', True)], limit=8)
    customers[:2].write({'property_product_pricelist': pl.id})

    # Programación de planta: administrador y usuario actual
    grp = env.ref('samblen_comercial.group_plant_scheduler')
    users = env.user | env.ref('base.user_admin')
    grp.write({'user_ids' if 'user_ids' in grp._fields else 'users':
               [(4, u.id) for u in users]})

    # Catálogo de prefabricados con existencias
    wh = env['stock.warehouse'].search([('company_id', '=', env.company.id)],
                                       limit=1)
    prefab = {}
    for name, fam, unit, kg, price, days, stock in PREFABS:
        p = env['product.product'].create({
            'name': name, 'type': 'consu', 'is_storable': True,
            'is_prefab': True, 'prefab_family': fam, 'prefab_unit': unit,
            'prefab_weight_kg': kg, 'prefab_lead_days': days,
            'list_price': price, 'standard_price': round(price * 0.62, 2),
            'invoice_policy': 'order'})
        if stock and wh:
            env['stock.quant']._update_available_quantity(
                p, wh.lot_stock_id, stock)
        prefab[name] = p
    for xid, fam, kg, days in [('product_prefab_losa', 'losa', 230.0, 5),
                               ('product_prefab_tubo', 'tubo', 520.0, 8)]:
        t = env.ref('samblen_comercial.' + xid, False)
        if t:
            t.write({'prefab_family': fam, 'prefab_weight_kg': kg,
                     'prefab_lead_days': days,
                     'prefab_unit': 'm2' if fam == 'losa' else 'pza'})

    # CRM: datos de obra en las oportunidades existentes
    designs = {d.name: d for d in env['concrete.mix.design'].search([])}

    def design(key):
        for n, d in designs.items():
            if key and key in n:
                return d
        return env['concrete.mix.design']
    stages = {s.name: s for s in env['crm.stage'].search([])}
    for i, lead in enumerate(env['crm.lead'].search([('obra_name', '=', False)])):
        z = zones[i % len(zones)]
        pre = any(w in lead.name.lower() for w in ('losa', 'tub', 'bordillo'))
        lead.write({
            'samblen_interest': 'prefab' if pre else 'concrete',
            'obra_name': lead.name, 'obra_zone_id': z.id,
            'obra_distance_km': z.distance_km,
            'obra_address': z.note.split(',')[0] + ', Pue.',
            'obra_type': 'fraccionamiento' if 'fracc' in lead.name.lower()
            else 'industrial' if 'nave' in lead.name.lower() else 'comercial',
            'm3_estimated': 0 if pre else round(lead.expected_revenue / 1850),
            'concrete_design_id': False if pre else design('250').id,
            'pour_date_estimated': today + timedelta(days=10 + i * 3)})
    src = {x: env.ref('samblen_comercial.' + x, False) for x in
           ('utm_source_llamada', 'utm_source_visita', 'utm_source_constructora',
            'utm_source_licitacion')}
    tag_c = env['crm.tag'].search([('name', '=', 'Concreto premezclado')], limit=1)
    tag_p = env['crm.tag'].search([('name', '=', 'Prefabricados')], limit=1)
    sellers = env['res.users'].search([('share', '=', False)], limit=3) or env.user
    leads = env['crm.lead']
    for i, (name, interest, otype, zi, m3, res, days, amount, source, stage,
            is_lead) in enumerate(NEW_LEADS):
        z = zones[zi]
        partner = customers[i % len(customers)] if customers else False
        vals = {
            'name': name, 'type': 'lead' if is_lead else 'opportunity',
            'partner_id': partner.id if partner and not is_lead else False,
            'contact_name': 'Ing. ' + NAMES[i % len(NAMES)] if is_lead else False,
            'phone': '222 %03d %04d' % (400 + i, 1000 + i * 37),
            'samblen_interest': interest, 'obra_name': name,
            'obra_type': otype, 'obra_zone_id': z.id,
            'obra_distance_km': z.distance_km,
            'obra_address': z.note.split(',')[0] + ', Pue.',
            'm3_estimated': m3, 'concrete_design_id': design(res).id,
            'pour_date_estimated': today + timedelta(days=days),
            'expected_revenue': amount,
            'source_id': src[source].id if src.get(source) else False,
            'user_id': sellers[i % len(sellers)].id,
            'tag_ids': [(6, 0, [t.id for t in
                                ((tag_c if interest != 'prefab' else
                                  env['crm.tag']) |
                                 (tag_p if interest != 'concrete' else
                                  env['crm.tag']))])],
        }
        if not is_lead and stage in stages:
            vals['stage_id'] = stages[stage].id
        lead = env['crm.lead'].create(vals)
        leads |= lead
        if is_lead:
            lead.activity_schedule('mail.mail_activity_data_call',
                                   summary='Calificar prospecto y pedir ubicación de obra',
                                   user_id=lead.user_id.id)
    # Visitas a obra en el calendario (próximos días)
    for k, lead in enumerate(leads.filtered(
            lambda l: l.stage_id.name == 'Visita a obra')):
        lead.visit_datetime = (now + timedelta(days=1 + k)).replace(
            hour=10 + 2 * k, minute=0, second=0)
        lead.action_schedule_visit()

    # Cotizaciones de prefabricados desde CRM
    pre_leads = leads.filtered(lambda l: l.samblen_interest != 'concrete'
                               and l.partner_id)[:3]
    baskets = [
        [('Guarnición trapezoidal 15x20x50 cm (ml)', 1200),
         ('Adoquín hexagonal 8 cm (m2)', 650)],
        [('Block hueco 15x20x40', 9000), ('Block macizo 12x20x40', 1500)],
        [('Tubo de concreto reforzado 90 cm x 2.5 m', 24),
         ('Tubo de concreto simple 30 cm x 1.25 m', 80)],
    ]
    for lead, basket in zip(pre_leads, baskets):
        act = lead.action_quote_prefab()
        so = SO.browse(act['res_id'])
        so.write({'order_line': [(0, 0, {'product_id': prefab[n].id,
                                         'product_uom_qty': q})
                                 for n, q in basket],
                  'advance_pct': 30.0})
        so.action_compute_prefab()

    # Cotizaciones de concreto que muestran las reglas nuevas
    prod = {}
    for t in env['product.template'].search([('concrete_design_id', '!=', False)]):
        prod[t.concrete_design_id.id] = t.product_variant_id
    d250 = design('250')
    cases = [
        ('Cisterna particular (carga incompleta)', 2.0, zones[0], 0, False),
        ('Losa con espera en obra', 14.0, zones[1], 150, True),
        ('Firme nave Huejotzingo (zona +3%)', 42.0, zones[2], 60, True),
    ]
    for k, (obra, m3, zone, wait, ret) in enumerate(cases):
        if not customers or d250.id not in prod:
            break
        so = SO.create({
            'partner_id': customers[(k + 3) % len(customers)].id,
            'concrete_obra': obra, 'concrete_design_id': d250.id,
            'concrete_zone_id': zone.id, 'concrete_distance_km': zone.distance_km,
            'concrete_wait_minutes': wait, 'freight_retention': ret,
            'advance_pct': 50.0 if k else 100.0,
            'concrete_pour_datetime': (now + timedelta(days=3 + k)).replace(
                hour=8, minute=0, second=0),
            'concrete_tma_option_id': env.ref('samblen_comercial.opt_tma_20').id
            if env.ref('samblen_comercial.opt_tma_20', False) else False,
            'order_line': [(0, 0, {'product_id': prod[d250.id].id,
                                   'product_uom_qty': m3})]})
        so.action_compute_charges()

    # Agenda: fechas de colado en las órdenes de surtimiento
    oscs = env['concrete.supply.order'].search([('date_pour', '=', False)],
                                               order='id')
    future = 0
    for osc in oscs:
        if osc.state in ('done', 'partial', 'dosing'):
            start = osc.date_order.replace(hour=7, minute=30, second=0)
        else:
            future += 1
            start = (now + timedelta(days=future)).replace(
                hour=[7, 9, 11, 14][future % 4], minute=0, second=0)
        osc.write({'date_pour': start,
                   'date_pour_end': start + timedelta(hours=3)})
        if osc.sale_order_id and not osc.sale_order_id.concrete_pour_datetime:
            osc.sale_order_id.concrete_pour_datetime = start
        if osc.state in ('draft', 'released'):
            osc._notify_plant()
    for d in env['concrete.delivery'].search([('date_load', '=', False),
                                              ('order_id.date_pour', '!=', False)]):
        d.date_load = d.order_id.date_pour + timedelta(minutes=40 * (d.olla - 1))

    # Seguimiento del vendedor en cotizaciones enviadas o en borrador
    act = env.ref('samblen_comercial.activity_quote_followup')
    for so in env['sale.order'].search([('state', 'in', ('draft', 'sent'))]):
        if not so.activity_ids.filtered(lambda a: a.activity_type_id == act):
            so.activity_schedule(activity_type_id=act.id,
                                 user_id=so.user_id.id or env.user.id,
                                 date_deadline=today + timedelta(days=2),
                                 summary='Dar seguimiento a la cotización')


SECTIONS = [
    ('crm', ['crm.lead'], _crm),
    ('comercial', ['samblen.commercial.zone', 'crm.lead'], _comercial),
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
