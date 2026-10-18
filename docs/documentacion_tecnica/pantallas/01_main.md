# 01 · Página Main (campañas)

| | |
|---|---|
| **Ruta** | `GET /` |
| **Acceso** | Público |
| **Vista** | `public.index` — `app/public.py` |
| **Plantilla** | `app/templates/index.html` |
| **Mockup** | `docs/material_base/01_portada_gestor_generico.png` |

## Propósito
Punto de entrada. Lista todas las campañas del gestor para que cualquier visitante pueda consultarlas.

## Contenido
Tabla de una columna de ancho completo con:

| Columna | Origen |
|---|---|
| Nombre de campaña | `campanas.campana_nombre` (enlace a `/campana/<id>`) |
| Nombre de reglas | `reglas.regla_descripcion` + `(regla_version)` |
| Año de campaña | `campanas.campana_temporada` |

Consulta: `campanas LEFT JOIN reglas`, ordenado por temporada descendente y nombre.

## Acciones
- Clic en una campaña → [02 · Campaña](02_campana.md).
- Cabecera: **Login** (sin sesión) o **Mi perfil / Salir** (con sesión).

## Estados vacíos
«No hay campañas creadas.»

## Notas
Si `DATABASE_URL` falta, la consulta devuelve vacío y se ve el estado vacío; usar `/salud` para distinguirlo
([14 · Diagnóstico](14_salud_backup.md)).
