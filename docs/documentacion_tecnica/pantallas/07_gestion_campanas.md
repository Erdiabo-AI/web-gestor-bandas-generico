# 07 · Gestión de campañas

| | |
|---|---|
| **Ruta** | `GET /gestion-campanas[?campana=<id>]` + acciones POST |
| **Acceso** | Usuario con sesión. Bloque 2 según permisos; Bloque 3 solo ADM |
| **Vista** | `app/campanas.py` |
| **Plantilla** | `app/templates/gestion_campanas.html` |
| **Mockup** | `docs/material_base/05_gestionar_campanas_gestor_generico.png` (es una copia del de batallas; la pantalla sigue la especificación) |

## Bloque 1 · Nueva campaña
`POST /gestion-campanas/crear` (`campanas.crear`)

| Campo | Reglas | Destino |
|---|---|---|
| Nombre de la campaña | Obligatorio, máx. 150 | `campana_nombre` |
| Tesorería inicial | Número ≥ 0 (por defecto 500) | `campana_tesoreria_inicial` |
| Temporada | Por defecto el año actual, máx. 15 | `campana_temporada` |
| Reglamento | Desplegable de `reglas`, obligatorio | `regla_id` |

Se crea en estado `INSCRIPCION`, formato `LIBRE`, con el usuario como gestor. Sin reglamentos se muestra
un aviso (y al ADM un enlace para crearlos).

## Bloque 2 · Opciones de campaña
Desplegable con las campañas que el usuario **gestiona** (creador o suplente; ADM: todas). Al elegir una:

| Elemento | Ruta | Quién |
|---|---|---|
| Estado (Inscripción / Abierta / Cerrada) | `POST /gestion-campanas/<id>/estado` | gestor, suplente, ADM |
| Suplente (entre los **inscritos**) | `POST /gestion-campanas/<id>/suplente` | solo creador o ADM |
| **Acceder como comisario** / Salir del modo comisario | `POST /gestion-campanas/<id>/comisario` (`activar=1/0`) | gestor, suplente, ADM |
| Mensajes al comisario (marcar leído / eliminar) | `POST /gestion-campanas/mensaje/<nid>` (`accion=leida/borrar`) | gestor, suplente, ADM |

**Modo comisario**: añade el id de la campaña a `session["com"]`. Mientras esté activo, el usuario puede
editar todas las bandas y actas de esa campaña. En la cabecera aparece el distintivo «Modo comisario».

## Bloque 3 · Opciones de administrador (solo ADM, ancla `#bloque-3`)
- **Todas las campañas**: campaña (enlace a su Bloque 2), reglas, temporada, estado, gestor, nº de bandas.
- **Todos los usuarios**: nombre, email, rol, «Solicitada dd/mm hh:mm» si pidió recuperar la contraseña,
  botón **Enlace de contraseña** → `POST /admin/usuarios/<id>/reset` (ver [12](12_acceso.md)).

## Validaciones y errores
- Estado fuera de la lista → 400. Usuario sin permiso → 403. Campaña inexistente → 404.
- Suplente no inscrito → «El suplente debe estar inscrito en la campaña.»

## Mensajes
«Campaña «X» creada en estado Inscripción.», «Estado de la campaña actualizado.»,
«Comisario suplente actualizado.», «Modo comisario activado en «X»…», «Modo comisario desactivado.»
