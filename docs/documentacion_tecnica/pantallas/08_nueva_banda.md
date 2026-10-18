# 08 · Nueva banda

| | |
|---|---|
| **Ruta** | `GET/POST /banda/nueva` |
| **Acceso** | Usuario con sesión |
| **Vista** | `bandas.nueva` — `app/bandas.py` |
| **Plantilla** | `app/templates/banda_nueva.html` |
| **Mockup** | No hay (especificación: «Página Nueva banda») |

## Propósito
Crear una banda propia en una campaña.

## Formulario

| Campo | Reglas | Destino |
|---|---|---|
| Nombre de la banda | Obligatorio, máx. 150, único en la campaña | `banda_nombre` |
| Banda (tipo) | Obligatorio, texto libre, máx. 150 (p. ej. «Mercenarios de Reikland») | `banda_tipo` |
| Campaña | Desplegable, obligatorio | `campana_id` |

**Campañas ofrecidas**: estado `INSCRIPCION` o `ABIERTA` **y** donde el usuario no tenga ya una banda activa.

Botones **Confirmar** y **Cancelar** (vuelve al perfil).

## Al confirmar (una sola transacción)
1. Inscribe al usuario en la campaña: `INSERT INTO campanas_usuarios … ON CONFLICT (campana_id, usuario_id) DO NOTHING`.
2. Crea la banda con `banda_tesoreria = campana_tesoreria_inicial` y `banda_estado = 1` (Activa).
3. Anota en el historial: «Crea la banda con tesorería inicial N».
4. Redirige a la [ficha de banda](09_ficha_banda.md).

## Reglas
- Una banda activa por usuario y campaña (índice único parcial en BBDD). Si su banda queda **Destruida**
  (desde la ficha), la campaña vuelve a ofrecerse y puede crear otra.
- Si la campaña elegida no está en la lista permitida, se rechaza aunque se manipule el formulario.

## Mensajes
«Banda «X» creada.», «Indica el nombre, el tipo de banda y una campaña disponible.»,
«Ya existe una banda con ese nombre en la campaña.»
Sin campañas disponibles: explicación y botón Volver.
