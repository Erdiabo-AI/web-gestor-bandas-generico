# Especificación para replicar el programa (entregable a otra IA)

> **Instrucciones para la IA que lea este documento.**
> Eres un desarrollador Python/Flask. Tu tarea es construir desde cero una aplicación web idéntica en
> funcionamiento a la descrita aquí, lista para desplegar en Vercel con PostgreSQL. Este documento es
> **autocontenido**: no necesitas el código original. Sigue las secciones en orden, respeta los nombres
> de tablas, columnas, rutas y códigos de estado (son el contrato), y valida el resultado con la lista de
> comprobación de la sección 12. Si algo no está especificado, elige la opción más simple y documéntala.
> Responde y documenta en español.

---

## 1. Qué es

**Gestor de Fichas de control para campañas genérico**: web para llevar campañas de juegos de miniaturas por
bandas (Mordheim, Battlefleet Gothic…). Es genérica porque cada juego («reglamento») define en JSON qué
stats tiene un miembro de banda.

- **Parte 1 · pública (sin login):** listado de campañas, clasificación por coste, batallas, actas (lectura),
  estadísticas, contacto con el administrador y con el comisario de una campaña.
- **Parte 2 · gestor (con login):** crear campañas; crear y gestionar la banda propia (miembros, armamento,
  tesorería con historial); actas de batalla informativas; gestión de la campaña por su creador con
  «modo comisario»; administración de reglamentos.

## 2. Stack y restricciones

- Python 3.12, **Flask 3.0.3**, **psycopg2-binary 2.9.9**, python-dotenv 1.0.1, **reportlab 5.0.0** (PDF). Sin ORM: SQL parametrizado.
- PostgreSQL (Neon). UUID como claves (`gen_random_uuid()`), JSONB para datos variables.
- Plantillas Jinja2 + CSS propio + JavaScript básico (sin frameworks de frontend).
- Despliegue en Vercel con `@vercel/python` (serverless): **no hay disco persistente** y cada petición abre
  y cierra su conexión a la BBDD.
- Variables de entorno: `SECRET_KEY`, `DATABASE_URL` (host *pooler* de Neon, `?sslmode=require`), `APP_NAME` (opcional).
- Idioma de la interfaz: español.

## 3. Estructura de archivos a crear

```
api/index.py         Entrada Vercel (Anexo C: incluye corrección de ruta)
wsgi.py              Entrada local (puerto 5001)
vercel.json          (Anexo D)
requirements.txt     Flask==3.0.3, psycopg2-binary==2.9.9, python-dotenv==1.0.1, reportlab==5.0.0
.env.example         SECRET_KEY=, DATABASE_URL=, APP_NAME=
.gitignore           __pycache__, .venv, .env, .env.* (salvo .env.example), .vercel, *.pdf
.vercelignore        .venv .env .env.* .claude db docs wsgi.py *.md *.pdf
app/__init__.py      create_app(): Config, teardown close_db, 7 blueprints, filtro |info, context processor
app/config.py        SECRET_KEY (o aleatoria), DATABASE_URL, APP_NAME
app/db.py            (Anexo B)
app/helpers.py       decoradores, permisos, estados, stats, filtro info, a_entero
app/servicios.py     anotar_historial, recalcular_valor, historial
app/auth.py | public.py | dashboard.py | campanas.py | bandas.py | batallas.py | admin.py | pdf.py
app/templates/       base.html, index, campana, estadisticas, batallas, acta, perfil,
                     gestion_campanas, banda_nueva, banda, legal, auth/{login,register,recuperar,restablecer},
                     admin/{reglamentos,notificaciones}
app/static/css/style.css
db/schema.sql        (Anexo A)
```

## 4. Modelo de datos

Crea las tablas exactamente como en el **Anexo A**. Resumen de relaciones:
`reglas 1-n campanas 1-n campanas_usuarios n-1 usuarios`; `campanas 1-n bandas` (cada banda pertenece a un
`campanas_usuarios`); `bandas 1-n bandas_lin`; `campanas 1-n batallas 1-n batallas_bandas n-1 bandas`;
`notificaciones` opcionalmente ligada a `usuarios` (remitente) y a `campanas` (mensaje al comisario).

### 4.1 Códigos de estado (contrato)
| Campo | Valores |
|---|---|
| `campanas.campana_estado` | `INSCRIPCION`, `ABIERTA`, `CERRADA` |
| `bandas.banda_estado` | `1` Activa, `2` Destruida |
| `bandas_lin.banda_lin_estado` | `0` Activo, `1` Lesionado, `2` Despedido, `3` Muerto. **En plantilla** = {0, 1} |
| `batallas.batalla_estado` | `0` Borrador, `1` Confirmada |
| `usuarios.usuario_rol` | `STD`, `ADM` |
| `notificaciones.notificacion_tipo` | `CONTACTO`, `RECUPERACION`, `COMISARIO` |

### 4.2 Formatos JSON
- `reglas.regla_stats_especificos`: objeto `{"stat": valor_por_defecto}`. Ej. Mordheim
  `{"m":4,"ha":4,"hp":3,"f":3,"r":3,"h":1,"i":4,"a":1,"l":7}`; Battlefleet `{"velocidad":20,"giros":"45°","blindaje":5}`.
- `reglas.regla_info`: `{"orden_stats": ["m","ha",…]}`. **Obligatorio**: `jsonb` reordena las claves por
  longitud; guarda el orden escrito al crear/editar y úsalo al mostrar columnas.
- `bandas_lin.banda_lin_stats`: objeto con las claves del reglamento. Convierte cada valor al tipo del valor por
  defecto (int, float, bool o texto ≤ 50).
- `bandas_lin.banda_lin_armamento`: lista `[{"nombre": str, "precio": int}]` (admite repetidos).
- `batallas_bandas.batalla_banda_info`: `{"bajas": str}` o NULL.
- Escribe JSONB con `psycopg2.extras.Json(...)`.

## 5. Capa de datos (contrato de `app/db.py`, ver Anexo B)
- `query(sql, params=None, one=False)`: SELECT con `RealDictCursor`; ante `psycopg2.Error` hace rollback y devuelve `[]`/`None`.
- `execute(sql, params=None, returning=False, commit=True)`: con `commit=False` deja la sentencia en la transacción
  abierta. **Las operaciones compuestas** (contratar = insertar + cobrar + historial + recalcular) se encadenan con
  `commit=False` y la última confirma. Si algo falla, `close_db` cierra sin confirmar.
- Sin `DATABASE_URL`: `query` devuelve vacío y `execute` lanza `RuntimeError`.

## 6. Permisos

| Función (helpers.py) | Regla |
|---|---|
| `login_required` | Sin `session["user"]` → flash + redirect a `/login` |
| `admin_required` | Sin sesión → login; rol ≠ ADM → 403 |
| `es_gestor_campana(campana, user)` | ADM, o `usuarios_gestor_id` o `usuarios_gestor_suplente_id` = user |
| `es_comisario(campana_id, user)` | ADM, o `campana_id` ∈ `session["com"]` |
| `puede_editar_banda(banda, user)` | Propietario (usuario de su `campanas_usuarios`) o `es_comisario` |

- La sesión guarda `user = {id, nombre, rol}` y `com = [ids de campaña]`. Login y logout borran `com`.
- «Acceder como comisario» solo lo pueden activar quienes cumplen `es_gestor_campana`.
- Comprueba los permisos en el servidor en cada POST (403), no solo ocultando botones.

## 7. Reglas de negocio (implementar todas)

1. **Campaña nueva**: estado `INSCRIPCION`, formato `LIBRE` (DEFAULT), temporada = año actual (editable),
   `campana_tesoreria_inicial` ≥ 0, gestor = creador. Requiere un reglamento existente.
2. **Banda nueva**: solo en campañas `INSCRIPCION` o `ABIERTA` donde el usuario **no** tenga banda activa.
   Inscribe al usuario (`INSERT … ON CONFLICT (campana_id, usuario_id) DO NOTHING`), crea la banda con
   `banda_tesoreria = campana_tesoreria_inicial`, `banda_estado = 1`, y anota historial.
   El índice único parcial `bandas_una_activa_por_usuario` garantiza una banda activa por usuario y campaña;
   con la banda Destruida puede crear otra. Nombre único por campaña.
3. **Coste unitario del miembro** = precio base + Σ precio del armamento. El precio base no se guarda
   (al editar = coste − Σ armamento).
4. **Valor de banda** = Σ `coste × cantidad` de miembros en estado 0 o 1. Recalcular tras cada cambio de miembros.
5. **Contratar**: inserta (estado 0) y descuenta `coste × cantidad` de la tesorería.
6. **Editar miembro**: cobra solo el incremento `coste×cantidad nuevo − anterior` si es > 0 y el miembro sigue en
   plantilla. Retirar equipo no reembolsa. Detecta equipo comprado/retirado comparando listas de nombres (multiconjunto).
7. **Despedir**: estado 2.
8. **Tesorería**: siempre editable a mano (puede quedar negativa con aviso). Los cobros se hacen en una sola sentencia (`SET banda_tesoreria = banda_tesoreria - x RETURNING banda_tesoreria`).
8b. **Concurrencia**: toda operación que modifica una banda empieza con `SELECT 1 FROM bandas WHERE banda_id=%s FOR UPDATE`. En `base.html`, cada formulario POST se envía una sola vez (marca `data-enviando`; desactiva botones con `setTimeout(…,0)` para conservar el valor del botón pulsado; reactiva en `pageshow`). Despedir es idempotente.
8c. **Categoría del miembro**: `banda_lin_categoria` varchar(50) opcional, texto libre con `<datalist>` («Héroe», «Secuaz» + usadas); columna en la ficha y en el PDF; cambios al historial.
9. **Historial** (`bandas.banda_audit`, texto): cada acción añade
   `to_char(now() AT TIME ZONE 'Europe/Madrid','DD/MM/YYYY HH24:MI') || ' · ' || usuario || ' · ' || texto || '\n'`.
   Textos: «Crea la banda con tesorería inicial N»; «Contrata «X» (Tipo) ×n por T [equipo: …] · tesorería A → B»;
   «Edita «X»: coste 49 → 54; compra Escudo · cargo 5 · tesorería A → B»; «Despide a «X» (Tipo)»;
   «Edita la banda: tesorería A → B (edición manual); estado Activa → Destruida». Se muestra en orden inverso.
10. **Actas informativas**: nunca modifican bandas.
11. **Crear batalla**: comisario o usuario con banda activa en la campaña (no en `CERRADA` salvo comisario).
    `orden = MAX+1` (subconsulta en el INSERT), fecha hoy, escenario «Por definir», vincula la banda propia.
12. **Editar acta**: en borrador, el comisario o un participante con banda vinculada. Un jugador no quita su propia
    banda. Confirmar → estado 1 (bloqueada). Reabrir y eliminar (solo en borrador): solo comisario.
    `batalla_ganador` = nombres de las bandas marcadas ganadoras, separados por «, ».
13. **Estadísticas**: por banda, con actas **confirmadas**: jugadas, victorias, Σ ganancias; bajas = miembros en estado 3.
14. **Clasificación**: bandas activas primero, luego `banda_valor_banda` desc., nombre.
15. **Notificaciones**: contacto del pie → `CONTACTO` sin campaña (ADM); botón de campaña → `COMISARIO` con
    `campana_id` (lo ve el gestor en Gestión de campañas; el ADM no lo ve en su bandeja).
16. **Recuperación sin correo**: `/recuperar` anota `reset_solicitado` + notificación `RECUPERACION` (sin revelar si el
    email existe). El ADM genera token `secrets.token_urlsafe(32)`, guarda `sha256(token)` en `reset_token_hash`, caduca a
    las 24 h. `/restablecer/<token>` fija la contraseña (≥ 8, confirmada) y limpia los campos `reset_*`.
17. **Contraseñas**: `werkzeug.security.generate_password_hash` / `check_password_hash`, mínimo 8 caracteres.
18. **Registro**: rol STD, abre sesión y redirige a `/`. `IntegrityError` → «Ese email ya está registrado…»;
    otro error → «No se pudo registrar por un problema con la base de datos. Avisa al administrador.» + log.

## 8. Rutas (todas con `<uuid:…>` en los identificadores)

| Método · Ruta | Endpoint | Acceso | Función |
|---|---|---|---|
| GET `/` | public.index | público | Tabla de campañas (nombre→enlace, reglas+versión, temporada) |
| GET `/campana/<id>` | public.campana | público | Clasificación + botones Estadísticas, Batallas, Contactar comisario (popup); «Gestionar campaña» si gestor |
| GET `/campana/<id>/batallas?banda=` | public.batallas | público | Listado cronológico (fecha, orden), filtro por banda, oponentes (`string_agg`), estado, botón Acta; «Crear batalla» si procede |
| GET `/campana/<id>/estadisticas` | public.estadisticas | público | Regla 13 |
| GET `/salud` | public.salud | público | JSON `ok` / `sin_bd` / `error_bd` / `sin_tablas` (503 salvo ok); sin secretos |
| GET `/aviso-legal`, `/privacidad` | public.* | público | Textos legales (sin ánimo de lucro; RGPD; una cookie técnica) |
| POST `/contactar` | public.contactar | público | Regla 15; vuelve al referrer solo si es del mismo host |
| GET/POST `/login` | auth.login | público | → `/perfil` |
| GET/POST `/registro` | auth.register | público | Regla 18 |
| GET `/logout` | auth.logout | — | Borra user y com |
| GET/POST `/recuperar`, `/restablecer/<token>` | auth.* | público | Regla 16 |
| GET `/perfil` | dashboard.perfil | login | Mis campañas (con nº mensajes sin leer si gestor), Mis bandas, Mis datos; bloque ADM (Reglamentos, Notificaciones (N), Copia BBDD) |
| POST `/perfil/editar` | dashboard.perfil_editar | login | Nombre y email |
| GET `/gestion-campanas?campana=` | campanas.gestion_campanas | login | Bloque 1 nueva campaña; Bloque 2 campaña gestionada (estado, suplente, comisario, mensajes); Bloque 3 (ADM) todas las campañas y todos los usuarios con «Enlace de contraseña» |
| POST `/gestion-campanas/crear` | campanas.crear | login | Regla 1 |
| POST `/gestion-campanas/<id>/estado` | campanas.cambiar_estado | gestor | Estado ∈ lista (si no, 400) |
| POST `/gestion-campanas/<id>/suplente` | campanas.suplente | creador o ADM | Usuario inscrito o vacío |
| POST `/gestion-campanas/<id>/comisario` | campanas.comisario | gestor | `activar=1/0` sobre `session["com"]` |
| POST `/gestion-campanas/mensaje/<nid>` | campanas.mensaje | gestor de esa campaña | `accion=leida/borrar` |
| POST `/campana/<id>/contactar` | campanas.contactar_comisario | público | Regla 15 |
| GET/POST `/banda/nueva` | bandas.nueva | login | Regla 2 |
| GET `/banda/<id>` | bandas.ver | público | Ficha (sección 9) |
| GET `/banda/<id>/pdf` | bandas.pdf | público | PDF A4 apaisado de la ficha (sección 9.3, punto 5) |
| POST `/banda/<id>/editar` | bandas.editar | propietario/COM | Nombre, tipo, tesorería, estado, observaciones + historial |
| POST `/banda/<id>/contratar` | bandas.contratar | propietario/COM | Reglas 3-5, 9 |
| POST `/banda/<id>/miembro/<lid>/editar` | bandas.editar_miembro | propietario/COM | Regla 6 |
| POST `/banda/<id>/miembro/<lid>/despedir` | bandas.despedir | propietario/COM | Regla 7 |
| POST `/campana/<id>/batallas/crear` | batallas.crear | ver regla 11 | → acta |
| GET/POST `/batalla/<id>/acta` | batallas.acta | lectura pública | `accion` = guardar / anadir / quitar:<bb_id> / confirmar / reabrir / eliminar |
| GET `/admin/reglamentos` | admin.reglamentos | ADM | Listado + popup |
| POST `/admin/reglamentos/guardar` | admin.reglamento_guardar | ADM | Valida objeto JSON; guarda `orden_stats` |
| POST `/admin/reglamentos/<id>/borrar` | admin.reglamento_borrar | ADM | Solo si ninguna campaña lo usa |
| GET `/admin/notificaciones` (+ `/<nid>/leida`, `/<nid>/borrar`, `/leidas`) | admin.* | ADM | Solo `campana_id IS NULL` |
| POST `/admin/usuarios/<id>/reset` | admin.generar_reset | ADM | Regla 16; vuelve a Gestión de campañas `#bloque-3` |
| GET `/admin/backup.sql` | admin.backup_sql | ADM | INSERTs de todas las tablas en orden topológico por FK, en una transacción |

## 9. Interfaz

### 9.1 Layout (`base.html`)
- **Cabecera** gris oscuro: título (`APP_NAME`) a la izquierda; a la derecha, sin sesión **Login**; con sesión
  distintivo amarillo **Modo comisario** (si `session["com"]` no está vacío), nombre, **Mi perfil**, **Salir**.
- Mensajes flash (success/danger/warning/info) bajo la cabecera.
- **Pie**: Contacto (abre popup), Aviso legal, Política de privacidad; mismo fondo que el cuerpo.
- **Popups**: `.modal` (fondo semitransparente) + `.modal-box`; `data-abrir="id"` abre, `data-cerrar` o clic en el
  fondo cierra; funciones globales `abrirModal`/`cerrarModal`; bloque `{% block scripts %}`.
- Filtro Jinja `|info`: dict → `clave: valor · …`, lista → `a, b`.
- Pasar datos a JS con `<script type="application/json" id="…">{{ datos|tojson }}</script>`.

### 9.2 Estilo
Variables: `--bg:#e8e4bc` (beige), `--surface:#fff`, `--ink:#1f2937`, `--muted:#6b7280`, `--line:#e5e7eb`,
`--bar:#3f3f46` (cabecera), `--accent:#7c3aed` (botón principal). Tarjetas blancas con borde suave y radio 0.5rem;
tablas blancas con cabecera gris en mayúsculas pequeñas; contenedor máx. 1100 px; envolver tablas anchas en
`.tabla-scroll` (overflow-x); filas de bajas/destruidas en gris; distintivos `.badge`, `.badge-ok` (verde),
`.badge-pend` (amarillo). Adaptable a móvil.

### 9.3 Ficha de banda (la pantalla más compleja)
1. Datos con **edición in situ**: botón «Editar datos» alterna una clase `.editando` que oculta la vista y muestra
   el formulario (nombre, tipo, tesorería, estado, observaciones).
2. Tabla de miembros en plantilla: Orden, Nombre (+Lesionado), Tipo, Cant., **una columna por stat** (mayúsculas,
   orden de `orden_stats`), Armamento `nombre (precio)`, Exp., Coste (`×n = total`), Notas, Editar / Despedir (con confirm).
3. **Popup de miembro** compartido para contratar y editar (cambia `action`, título y botón):
   orden (siguiente libre), nombre, tipo, categoría, cantidad, precio base, stats (`stat_0…`, `type=number` si el valor por
   defecto es número; precargados con el valor por defecto o el actual), filas dinámicas de armamento
   (`arm_nombre[]`, `arm_precio[]`, añadir/quitar), **coste en vivo** = precio + Σ armamento, `× cantidad = total`,
   aviso «se descontarán N de la tesorería» (nuevo: total; edición: total − total inicial si > 0), experiencia,
   estado (solo editar), notas, observaciones.
4. Plegable «Bajas (n)» y plegable «Historial (n)».
5. Botón **📄 Generar PDF** (pestaña nueva): con reportlab, A4 apaisado — título, tabla de datos, observaciones,
   miembros (una columna por stat, ancho medido con `stringWidth` de la palabra más larga, `_` → espacio),
   bajas, historial completo y pie con fecha y nº de página. Helvetica no tiene «→»: sustituir por «->».
   Nombre de archivo ASCII (`unicodedata.normalize('NFKD')`).

### 9.4 Otras pantallas
Ver la tabla de rutas. Gestión de campañas en rejilla de dos columnas (Bloque 1 | Bloque 2) y Bloque 3 debajo.
Reglamentos: tabla + popup (nombre del juego, año, versión, observaciones, textarea JSON con ejemplo).
Acta: tabla de bandas implicadas con inputs por fila (`ganancias_<id>`, `bajas_<id>`, `ganador_<id>`), selector para
vincular, comentarios, botones Guardar / Guardar y confirmar / Eliminar (comisario) / Reabrir (comisario, si confirmada);
campos deshabilitados si no puede editar.

## 10. Despliegue en Vercel (problemas conocidos)
1. `vercel.json` del Anexo D (todo a `api/index.py`).
2. **El proxy puede entregar `PATH_INFO=/api/index`** en lugar de la ruta real: usa el WSGI intermedio del Anexo C,
   que la recupera de las cabeceras. Sin esto, todas las páginas darían 404.
3. Las variables se crean **una a una con el nombre exacto** (`DATABASE_URL`, `SECRET_KEY`) en Production; tras
   crearlas, **Redeploy**. Verificar con `/salud`.
4. Inicializar la BBDD con el Anexo A; el primer ADM se asigna por SQL.

## 11. Orden de construcción recomendado
1. Esquema (Anexo A) y `db.py`. 2. `config`, `create_app`, `base.html`, CSS. 3. Auth completo.
4. Reglamentos (ADM). 5. Gestión de campañas. 6. Nueva banda y ficha (historial, cobros, valor).
7. Clasificación y Main. 8. Batallas y acta. 9. Estadísticas. 10. Contacto, comisario, notificaciones,
legal, `/salud`, copia de seguridad. 11. Despliegue.

## 12. Lista de comprobación (aceptación)
Con usuarios ADM, Gestor (STD que crea la campaña), Jugador1 y Jugador2:

- [ ] JSON de stats inválido rechazado; un STD recibe 403 en `/admin/reglamentos`.
- [ ] Campaña creada en Inscripción, formato LIBRE, tesorería inicial 500.
- [ ] Jugador1 crea banda en campaña en Inscripción → tesorería 500; la campaña deja de ofrecérsele; no puede crear otra.
- [ ] Contratar precio 35 + Espada 10 + Daga 2 + Daga 2 → coste 49, armamento con dos dagas, tesorería 451.
- [ ] Contratar grupo ×3 de 25 + Daga 2 → tesorería 370, valor 130.
- [ ] Editar añadiendo Escudo 5 → tesorería 365; historial con «compra Escudo», «cargo 5», «tesorería 370 → 365».
- [ ] Tesorería editada a mano a 400 → historial «(edición manual)».
- [ ] Jugador2 y el Gestor (sin modo comisario) reciben 403 al editar la banda de Jugador1.
- [ ] Despedir el grupo → estado 2, valor 54; la ficha muestra «Bajas (1)».
- [ ] Columnas de stats en orden `M HA HP F R H I A L`; Battlefleet guarda `{"velocidad":20,"giros":"90°","blindaje":6}`.
- [ ] Gestor cambia estado a Abierta; un jugador recibe 403. Gestor activa modo comisario → aparece el aviso y puede editar.
- [ ] Jugador1 crea batalla (su banda vinculada), vincula a Jugador2, guarda ganancias 60, ganador y bajas; la tesorería no cambia.
- [ ] Jugador1 no puede quitar su banda; confirma; ya no puede editar (403); el comisario reabre.
- [ ] Clasificación por coste; batallas con «Banda A, Banda B»; filtro por banda; estadísticas 1/1/60/0.
- [ ] Banda destruida → puede crear otra; no puede reactivar la vieja teniendo otra activa.
- [ ] Mensaje al comisario visible para el gestor (y contador en su perfil), no en la bandeja del ADM ni para otros jugadores.
- [ ] Suplente (inscrito) puede activar el modo comisario pero no cambiar el suplente.
- [ ] Bloque 3 visible solo al ADM; un reglamento en uso no se puede borrar; la copia SQL incluye `batallas_bandas`.
- [ ] El registro redirige a `/`; `/salud` responde `ok`.
- [ ] Dos ediciones simultáneas que añaden una Espada (10) → un solo cargo; cinco contrataciones simultáneas de 20 → tesorería exacta (−100) e historial encadenado; doble despedir → una sola línea.
- [ ] Tres clics seguidos en «Enviar» del contacto → un único mensaje.

---

# Anexos (copiados del código fuente)

## Anexo A · `db/schema.sql`

```sql
-- =============================================================================
--  gestorbandasgenerico · Esquema completo (PostgreSQL)
--  = material_base/mordheim.sql + db/migracion_2026-10-18_base.sql
--  Para una BBDD nueva basta con este fichero.
--
--  Códigos de estado:
--    campanas.campana_estado      INSCRIPCION · ABIERTA · CERRADA
--    bandas.banda_estado          1 Activa · 2 Destruida
--    bandas_lin.banda_lin_estado  0 Activo · 1 Lesionado · 2 Despedido · 3 Muerto
--    batallas.batalla_estado      0 Borrador · 1 Confirmada
--    usuarios.usuario_rol         STD · ADM  (COM es un modo de sesión, no un rol)
-- =============================================================================

CREATE TABLE public.reglas (
	regla_id uuid DEFAULT gen_random_uuid() NOT NULL,
	regla_anyo int4 NOT NULL,
	regla_descripcion varchar(150) NOT NULL,
	regla_version varchar(50) NOT NULL,
	regla_observaciones varchar(255) NULL,
	regla_stats_especificos jsonb,      -- {"m": 4, "ha": 4, ...}: claves = stats, valores = por defecto
	regla_info jsonb,
	CONSTRAINT reglas_pkey PRIMARY KEY (regla_id)
);

CREATE TABLE public.usuarios (
	usuario_id uuid DEFAULT gen_random_uuid() NOT NULL,
	usuario_nombre varchar(100) NOT NULL,
	usuario_email varchar(150) NOT NULL,
	usuario_password_hash varchar(255) NOT NULL,
	usuario_rol varchar(20) DEFAULT 'STD'::character varying NULL,
	reset_token_hash varchar(64) NULL,
	reset_expira timestamp NULL,
	reset_solicitado timestamp NULL,
	CONSTRAINT usuarios_pkey PRIMARY KEY (usuario_id),
	CONSTRAINT usuarios_usuario_email_key UNIQUE (usuario_email)
);

CREATE TABLE public.campanas (
	campana_id uuid DEFAULT gen_random_uuid() NOT NULL,
	regla_id uuid NOT NULL,
	campana_nombre varchar(150) NOT NULL,
	campana_temporada varchar(15) NOT NULL,
	campana_formato varchar(20) DEFAULT 'LIBRE' NOT NULL,
	campana_estado varchar(20) DEFAULT 'INSCRIPCION'::character varying NOT NULL,
	campana_logo_path varchar(200) NULL,
	usuarios_gestor_id uuid NOT NULL,
	usuarios_gestor_suplente_id uuid NULL,
	campana_ia_clave text NULL,
	campana_ia_activa bool DEFAULT true NOT NULL,
	campana_adicional jsonb NULL,
	campana_tesoreria_inicial int4 DEFAULT 0 NOT NULL,
	CONSTRAINT campanas_pkey PRIMARY KEY (campana_id),
	CONSTRAINT fk_campana_regla FOREIGN KEY (regla_id) REFERENCES public.reglas(regla_id),
	CONSTRAINT fk_campana_gestor FOREIGN KEY (usuarios_gestor_id) REFERENCES public.usuarios(usuario_id),
	CONSTRAINT campanas_usuarios_gestor_suplente_id_fkey FOREIGN KEY (usuarios_gestor_suplente_id) REFERENCES public.usuarios(usuario_id) ON DELETE SET NULL
);

CREATE TABLE public.campanas_usuarios (
	campana_usuario_id uuid DEFAULT gen_random_uuid() NOT NULL,
	campana_id uuid NOT NULL,
	usuario_id uuid NOT NULL,
	fecha_inscripcion date NOT NULL,
	usuario_estado int4 DEFAULT 1 NULL,
	CONSTRAINT campanas_usuarios_campana_id_usuario_id_key UNIQUE (campana_id, usuario_id),
	CONSTRAINT campanas_usuarios_pkey PRIMARY KEY (campana_usuario_id),
	CONSTRAINT fk_lu_campana FOREIGN KEY (campana_id) REFERENCES public.campanas(campana_id) ON DELETE CASCADE,
	CONSTRAINT fk_lu_usuario FOREIGN KEY (usuario_id) REFERENCES public.usuarios(usuario_id) ON DELETE CASCADE
);

CREATE TABLE public.notificaciones (
	notificacion_id uuid DEFAULT gen_random_uuid() NOT NULL,
	notificacion_tipo varchar(15) DEFAULT 'CONTACTO'::character varying NOT NULL,
	remitente_nombre varchar(100) NULL,
	remitente_email varchar(150) NULL,
	usuario_id uuid NULL,
	mensaje text NOT NULL,
	fecha timestamp DEFAULT now() NULL,
	leida bool DEFAULT false NULL,
	campana_id uuid NULL,               -- con valor: mensaje al comisario de esa campaña
	CONSTRAINT notificaciones_pkey PRIMARY KEY (notificacion_id),
	CONSTRAINT notificaciones_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(usuario_id) ON DELETE SET NULL,
	CONSTRAINT fk_notif_campana FOREIGN KEY (campana_id) REFERENCES public.campanas(campana_id) ON DELETE CASCADE
);

CREATE TABLE public.bandas (
	banda_id uuid DEFAULT gen_random_uuid() NOT NULL,
	campana_id uuid NOT NULL,
	campana_usuario_id uuid NOT NULL,
	banda_nombre varchar(150) NOT NULL,
	banda_tipo varchar(150) NOT NULL,
	banda_valor_banda int4 DEFAULT 0 NULL,
	banda_tesoreria int4 DEFAULT 0 NULL,
	banda_estado int4 DEFAULT 1 NOT NULL,
	banda_observaciones text NULL,
	banda_info jsonb,
	banda_logo_path varchar(200) NULL,
	banda_audit text NULL,              -- historial: una línea por acción
	CONSTRAINT bandas_campana_id_banda_nombre_key UNIQUE (campana_id, banda_nombre),
	CONSTRAINT bandas_pkey PRIMARY KEY (banda_id),
	CONSTRAINT fk_eq_campana FOREIGN KEY (campana_id) REFERENCES public.campanas(campana_id) ON DELETE CASCADE,
	CONSTRAINT fk_eq_lu FOREIGN KEY (campana_usuario_id) REFERENCES public.campanas_usuarios(campana_usuario_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX bandas_una_activa_por_usuario ON public.bandas (campana_usuario_id) WHERE banda_estado = 1;

CREATE TABLE public.bandas_lin (
	banda_lin_id uuid DEFAULT gen_random_uuid() NOT NULL,
	banda_id uuid NOT NULL,
	banda_lin_orden int4 NOT NULL,
	banda_lin_nombre varchar(150) NOT NULL,
	banda_lin_subtipo varchar(150) NOT NULL,
	banda_lin_categoria varchar(50) NULL,   -- p. ej. «Héroe», «Secuaz» (texto libre)
	banda_lin_cantidad int4 NOT NULL,
	banda_lin_coste int4 NOT NULL,      -- coste unitario total = precio base + armamento
	banda_lin_experiencia int4 DEFAULT 0 NULL,
	banda_lin_nivel int4 DEFAULT 1 NULL,
	banda_lin_estado int2 DEFAULT 0 NULL,
	banda_lin_observaciones text NULL,
	banda_lin_stats jsonb,
	banda_lin_armamento jsonb,          -- [{"nombre": "Hacha", "precio": 5}, ...]
	banda_lin_notas text NULL,
	banda_lin_audit text NULL,
	CONSTRAINT bandas_lin_pkey PRIMARY KEY (banda_lin_id),
	CONSTRAINT fk_banda_lin FOREIGN KEY (banda_id) REFERENCES public.bandas(banda_id) ON DELETE CASCADE
);

CREATE TABLE public.batallas (
	batalla_id uuid DEFAULT gen_random_uuid() NOT NULL,
	campana_id uuid NOT NULL,
	batalla_orden int4 NOT NULL,
	batalla_escenario varchar(50) NOT NULL,
	batalla_observaciones text NULL,
	batalla_ganador varchar(200),
	batalla_info jsonb,
	batalla_fecha date NOT NULL,
	batalla_estado int2 DEFAULT 0 NOT NULL,
	CONSTRAINT batalla_pkey PRIMARY KEY (batalla_id),
	CONSTRAINT batallas_campana_orden_key UNIQUE (campana_id, batalla_orden),
	CONSTRAINT fk_batalla_campana FOREIGN KEY (campana_id) REFERENCES public.campanas(campana_id) ON DELETE CASCADE
);

CREATE TABLE public.batallas_bandas (
	batalla_banda_id uuid DEFAULT gen_random_uuid() NOT NULL,
	batalla_id uuid NOT NULL,
	banda_id uuid NOT NULL,
	batalla_banda_ganancias int4 DEFAULT 0 NOT NULL,
	batalla_banda_ganador bool DEFAULT false NOT NULL,
	batalla_banda_info jsonb NULL,      -- {"bajas": "miembros muertos o lisiados"}
	CONSTRAINT batallas_bandas_pkey PRIMARY KEY (batalla_banda_id),
	CONSTRAINT batallas_bandas_batalla_banda_key UNIQUE (batalla_id, banda_id),
	CONSTRAINT fk_bb_batalla FOREIGN KEY (batalla_id) REFERENCES public.batallas(batalla_id) ON DELETE CASCADE,
	CONSTRAINT fk_bb_banda FOREIGN KEY (banda_id) REFERENCES public.bandas(banda_id) ON DELETE CASCADE
);

CREATE INDEX idx_campanas_regla ON public.campanas (regla_id);
CREATE INDEX idx_bandas_campana ON public.bandas (campana_id);
CREATE INDEX idx_bandas_lin_banda ON public.bandas_lin (banda_id);
CREATE INDEX idx_batallas_campana ON public.batallas (campana_id);
CREATE INDEX idx_batallas_bandas_banda ON public.batallas_bandas (banda_id);
CREATE INDEX idx_notif_campana ON public.notificaciones (campana_id);
```

## Anexo B · `app/db.py`

```python
"""Acceso a PostgreSQL con psycopg2.

Diseñado para entornos serverless (Vercel): una conexión por petición, cerrada
al terminar. Si no hay DATABASE_URL configurada, las consultas devuelven vacío en
lugar de fallar, para que el esqueleto pueda arrancar sin base de datos.
"""
from flask import current_app, g

try:
    import psycopg2
    import psycopg2.extras
    _HAS_PG = True
except ImportError:  # permite importar el módulo aunque psycopg2 no esté instalado
    _HAS_PG = False


def get_db():
    if "db" in g:
        return g.db
    url = current_app.config.get("DATABASE_URL")
    if not url or not _HAS_PG:
        g.db = None
        return None
    g.db = psycopg2.connect(url)
    return g.db


def query(sql, params=None, one=False):
    """Ejecuta un SELECT. Devuelve lista de dicts (o un dict si one=True)."""
    conn = get_db()
    if conn is None:
        return None if one else []
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall() if cur.description else []
        return (rows[0] if rows else None) if one else rows
    except psycopg2.Error:
        conn.rollback()
        return None if one else []


def execute(sql, params=None, returning=False, commit=True):
    """Ejecuta INSERT/UPDATE/DELETE. Con returning=True devuelve la primera fila.

    Con commit=False la sentencia queda en la transacción abierta: varias
    operaciones encadenadas se confirman juntas en la última con commit=True
    (si algo falla antes, close_db cierra la conexión sin confirmar nada)."""
    conn = get_db()
    if conn is None:
        raise RuntimeError("No hay DATABASE_URL configurada")
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params or ())
        row = cur.fetchone() if (returning and cur.description) else None
    if commit:
        conn.commit()
    return row


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
```

## Anexo C · `api/index.py` (corrección de ruta de Vercel)

```python
"""Entrypoint serverless para Vercel (@vercel/python detecta la variable `app`)."""
import os
import sys

# Permite importar el paquete `app` desde la raíz del proyecto.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402

_flask_app = create_app()

# Cabeceras donde el proxy de Vercel puede dejar la ruta ORIGINAL cuando el
# rewrite /(.*) -> /api/index entrega la petición con PATH_INFO=/api/index
# (comportamiento del runtime de Python a partir de 2026-07; antes llegaba la
# ruta original directamente).
_CANDIDATAS = ("HTTP_X_VERCEL_ORIGINAL_PATH", "HTTP_X_ORIGINAL_PATH",
               "HTTP_X_FORWARDED_URI", "HTTP_X_REWRITE_URL")


@_flask_app.route("/api/index")
def _ruta_perdida():
    """Si una petición llega aquí es que el proxy no entregó la ruta original
    (incidencia del runtime de Vercel de 2026-08). Aviso en lugar de 404."""
    return ("<h1>Mantenimiento</h1><p>Estamos restaurando el servicio. "
            "Vuelve a intentarlo en unos minutos.</p>", 503)


def app(environ, start_response):
    """WSGI intermedio: restaura la ruta original antes de entrar en Flask."""
    path = environ.get("PATH_INFO", "")
    if path.startswith("/api/index"):
        nuevo = None
        for cab in _CANDIDATAS:
            valor = environ.get(cab)
            if valor:
                nuevo = valor.split("?", 1)[0]
                break
        if nuevo is None:
            # Formato antiguo x-now-route-matches: "1=<ruta-codificada>"
            m = environ.get("HTTP_X_NOW_ROUTE_MATCHES")
            if m:
                from urllib.parse import parse_qs, unquote
                grupos = parse_qs(m)
                if "1" in grupos:
                    nuevo = "/" + unquote(grupos["1"][0]).lstrip("/")
        if nuevo and not nuevo.startswith("/api/index"):
            environ["PATH_INFO"] = nuevo
    return _flask_app(environ, start_response)
```

## Anexo D · `vercel.json` y `requirements.txt`

```json
{
  "version": 2,
  "builds": [
    { "src": "api/index.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/(.*)", "dest": "api/index.py" }
  ]
}
```

```
Flask==3.0.3
psycopg2-binary==2.9.9
python-dotenv==1.0.1
reportlab==5.0.0
```

## Anexo E · Servicios de historial y valor (`app/servicios.py`)

```python
"""Operaciones de datos compartidas: historial y valor de las bandas."""
from flask import session

from . import db
from .helpers import MIEMBRO_EN_PLANTILLA


def anotar_historial(banda_id, texto, commit=True):
    """Añade una línea al historial de la banda (bandas.banda_audit):
    «dd/mm/aaaa hh:mm · Usuario · texto». La hora es la de España."""
    autor = (session.get("user") or {}).get("nombre", "sistema")
    db.execute(
        """UPDATE bandas SET banda_audit = COALESCE(banda_audit, '')
               || to_char(now() AT TIME ZONE 'Europe/Madrid', 'DD/MM/YYYY HH24:MI')
               || ' · ' || %s || ' · ' || %s || E'\n'
           WHERE banda_id = %s""",
        (autor, texto, str(banda_id)), commit=commit,
    )


def recalcular_valor(banda_id, commit=True):
    """Valor de banda = Σ coste × cantidad de los miembros en plantilla
    (activos y lesionados). Es la base de la clasificación de la campaña."""
    db.execute(
        """UPDATE bandas SET banda_valor_banda = COALESCE((
               SELECT SUM(banda_lin_coste * banda_lin_cantidad) FROM bandas_lin
               WHERE banda_id = %s AND banda_lin_estado = ANY(%s)), 0)
           WHERE banda_id = %s""",
        (str(banda_id), list(MIEMBRO_EN_PLANTILLA), str(banda_id)), commit=commit,
    )


def historial(texto_audit):
    """Líneas del historial, la más reciente primero."""
    return [ln for ln in (texto_audit or "").splitlines() if ln.strip()][::-1]
```
