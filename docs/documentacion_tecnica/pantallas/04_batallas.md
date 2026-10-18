# 04 · Batallas de campaña

| | |
|---|---|
| **Ruta** | `GET /campana/<uuid:campana_id>/batallas[?banda=<banda_id>]` |
| **Acceso** | Público (lectura). Crear: participante con banda activa o comisario |
| **Vista** | `public.batallas` — `app/public.py`; crear: `batallas.crear` — `app/batallas.py` |
| **Plantilla** | `app/templates/batallas.html` |
| **Mockup** | `docs/material_base/04_batalla_gestor_generico.png` |

## Propósito
Listado cronológico de las batallas de la campaña, con filtro y acceso al acta.

## Contenido
- Título «Batallas de campaña · [nombre]».
- Botón **Crear batalla** (si `puede_crear`).
- **Filtro por banda** (desplegable; se envía al cambiar).
- Tabla:

| Columna | Origen |
|---|---|
| Orden | `batalla_orden` |
| Escenario | `batalla_escenario` |
| Fecha | `batalla_fecha` (dd/mm/aaaa) |
| Oponentes | `string_agg` de los nombres de `batallas_bandas` |
| Ganador | `batalla_ganador` |
| Estado | Borrador (amarillo) / Confirmada (verde) |
| Observaciones | `batalla_observaciones` |
| — | Botón **Acta** → [05](05_acta.md) |

Orden: `batalla_fecha`, `batalla_orden` (cronológico). Con filtro, solo las batallas donde participa la banda.
- Botón inferior **← Volver** a la campaña.

## Acción: crear batalla
`POST /campana/<id>/batallas/crear`

| Regla | Detalle |
|---|---|
| Permiso | Comisario de la campaña, o usuario con banda **activa** en ella |
| Campaña cerrada | Solo el comisario |
| Datos iniciales | `batalla_orden = MAX + 1`, `batalla_fecha = hoy`, `batalla_escenario = 'Por definir'`, estado borrador |
| Banda propia | Si el usuario tiene banda activa, se vincula automáticamente |
| Concurrencia | Si dos altas chocan en el orden (único), se avisa y se reintenta |

Redirige al acta. Mensajes: «Necesitas una banda activa…», «La campaña está cerrada.», «No se pudo crear la batalla…».
