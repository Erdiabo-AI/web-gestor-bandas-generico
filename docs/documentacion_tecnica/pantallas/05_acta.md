# 05 · Acta de batalla

| | |
|---|---|
| **Ruta** | `GET/POST /batalla/<uuid:batalla_id>/acta` |
| **Acceso** | Lectura pública. Edición: ver permisos |
| **Vista** | `batallas.acta` — `app/batallas.py` |
| **Plantilla** | `app/templates/acta.html` |
| **Mockup** | No hay (especificación: «Página Introducir Acta») |

## Propósito
Registrar los datos de una batalla. **Es informativa: no modifica las bandas** (decisión H2).

## Contenido
- Título «Acta de batalla nº N · [campaña]» y estado (Borrador / Confirmada).
- **Bloque 1 · Datos de la batalla**: fecha, escenario.
- **Bandas implicadas** (tabla):

| Columna | Campo del formulario | Destino |
|---|---|---|
| Banda / tipo | — | enlace a la ficha |
| Usuario | — | propietario |
| Ganancias | `ganancias_<bb_id>` (número) | `batalla_banda_ganancias` |
| Miembros muertos o lisiados | `bajas_<bb_id>` (texto, máx. 1000) | `batalla_banda_info = {"bajas": …}` |
| Ganador | `ganador_<bb_id>` (casilla, admite varios) | `batalla_banda_ganador` |
| — | botón `accion=quitar:<bb_id>` | borra la vinculación |

- Selector + **Vincular banda** (`accion=anadir`, `banda_id`): bandas de la campaña aún no vinculadas.
- **Comentarios**: `observaciones` → `batalla_observaciones`.

## Permisos

| Quién | Puede |
|---|---|
| Anónimo / no participante | Solo ver (campos deshabilitados). Un POST anónimo redirige a login |
| Participante (banda vinculada) | Editar mientras esté en **borrador**; no puede quitar su propia banda |
| Comisario (o ADM) | Editar en borrador, quitar cualquier banda, **eliminar** la batalla (borrador), **reabrir** una confirmada |

## Acciones (`POST`, campo `accion`)

| Acción | Efecto |
|---|---|
| `guardar` | Guarda fecha, escenario, observaciones, y por banda ganancias/bajas/ganador. `batalla_ganador` = nombres de las ganadoras separados por comas |
| `anadir` | Guarda y vincula `banda_id` (debe ser de la misma campaña; `ON CONFLICT DO NOTHING`) |
| `quitar:<id>` | Guarda y desvincula (prohibido para la banda propia salvo comisario) |
| `confirmar` | Guarda y pone `batalla_estado = 1`; vuelve al listado |
| `reabrir` | Solo comisario: `batalla_estado = 0` |
| `eliminar` | Solo comisario y en borrador: borra la batalla (cascada a `batallas_bandas`) |

Todas las acciones de edición guardan antes los datos del formulario (`_guardar`).
Fecha inválida → se mantiene la anterior; escenario vacío → se mantiene el anterior.

## Mensajes
«Acta guardada.», «Acta confirmada.», «Acta reabierta para edición.», «Batalla eliminada.»,
«No puedes quitar tu propia banda del acta.». Confirmaciones en el navegador antes de confirmar, quitar y eliminar.
