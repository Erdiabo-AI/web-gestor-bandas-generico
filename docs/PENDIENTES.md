# Pendientes y decisiones — gestorbandasgenerico

Especificación: `material_base/Definicion_gestor-bandas.txt` e `intro_gestor-bandas.txt`.
Decisiones tomadas el 18/10/2026. ✅ = implementado y probado · ❓ = pendiente.

## Decisiones tomadas

| # | Decisión | Estado |
|---|---|---|
| C1 | Título: "Gestor de Fichas de control para campañas genérico" (ver ❓ abajo) | ✅ `APP_NAME` |
| C2 | Login en página (no popup) | ✅ |
| C3 | Registro → Página Main | ✅ |
| C4 | Crear banda en campañas en **Inscripción** y **Abierta** | ✅ |
| C5 | Temporada = año actual (editable); `campana_formato` DEFAULT 'LIBRE' | ✅ |
| C6 | "Tesorería inicial" de la campaña, copiada a cada banda al crearla | ✅ |
| C7 | Estados de miembro: 0 Activo · 1 Lesionado · 2 Despedido · 3 Muerto | ✅ |
| C8 | Armamento en `banda_lin_armamento` como lista `[{"nombre","precio"}]` | ✅ |
| H1 | Estadísticas por banda: jugadas, victorias, ganancias, bajas (actas confirmadas) | ✅ |
| H2 | Actas **informativas**: bandas vinculadas a mano, borrador/confirmada, no tocan las bandas | ✅ |
| H3 | Contratar y comprar equipo descuentan de la tesorería; tesorería editable; todo al historial | ✅ |
| H4 | Contacto con el comisario desde la página de la campaña | ✅ |
| D4 | Una banda **activa** por usuario y campaña; con la banda Destruida puede crear otra | ✅ índice único parcial |

## Interpretaciones (aplicadas por defecto, revisables)

- **Modo comisario (COM)**: no es un rol guardado. El creador, el suplente o el ADM pulsan
  «Acceder como comisario» y, mientras dura la sesión, gestionan bandas y actas de todos.
  Sin activarlo, el gestor solo edita su propia banda.
- **Suplente**: lo nombra el creador entre los inscritos (Gestión de campañas · Bloque 2).
- **Cobro al editar un miembro**: se cobra lo que sube el coste de la línea (equipo nuevo o
  más unidades). Retirar equipo **no reembolsa** solo; se corrige editando la tesorería.
- **Quién crea batallas**: cualquier participante con banda activa (se vincula la suya) o el comisario.
  Un jugador no puede quitar su propia banda del acta. Tras confirmar, solo el comisario reabre.
- **Estado de banda**: 1 Activa · 2 Destruida.
- **Orden de los stats**: jsonb no conserva el orden de las claves, así que el orden escrito
  se guarda en `regla_info.orden_stats`.
- **Usuarios del ADM**: tabla en Gestión de campañas · Bloque 3 (con enlace de recuperación).

## ❓ Pendiente de confirmar

- **Nombre del gestor**: en C1 se eligió "Gestor de Fichas de control para campañas genérico"
  y en la decisión 5 "BandasGenerico". Se usa el primero; cambiarlo es una variable (`APP_NAME`).

## Base de datos

- ✅ Migración `db/migracion_2026-10-18_base.sql` aplicada en Neon (solo la BBDD de este proyecto).
- ✅ `db/schema.sql` = esquema completo actualizado (para instalar desde cero).
- Sin uso en esta versión: `campana_logo_path`, `banda_logo_path`, `campana_ia_*`, `campana_adicional`,
  `batallas.batalla_info`, `bandas_lin.banda_lin_nivel`, `banda_lin_audit`.

## Despliegue (consultar antes)

- [ ] Repo nuevo en GitHub (no tocar `Erdiabo-AI/web-gestor-bellvibowl`).
- [ ] Proyecto nuevo en Vercel con `SECRET_KEY` y `DATABASE_URL` propias.
- [ ] Rotar la contraseña de Neon antes de producción (se compartió por chat).
- [ ] Los PDF de `manual-mordheim/` nunca al repo (excluidos en `.gitignore` / `.vercelignore`).
