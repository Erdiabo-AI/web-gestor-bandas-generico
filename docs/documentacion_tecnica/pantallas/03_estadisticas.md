# 03 · Estadísticas de campaña

| | |
|---|---|
| **Ruta** | `GET /campana/<uuid:campana_id>/estadisticas` |
| **Acceso** | Público |
| **Vista** | `public.estadisticas` — `app/public.py` |
| **Plantilla** | `app/templates/estadisticas.html` |
| **Mockup** | No hay (definido en `PENDIENTES.md`, decisión H1) |

## Propósito
Resumen del rendimiento de cada banda en la campaña.

## Contenido

| Columna | Cálculo |
|---|---|
| Banda | Nombre (enlace a la ficha) + distintivo si está destruida |
| Tipo | `banda_tipo` |
| Batallas jugadas | Nº de `batallas_bandas` de la banda cuya batalla está **confirmada** |
| Victorias | Ídem con `batalla_banda_ganador = true` |
| Ganancias totales | Σ `batalla_banda_ganancias` en batallas confirmadas |
| Bajas | Nº de miembros de la banda en estado `3` (Muerto) |

Orden: victorias desc., ganancias desc., nombre.

```sql
FROM bandas b
LEFT JOIN batallas_bandas bb ON bb.banda_id = b.banda_id
LEFT JOIN batallas bt ON bt.batalla_id = bb.batalla_id AND bt.batalla_estado = 1
-- count(bt.batalla_id), count(...) FILTER (WHERE bb.batalla_banda_ganador), SUM(...) FILTER (...)
```

## Acciones
**← Volver** a la campaña.

## Notas
Las actas en borrador no cuentan. Las bandas sin batallas aparecen con ceros.
