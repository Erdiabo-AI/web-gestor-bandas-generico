# gestorbandasgenerico — App Flask

Gestor de fichas de control para campañas de juegos de miniaturas (Mordheim y otros),
en **Python/Flask** con **PostgreSQL (Neon)**, para desplegar en **Vercel**.
Variante simplificada de web-gestor-bellvibowl (proyecto independiente: repo, Vercel y BBDD propios).

## Organización
```
api/index.py        Entrypoint serverless (Vercel)
wsgi.py             Entrypoint local (python wsgi.py → http://127.0.0.1:5001)
vercel.json         Configuración de despliegue
requirements.txt    Dependencias
app/
  __init__.py       create_app() y blueprints
  config.py         SECRET_KEY, DATABASE_URL, APP_NAME (desde .env / variables de Vercel)
  db.py             Acceso a PostgreSQL (una conexión por petición)
  helpers.py        Permisos (login, ADM, gestor, modo comisario), estados, stats dinámicos
  servicios.py      Historial de la banda y recálculo del valor (coste)
  auth.py           Login, registro, recuperación de contraseña
  public.py         Main, campaña (clasificación), batallas, estadísticas, legal, contacto
  dashboard.py      Perfil: Mis campañas, Mis bandas, Mis datos
  campanas.py       Gestión de campañas, modo comisario, suplente, mensajes al comisario
  bandas.py         Nueva banda, ficha, edición in situ, contratar / editar / despedir miembros
  batallas.py       Crear batalla y acta (informativa: borrador / confirmada)
  admin.py          Reglamentos, notificaciones, enlace de recuperación, copia BBDD
  templates/ static/
db/schema.sql       Esquema completo de la BBDD (instalación desde cero)
db/migracion_*.sql  Migraciones aplicadas sobre la BBDD existente
docs/PENDIENTES.md  Decisiones tomadas, interpretaciones y pendientes
material_base/      Mockups y SQL original (no se despliega)
manual-mordheim/    PDFs de reglas (solo local, nunca al repo)
```

## Arranque local
```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env      (y rellenar SECRET_KEY y DATABASE_URL)
.venv\Scripts\python wsgi.py
```

## Administrador
El primer usuario se registra desde la web y se le da rol de administrador en la BBDD:
```sql
UPDATE usuarios SET usuario_rol = 'ADM' WHERE usuario_email = 'tu@email';
```
