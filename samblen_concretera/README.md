# Samblen Concretera (PoC) — Odoo 19

Módulo de prueba de concepto para la concretera de Samblen. Cubre el flujo:

**Cotización → Orden de Surtimiento de Concreto (OSC) → Dosificación (Frumecar) → Control de desviaciones → Reporte unificado.**

## Qué incluye

- **Diseños de mezcla** (`concrete.mix.design`) — fórmula por m³ con tolerancia configurable.
- **Órdenes de Surtimiento** (`concrete.supply.order`) — cliente, obra, producto (FC/TMA/Rev), cantidad, estados (Solicitado → Liberado → Dosificando → Parcial → Surtido), ubicación origen/destino, panel de vehículos/ollas con **Remisión Frumecar**.
- **Remisiones/Ollas** (`concrete.delivery`) — dosificado real por material, comparado contra el diseño; aviso automático (mensaje + actividad) al salir de tolerancia.
- **Reporte Concretera** y **Consumo de material** — lista + tabla dinámica.
- **Escenario de ejemplo** precargado: FC 250, 14 m³ para Cholula, 2 ollas (una con desviación en cemento).

## Punto de integración Frumecar

La acción **"Recibir remisión (Frumecar)"** en cada olla **simula** la llegada del dosificado real.
En producción, ese mismo punto lo dispara el **middleware** conectado al *puerto bidireccional* de Frumecar
(Frumecar → Odoo). El envío del diseño (Odoo → Frumecar) sale del botón **"Enviar diseño a Frumecar"** de la OSC.

## Instalación (Odoo.sh)

1. Rama **dev** → Odoo.sh construye automáticamente.
2. Apps → actualizar lista → instalar **Samblen Concretera**.
3. Abrir el menú **Concretera** → Órdenes de Surtimiento → OSC/22254.

> PoC para demostración. La versión productiva extenderá `sale.order` (cotización nativa),
> usará BoM de MRP para los diseños e Inventario/Compras/Contabilidad nativos.

## Alcance / roadmap

Ver `Plan de Implementacion Samblen Concretera Odoo 19.docx` (fases 1–7 + integración Frumecar).
