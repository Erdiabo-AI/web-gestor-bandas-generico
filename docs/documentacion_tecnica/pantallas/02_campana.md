# 02 · Página de campaña (clasificación)

| | |
|---|---|
| **Ruta** | `GET /campana/<uuid:campana_id>` |
| **Acceso** | Público (404 si la campaña no existe) |
| **Vista** | `public.campana` — `app/public.py` |
| **Plantilla** | `app/templates/campana.html` |
| **Mockup** | `docs/material_base/02_campana_gestor_generico.png` |

## Propósito
Muestra la campaña y su **clasificación automática por coste de la banda**.

## Contenido
- **Título**: nombre de la campaña. Subtítulo: reglamento (versión) · temporada · estado. Distintivo
  «Comisario» si el usuario tiene el modo comisario activo en ella.
- Botón **Gestionar campaña** (solo gestor, suplente o ADM) → [07](07_gestion_campanas.md) con la campaña preseleccionada.
- **Tabla de clasificación**:

| Columna | Origen |
|---|---|
| # | Posición (solo bandas activas; las destruidas muestran «—») |
| Nombre banda | `bandas.banda_nombre` (enlace a la ficha) + distintivo «Destruida» si procede |
| Tipo banda | `bandas.banda_tipo` |
| Coste | `bandas.banda_valor_banda` |
| Usuario | `usuarios.usuario_nombre` (vía `campanas_usuarios`) |

Orden: bandas activas primero, después por `banda_valor_banda` descendente y nombre.
Las filas de bandas destruidas se muestran en gris (`.fila-baja`).

- **Barra inferior**: botones **Estadísticas** ([03](03_estadisticas.md)), **Batallas** ([04](04_batallas.md))
  y **Contactar con el comisario** (popup).

## Acción: contactar con el comisario
Popup `#modal-comisario` → `POST /campana/<id>/contactar` (`campanas.contactar_comisario`).

| Campo | Reglas |
|---|---|
| Tu nombre | Opcional, máx. 100 (se rellena con el usuario en sesión) |
| Tu email | Obligatorio, máx. 150 |
| Mensaje | Obligatorio, máx. 2000 |

Crea una `notificaciones` con `notificacion_tipo='COMISARIO'` y `campana_id`. La ve el gestor en
[07 · Gestión de campañas](07_gestion_campanas.md) y un contador en su [perfil](06_perfil.md).
Mensajes: «Mensaje enviado al comisario de la campaña.» / «Escribe tu email y el mensaje…».

## Regla de cálculo del coste
`banda_valor_banda = Σ coste × cantidad` de los miembros Activos (0) y Lesionados (1). Se recalcula en
cada cambio de miembros (`servicios.recalcular_valor`).
