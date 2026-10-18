# 11 · Notificaciones (administración)

| | |
|---|---|
| **Ruta** | `GET /admin/notificaciones` + `POST …/<nid>/leida`, `POST …/<nid>/borrar`, `POST /admin/notificaciones/leidas` |
| **Acceso** | Solo ADM |
| **Vista** | `app/admin.py` |
| **Plantilla** | `app/templates/admin/notificaciones.html` |
| **Mockup** | No hay (heredada de BellviBowl) |

## Propósito
Bandeja del administrador con los mensajes del formulario de **Contacto** y las solicitudes de
**recuperación de contraseña**.

## Contenido
Tarjetas (máx. 200), primero las no leídas y después por fecha descendente:
- Distintivo **Recuperación** o **Contacto**, remitente (nombre, usuario o email), «nueva», fecha y hora.
- Mensaje, «Responder a: email» y, si estaba registrado, su nombre de usuario.
- Botones **Marcar leída** y **Eliminar** (con confirmación). Arriba: **Marcar todas leídas** y **← Volver**.

## Filtro
Solo `notificaciones` con `campana_id IS NULL`. Los mensajes al comisario de una campaña se gestionan en
[07 · Gestión de campañas](07_gestion_campanas.md).

## Relación con otras pantallas
- El contador «Notificaciones (N)» del [perfil](06_perfil.md) cuenta las no leídas de esta bandeja.
- Una solicitud de recuperación se atiende generando el enlace en Gestión de campañas · Bloque 3 ([12](12_acceso.md)).
