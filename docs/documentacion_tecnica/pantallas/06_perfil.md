# 06 · Perfil de usuario (dashboard)

| | |
|---|---|
| **Ruta** | `GET /perfil` · `POST /perfil/editar` |
| **Acceso** | Usuario con sesión (si no, a login) |
| **Vista** | `dashboard.perfil`, `dashboard.perfil_editar` — `app/dashboard.py` |
| **Plantilla** | `app/templates/perfil.html` |
| **Mockup** | `docs/material_base/03_perfil_gestor_generico.png` |

## Propósito
Panel personal tras iniciar sesión: campañas, bandas y datos del usuario.

## Bloque 1 · Mis campañas
Campañas donde el usuario es gestor, suplente o está inscrito. Por cada una: nombre (temporada), estado,
«gestor» si lo es, contador de **mensajes al comisario sin leer**, botones **Ver** y
**Gestionar campaña** (gestor/suplente/ADM). Botón general **Gestión de campañas** → [07](07_gestion_campanas.md).

## Bloque 2 · Mis bandas
Tabla: Nombre banda (enlace) · Tipo · Campaña · Reglas · Año. Las destruidas en gris con distintivo.
Orden: activas primero. Botón **+ Crear nueva banda** → [08](08_nueva_banda.md).

## Bloque 3 · Mis datos
Formulario `POST /perfil/editar`:

| Campo | Reglas |
|---|---|
| Nombre | Obligatorio, máx. 100 |
| Email | Obligatorio, máx. 150, único (minúsculas) |

Actualiza también el nombre en la sesión. Mensajes: «Datos actualizados.», «Nombre y email son obligatorios.»,
«No se pudo actualizar (¿email ya en uso?).»

## Bloque adicional · Opciones de administrador (solo ADM)
- **Reglamentos** → [10](10_reglamentos.md)
- **Notificaciones (N)** → [11](11_notificaciones.md) (N = sin leer y sin campaña; resaltado si hay)
- **Copia de seguridad BBDD** → [14](14_salud_backup.md)

## Notas
El cambio de contraseña no está en el perfil: se hace con el flujo de recuperación ([12](12_acceso.md)).
