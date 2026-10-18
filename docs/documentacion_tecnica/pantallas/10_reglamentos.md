# 10 · Reglamentos (administración)

| | |
|---|---|
| **Ruta** | `GET /admin/reglamentos` · `POST /admin/reglamentos/guardar` · `POST /admin/reglamentos/<id>/borrar` |
| **Acceso** | Solo ADM (otros: 403; sin sesión: login) |
| **Vista** | `app/admin.py` |
| **Plantilla** | `app/templates/admin/reglamentos.html` |
| **Mockup** | No hay (especificación: «Página de reglamento») |

## Propósito
Definir los juegos. Es lo que hace **genérico** al gestor: cada reglamento indica qué stats tiene un miembro.

## Listado
Juego · Año · Versión · Stats de un miembro (en el orden escrito) · Observaciones · Nº de campañas que lo usan ·
**Editar** · **Eliminar** (solo si ninguna campaña lo usa). Botones **+ Nuevo reglamento** y **← Volver al perfil**.

## Popup alta / edición
| Campo | Reglas | Destino |
|---|---|---|
| Nombre del juego | Obligatorio, máx. 150 | `regla_descripcion` |
| Año de creación | Obligatorio, entero | `regla_anyo` |
| Versión | Obligatorio, máx. 50 | `regla_version` |
| Observaciones | Opcional, máx. 255 | `regla_observaciones` |
| Stats de un miembro (JSON) | Debe ser un **objeto JSON** `{…}` o vacío | `regla_stats_especificos` |

Ejemplos:
```json
{"m": 4, "ha": 4, "hp": 3, "f": 3, "r": 3, "h": 1, "i": 4, "a": 1, "l": 7}
{"velocidad": 20, "giros": "45°", "blindaje": 5, "escudos": 2, "torretas": 1, "impactos_totales": 6, "impactos_actuales": 6}
```
- **Claves** = columnas de stats de la ficha de banda.
- **Valores** = valores por defecto al contratar; su tipo (número o texto) define el tipo de campo.

## Detalle técnico: orden de las claves
`jsonb` reordena las claves. Al guardar se añade `regla_info.orden_stats` con la lista de claves en el
orden escrito (`regla_info = COALESCE(regla_info,'{}') || {"orden_stats": […]}` al editar), y al leer
`helpers.definicion_stats()` reconstruye el orden. El popup recibe los datos con `{{ datos|tojson }}`.

## Validaciones y mensajes
- JSON inválido o que no sea objeto → «El JSON de stats no es válido (…). Ejemplo: {"m": 4, …}».
- Faltan obligatorios → «Nombre del juego, año y versión son obligatorios.»
- Borrar uno en uso → «No se puede eliminar: hay campañas que usan este reglamento.»
- Éxito: «Reglamento creado.», «Reglamento actualizado.», «Reglamento eliminado.»

## Nota
Cambiar los stats de un reglamento con bandas existentes no modifica sus miembros: las columnas nuevas
aparecen vacías y las eliminadas dejan de mostrarse.
