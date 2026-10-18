# 14 · Diagnóstico (/salud) y copia de seguridad

## /salud

| | |
|---|---|
| **Ruta** | `GET /salud` |
| **Acceso** | Público (no muestra secretos) |
| **Vista** | `public.salud` — `app/public.py` |
| **Respuesta** | JSON |

| Respuesta | HTTP | Significado | Qué hacer |
|---|---|---|---|
| `{"estado":"ok"}` | 200 | BBDD configurada, accesible y con el esquema | — |
| `{"estado":"sin_bd","detalle":"Falta la variable DATABASE_URL"}` | 503 | La variable no llega al despliegue | Crear `DATABASE_URL` (nombre exacto) en Vercel y hacer Redeploy |
| `{"estado":"error_bd","detalle":"OperationalError"}` | 503 | La variable existe pero no conecta | Revisar el valor (host `-pooler`, `sslmode=require`, sin comillas) o la contraseña |
| `{"estado":"sin_tablas", …}` | 503 | Conecta pero la BBDD está vacía | Ejecutar `db/schema.sql` |

Útil tras cada despliegue o cambio de variables.

## Copia de seguridad

| | |
|---|---|
| **Ruta** | `GET /admin/backup.sql` |
| **Acceso** | Solo ADM (botón «Copia de seguridad BBDD» del perfil) |
| **Vista** | `admin.backup_sql` — `app/admin.py` |
| **Respuesta** | Descarga `gestorbandas_backup_AAAAMMDD_HHMM.sql` |

Genera un volcado con `INSERT` de todas las tablas del esquema `public`:
- Las tablas se ordenan **topológicamente** según sus claves foráneas (primero las referenciadas).
- UUID y JSONB se convierten a literales SQL con `cursor.mogrify`.
- Todo dentro de `BEGIN; … COMMIT;`, con el número total de filas al final.

### Restaurar
Sobre una BBDD **vacía**:
```
psql "$DATABASE_URL" -f db/schema.sql
psql "$DATABASE_URL" -f gestorbandas_backup_AAAAMMDD_HHMM.sql
```

## Nota
Neon tiene además su propio historial de restauración (*branching / point-in-time restore*), útil si se
necesita volver a un momento concreto.
