# Documentación técnica — Gestor de bandas genérico

| Documento | Para qué sirve |
|---|---|
| [01_DOCUMENTO_TECNICO.md](01_DOCUMENTO_TECNICO.md) | Visión completa del programa: arquitectura, módulos, modelo de datos, permisos, reglas de negocio, despliegue y mantenimiento |
| [pantallas/](pantallas/) | Un documento por pantalla: ruta, permisos, datos, acciones, validaciones y mensajes |
| [02_REPLICACION_IA.md](02_REPLICACION_IA.md) | Especificación autocontenida para que otra IA (o un desarrollador) pueda reconstruir el programa desde cero |

## Pantallas

| Nº | Pantalla | Ruta |
|---|---|---|
| 01 | [Main (campañas)](pantallas/01_main.md) | `/` |
| 02 | [Campaña (clasificación)](pantallas/02_campana.md) | `/campana/<id>` |
| 03 | [Estadísticas](pantallas/03_estadisticas.md) | `/campana/<id>/estadisticas` |
| 04 | [Batallas](pantallas/04_batallas.md) | `/campana/<id>/batallas` |
| 05 | [Acta de batalla](pantallas/05_acta.md) | `/batalla/<id>/acta` |
| 06 | [Perfil de usuario](pantallas/06_perfil.md) | `/perfil` |
| 07 | [Gestión de campañas](pantallas/07_gestion_campanas.md) | `/gestion-campanas` |
| 08 | [Nueva banda](pantallas/08_nueva_banda.md) | `/banda/nueva` |
| 09 | [Ficha de banda](pantallas/09_ficha_banda.md) | `/banda/<id>` |
| 10 | [Reglamentos (ADM)](pantallas/10_reglamentos.md) | `/admin/reglamentos` |
| 11 | [Notificaciones (ADM)](pantallas/11_notificaciones.md) | `/admin/notificaciones` |
| 12 | [Acceso: login, registro, recuperación](pantallas/12_acceso.md) | `/login`, `/registro`, `/recuperar`, `/restablecer/<token>` |
| 13 | [Legal y contacto](pantallas/13_legal_contacto.md) | `/aviso-legal`, `/privacidad`, popup de contacto |
| 14 | [Diagnóstico y copia de seguridad](pantallas/14_salud_backup.md) | `/salud`, `/admin/backup.sql` |

Mockups originales: `docs/material_base/` (solo en local, excluidos del repositorio porque contienen datos personales).
Decisiones funcionales: [../PENDIENTES.md](../PENDIENTES.md).
